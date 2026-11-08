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
        situation, en, _ = self.sections('i have student insurance but I am not sure how to use it.')
        self.assertEqual(situation, 'insured')
        text = str(en)
        self.assertIn('in network', text); self.assertNotIn('uninsured', text); self.assertNotIn('self-pay', text)
        self.assertNotIn('Questions for my clinician', text)
        self.assertEqual(self.sections("I don't have insurance right now")[0], 'uninsured')
        self.assertEqual(self.sections('Which plan should I choose?')[0], 'choosing')
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
        self.assertEqual(self.post('/api/journeys', kind='first_visit', goal='I do not have insurance')['coverage_situation'], 'uninsured')
        self.assertEqual(self.post('/api/journeys', kind='concern', goal='I have student insurance')['coverage_situation'], 'insured')

    def test_refill_is_not_told_checkups_may_be_free(self):
        from app.scenarios import insured
        self.assertNotIn('Checkups and screenings may be free', [t['title'] for t in insured({'service': 'primary_care', 'need': 'refill'})['tips']])
        self.assertIn('Checkups and screenings may be free', [t['title'] for t in insured({'service': 'primary_care', 'need': 'checkup'})['tips']])
