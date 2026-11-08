"""Shared journeys, optional reports, review gating, persistence and egress boundaries."""
import base64
from copy import deepcopy
from datetime import date
import io
import re
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from app.config import Config
from app.server import App
from app.egress import dlp_violations
from tests.test_person_first import health_first


def synthetic_pdf():
    writer = PdfWriter();page=writer.add_blank_page(612,792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 40 700 Td (Lab results) Tj 0 -20 Td (SYNTHETIC Marker 12.34 mg/dL 01) Tj 0 -20 Td (Normal: 1-20) Tj 0 -20 Td (Final) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    buf=io.BytesIO();writer.write(buf)
    return base64.b64encode(buf.getvalue()).decode()


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();cfg=Config();cfg.store_path=Path(self.tmp.name)/'vault.fv';cfg.exa_key=cfg.tavily_key=''
        self.app=App(cfg);self.post('/api/vault/create',passphrase='synthetic-only-passphrase')
    def tearDown(self):self.tmp.cleanup()
    def post(self,path,**data):return self.app.dispatch('POST',path,data,{})
    def get(self,path,**query):return self.app.dispatch('GET',path,{}, {k:[v] for k,v in query.items()})
    def task(self,kind='first_visit'):return self.post('/api/journeys',kind=kind,goal='SYNTHETIC personal goal sentinel')
    def attach(self,j):
        p=self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=synthetic_pdf(),file_name='synthetic.pdf')
        return p,self.post('/api/reports/confirm',token=p['token'],confirmed=True,rows=p['rows'])
    def test_all_scenarios_start_without_report_or_full_profile(self):
        for kind in ('general','insurance','first_visit','concern','report','follow_up'):
            j=self.task(kind);self.assertEqual(j['kind'],kind);self.assertEqual(j['reports'],[])
            self.assertIn('One question first' if kind=='insurance' else 'Questions for my clinician',j['personal_preparation'])
        self.assertEqual(len(self.get('/api/state')['cases']),6)
        self.assertFalse(self.get('/api/state')['profile_ready'])
    def test_review_is_required_and_report_does_not_create_medical_tasks(self):
        j=self.task('report');p=self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=synthetic_pdf())
        self.assertFalse(self.app.store.data.get('reports'))
        with self.assertRaises(ValueError):self.post('/api/reports/confirm',token=p['token'],rows=p['rows'])
        reviewed=self.post('/api/reports/confirm',token=p['token'],confirmed=True,rows=p['rows'])
        self.assertEqual(len(reviewed['reports']),1)
        self.assertNotIn('follow_ups',self.app.store.data['profile'])
        self.assertEqual(reviewed['status'],'planning')
        self.assertNotIn('SYNTHETIC personal',self.app.store.path.read_bytes().decode(errors='ignore'))
    def test_search_extends_same_task_without_sending_goal_or_report(self):
        j=self.task('report');p,j=self.attach(j)
        before_id=j['id'];raw=health_first();raw['demo']=False
        preview=self.post('/api/preview',**raw,journey_id=j['id'])
        for q in preview['queries']:
            self.assertNotIn('12.34',q['query']);self.assertNotIn('sentinel',q['query'])
        case=self.post('/api/search',token=preview['token'],approved=True,live=False)
        self.assertEqual(case['id'],before_id);self.assertEqual(len(case['report_ids']),1)
        self.assertEqual(case['goal'],j['goal'])
        note=self.post('/api/case/preparation',id=case['id'])
        self.assertIn('12.34 mg/dL',note['personal_note'])
        self.assertNotIn('12.34',note['text'])
        self.assertTrue(dlp_violations({'query':'12.34 mg/dL'},self.app.store.data))
        self.assertTrue(dlp_violations({'query':j['goal']},self.app.store.data))
    def test_saved_task_keeps_its_kind_and_follow_ups_are_not_called_new_patients(self):
        j=self.task('follow_up');raw=health_first(service='follow_up',need='follow_up');raw['demo']=False
        preview=self.post('/api/preview',**raw,journey_id=j['id'])
        case=self.post('/api/search',token=preview['token'],approved=True,live=False)
        summary=next(c for c in self.get('/api/state')['cases'] if c['id']==j['id'])
        self.assertEqual(summary['kind'],'follow_up')
        reasons=[r for row in case['results'] for r in row['reasons']]
        self.assertTrue(reasons)
        self.assertFalse([r for r in reasons if 'new-patient' in r.lower()])
        self.assertIn('Appointment availability needs confirmation',reasons)
    def test_forget_clears_report_and_derived_preparation_then_cannot_restore(self):
        j=self.task();_,j=self.attach(j);rid=j['reports'][0]['id']
        self.app.get_journey(j['id'])['preparation']={'personal_note':'12.34 mg/dL'}
        self.post('/api/reports/forget',report_id=rid)
        j=self.get('/api/journey',id=j['id'])
        self.assertEqual(j['reports'],[]);self.assertNotIn('12.34',j['personal_preparation']);self.assertNotIn('preparation',j)
        self.post('/api/vault/lock');self.post('/api/vault/unlock',passphrase='synthetic-only-passphrase')
        self.assertEqual(self.get('/api/journey',id=j['id'])['reports'],[])
    def test_lock_and_forget_everything_clear_drafts_and_saved_reports(self):
        j=self.task();p,j=self.attach(j)
        self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=synthetic_pdf())
        self.post('/api/vault/lock');self.assertFalse(self.app.report_previews)
        self.post('/api/vault/unlock',passphrase='synthetic-only-passphrase')
        self.post('/api/profile/forget',field='everything')
        self.assertFalse(self.app.store.data.get('reports'));self.assertFalse(self.app.store.data['cases'])
    def test_task_goal_cannot_bypass_emergency_or_same_day_guard(self):
        emergency=self.post('/api/journeys',kind='first_visit',goal='I have chest pain')
        self.assertEqual(emergency['safety_notice']['level'],'emergency')
        raw=health_first();raw['demo']=False
        with self.assertRaises(ValueError):self.post('/api/preview',**raw,journey_id=emergency['id'])
        today=self.post('/api/journeys',kind='concern',goal='I have a current concern')
        same_day=health_first(checks=['high_fever'],none_reported=False)
        same_day['demo']=False
        with self.assertRaises(ValueError):self.post('/api/preview',**same_day,journey_id=today['id'])

    def test_invalid_reports_and_mismatched_review_do_not_mutate(self):
        j=self.task();before=deepcopy(self.app.store.data)
        for encoded in ('not-base64',base64.b64encode(b'not PDF').decode()):
            with self.assertRaises(ValueError):self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=encoded)
        self.assertEqual(before,self.app.store.data)
        p=self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=synthetic_pdf())
        with self.assertRaises(ValueError):self.post('/api/reports/confirm',token=p['token'],confirmed=True,rows=[])
        self.assertFalse(self.app.store.data.get('reports'))


class CoveragePreparationTests(unittest.TestCase):
    def sections(self, goal, profile=None):
        from app import journeys
        case = {'kind': 'insurance', 'goal': goal}
        secs = journeys.preparation_sections(case, [], profile)
        return journeys.coverage_situation(case, profile), journeys.localized(secs, 'en'), journeys.localized(secs, 'zh')

    def test_goal_wording_and_profile_choose_the_branch(self):
        from app.journeys import suggested_coverage
        # Wording alone is a suggestion, never a settled answer ("I think I have insurance").
        self.assertEqual(self.sections('i have student insurance but I am not sure how to use it.')[0], 'unknown')
        self.assertEqual(suggested_coverage({'goal': 'i have student insurance but I am not sure how to use it.'}), 'insured')
        self.assertEqual(suggested_coverage({'goal': "I don't have insurance right now"}), 'uninsured')
        self.assertEqual(suggested_coverage({'goal': 'Which plan should I choose?'}), 'choosing')
        self.assertIsNone(suggested_coverage({'goal': 'I want help'}))
        situation, en, _ = self.sections('I want help', {'insurance': 'yes'})
        text = str(en)
        self.assertIn('in network', text); self.assertNotIn('uninsured', text); self.assertNotIn('self-pay', text)
        self.assertNotIn('Questions for my clinician', text)
        self.assertEqual(self.sections('I want help')[0], 'unknown')
        # Saved profile beats wording and names the plan.
        situation, en, _ = self.sections('I want help', {'insurance': 'yes', 'plan': {'name': 'SYNTHETIC PPO'}})
        self.assertEqual(situation, 'insured'); self.assertIn('SYNTHETIC PPO', str(en))
        self.assertEqual(self.sections('I have insurance', {'insurance': 'no', 'wants_insurance': True})[0], 'choosing')

    def test_each_language_view_is_single_language_and_keeps_user_text(self):
        import re
        _, en, zh = self.sections('我有学生保险 SYNTHETIC')
        for sec in en:
            self.assertFalse(re.search(r'[\u3400-\u9fff]', sec['title'] + ''.join(i for i in sec['items'] if 'SYNTHETIC' not in i)))
        self.assertTrue(all(re.search(r'[\u3400-\u9fff]', sec['title']) for sec in zh))
        self.assertEqual(en[0]['items'][0], '我有学生保险 SYNTHETIC')


class ScenarioConsistencyTests(JourneyTests):
    """The call script and wizard hints must match what the user already said."""
    def script(self, kind='follow_up', goal='SYNTHETIC goal', **changes):
        j = self.post('/api/journeys', kind=kind, goal=goal)
        raw = health_first(**changes); raw['demo'] = False
        preview = self.post('/api/preview', **raw, journey_id=j['id'])
        case = self.post('/api/search', token=preview['token'], approved=True, live=False)
        return j, case, self.post('/api/case/preparation', id=case['id'])

    def test_insured_without_plan_name_is_not_asked_only_for_self_pay(self):
        _, _, prep = self.script(insurance='yes', plan={'name': '', 'rule': 'copay'})
        self.assertIn('in-network for my plan', prep['text'])
        self.assertNotIn('self-pay price', prep['text'].split('\n')[2])

    def test_follow_up_script_does_not_assume_a_new_patient(self):
        _, _, prep = self.script(service='follow_up', need='follow_up')
        self.assertIn('Am I already a patient here?', prep['text'])
        _, _, prep = self.script(service='primary_care')
        self.assertIn('Are you accepting new adult patients', prep['text'])

    def test_personal_note_is_offered_one_language_at_a_time(self):
        _, _, prep = self.script()
        self.assertFalse(re.search(r'[㐀-鿿]', prep['personal_note_view']['en']))
        self.assertTrue(re.search(r'[㐀-鿿]', prep['personal_note_view']['zh']))

    def test_goal_coverage_wording_is_exposed_for_every_task(self):
        j = self.post('/api/journeys', kind='first_visit', goal='I do not have insurance')
        self.assertEqual((j['coverage_situation'], j['suggested_coverage']), ('unknown', 'uninsured'))
        j = self.post('/api/journeys', kind='concern', goal='I have student insurance')
        self.assertEqual((j['coverage_situation'], j['suggested_coverage']), ('unknown', 'insured'))

    def test_refill_is_not_told_checkups_may_be_free(self):
        from app.scenarios import insured
        self.assertNotIn('Checkups and screenings may be free', [t['title'] for t in insured({'service': 'primary_care', 'need': 'refill'})['tips']])
        self.assertIn('Checkups and screenings may be free', [t['title'] for t in insured({'service': 'primary_care', 'need': 'checkup'})['tips']])


class ExplainCoverageTests(unittest.TestCase):
    class FakeModel:
        model_name = 'fake'
        def __init__(self, text, available=True): self.text, self.available = text, available
        def status(self): return {'available': self.available, 'reason': '' if self.available else 'off'}
        def generate(self, prompt, system, n):
            assert 'SYNTHETIC GOAL' not in prompt  # health/goal text never reaches the model
            return self.text

    def run_explain(self, text, available=True, lang='en'):
        from app import explain
        return explain.explain_coverage(self.FakeModel(text, available), {'kind': 'insurance', 'goal': 'SYNTHETIC GOAL I have student insurance'}, {'insurance': 'yes'}, lang)

    def test_checked_model_text_is_used_and_invented_facts_fall_back(self):
        ok = self.run_explain('You have insurance, but your benefits are not added yet, so the cost is unknown. Call the number on your card.')
        self.assertTrue(ok['source'].startswith('local model'), ok)
        made_up = self.run_explain('Your copay is $15 and the clinic is in network confirmed.')
        self.assertIn('rules template', made_up['source']); self.assertIn('unknown (not $0)', made_up['text'])
        self.assertIn('rules template', self.run_explain('You probably have a diagnosis.')['source'])
        # Real failures seen with the local model: plausible but unsupported cost claims.
        self.assertIn('rules template', self.run_explain('You are covered, but you will likely need to pay some money out of pocket.')['source'])
        self.assertIn('rules template', self.run_explain('您目前拥有保险，但此次就医的费用超出了您的计划覆盖范围。', lang='zh')['source'])
        self.assertIn('rules template', self.run_explain('You have insurance. Call the number on your card.')['source'])  # omits that cost is unknown
        off = self.run_explain('', available=False, lang='zh')
        self.assertIn('你有保险', off['text'])
        self.assertNotRegex(off['text'], r'[A-Za-z]{6,}')  # Chinese template is fully Chinese
        self.assertIn('rules template', self.run_explain('您的保险计划目前处于未激活状态，费用尚未确定。', lang='zh')['source'])

class ExplainCheckSanityTests(unittest.TestCase):
    def test_forbidden_pattern_does_not_match_neutral_text(self):
        from app import explain
        self.assertIsNone(explain.FORBIDDEN.search('Call the number on your card and ask about the visit.'))


class ExplainComparisonTests(unittest.TestCase):
    rows = [
        {"provider": {"name": "SYNTH Clinic A"}, "cost": {"amount": None, "status": "unknown"}, "supported": False, "unavailable": False,
         "miles": 0.8, "reasons": ["Chinese listed", "Appointment availability needs confirmation"], "confirmation": [1, 2]},
        {"provider": {"name": "SYNTH Clinic B"}, "cost": {"amount": 120, "status": "user_quote"}, "supported": True, "unavailable": False,
         "miles": None, "reasons": ["Within your visit budget"], "confirmation": [1]},
    ]

    def run_explain(self, text, lang='en'):
        from app import explain
        return explain.explain_comparison(ExplainCoverageTests.FakeModel(text), self.rows, {"priority": "cost"}, lang)

    def test_ranking_explanations_are_checked(self):
        ok = self.run_explain('The cost of SYNTH Clinic A is not known yet, and it is 0.8 miles away. SYNTH Clinic B has a $120 quote; ask A about cost.')
        self.assertTrue(ok['source'].startswith('local model'), ok)
        for bad in ['SYNTH Clinic B is the best and cheapest choice. Cost of A is unknown.',
                    'SYNTH Clinic A is in network. Its cost is unknown.',
                    'SYNTH Clinic A costs $90.',
                    'SYNTH Clinic A is listed first because Chinese is listed.']:  # omits unknown cost
            self.assertIn('rules template', self.run_explain(bad)['source'], bad)
        zh = self.run_explain('', lang='zh')
        self.assertIn('未知（不是 0）', zh['text'])
        # Real local-model failures: invented ordering reasons and "confirmed" language support.
        for bad in ['The first option is prioritized because it was the initial request for service; its cost is not known yet.',
                    '排序时优先列出这家诊所，因为这是用户明确选择的平衡选项，且该诊所已确认提供语言支持服务。费用未知。']:
            self.assertIn('rules template', self.run_explain(bad)['source'], bad)
        # B has supported cost and A does not: the rules sentence says so, whatever the model writes.
        good = self.run_explain('The cost of SYNTH Clinic A is not known yet; ask the office about cost and language support.')
        self.assertTrue(good['source'].startswith('local model'), good)

    def test_tied_options_are_described_as_tied(self):
        from app import explain
        tied = [dict(r, supported=False, cost={"amount": None}, miles=None) for r in self.rows]
        en, zh = explain.why_first(tied, "balanced")
        self.assertIn('same evidence', en); self.assertIn('按名称排列', zh)


class ConflictAuditTests(ScenarioConsistencyTests):
    """Every view of one task tells the same coverage story and follows the user's own choices."""
    def test_shortlist_coverage_is_the_same_on_results_journey_and_explanation(self):
        from app import explain
        # Goal wording says nothing about insurance; the Find care answer was "no insurance".
        j, case, _ = self.script(kind='follow_up', goal='SYNTHETIC goal', insurance='no', wants_insurance=False, plan=None)
        self.assertEqual(case['coverage_situation'], 'uninsured')
        self.assertEqual(self.get('/api/journey', id=j['id'])['coverage_situation'], 'uninsured')
        stored = self.app.store.data['cases'][j['id']]
        self.assertEqual(explain.coverage_facts(stored, {})['situation'], 'uninsured')

    def test_reviewed_benefits_are_not_claimed_for_an_uninsured_person(self):
        from app import explain
        facts = explain.coverage_facts({'goal': 'I do not have insurance', 'input': {'insurance': 'no'}},
                                       {'plan_benefits': {'name': 'SYNTHETIC'}, 'plan': {'name': 'SYNTHETIC PPO'}})
        self.assertEqual(facts['situation'], 'uninsured')
        self.assertFalse(facts['benefits_added']); self.assertEqual(facts['plan_name'], '')
        self.assertIn('unknown (not $0)', explain.template(facts, 'en'))
        self.assertNotIn('plan documents', explain.model_facts(facts))

    def test_next_action_follows_the_chosen_clinic(self):
        _, case, _ = self.script(kind='concern', goal='SYNTHETIC goal')
        self.assertGreater(len(case['results']), 1)
        last = case['results'][-1]['provider']
        self.assertNotIn(last['name'], case['next_action'])
        chosen = self.post('/api/case/contact', id=case['id'], status='comparing', provider_id=last['id'])
        self.assertIn(last['name'], chosen['next_action'])
