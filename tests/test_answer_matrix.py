"""RESTRUCTURE.md §6: same entry, one parameter changed -> a visibly different answer.

Rows A (first_visit) and D (insurance) are P1, row B (concern) is P2, row C (follow_up) is P3.
"""
from pathlib import Path
import re
import tempfile
import unittest

from app import answers
from app.config import Config
from app.server import App

PROFILES = {
    'insured': {'insurance': 'yes', 'plan': {'name': 'Northeastern University Student Health Plan (NUSHP) 2026–27'}, 'zip': '02445'},
    'uninsured': {'insurance': 'no', 'zip': '02445'},
    'choosing': {'insurance': 'no', 'wants_insurance': True},
    'not_sure': {},
}
SBC = {'name': 'SYNTHETIC PPO', 'services': {'primary': {'kind': 'copay', 'amount': 25}, 'urgent': {'kind': 'copay', 'amount': 50},
                                             'er': {'kind': 'copay', 'amount': 150}},
       'deductible': 500, 'oop_max': 4000, 'source': {'file': 'synthetic-sbc.pdf', 'read_on': '2026-11-08'}}


class MatrixTests(unittest.TestCase):
    def test_each_coverage_changes_the_headline_for_rows_a_and_d(self):
        for kind in ('first_visit', 'insurance'):
            heads = {cov: answers.view(kind, p)['en']['headline'] for cov, p in PROFILES.items()}
            self.assertEqual(len(set(heads.values())), 4, (kind, heads))
            for cov, p in PROFILES.items():
                self.assertEqual(answers.view(kind, p)['en']['coverage'], cov)

    def test_headlines_never_show_zero_dollars_and_languages_stay_separate(self):
        for kind in answers.CARD_KINDS:
            for p in PROFILES.values():
                v = answers.view(kind, p)
                self.assertNotIn('$0', v['en']['headline'])
                self.assertFalse(re.search(r'[㐀-鿿]', v['en']['headline']), v['en']['headline'])
                self.assertTrue(re.search(r'[㐀-鿿]', v['zh']['headline']), v['zh']['headline'])

    def test_unknown_cost_is_labeled_not_zero(self):
        v = answers.view('first_visit', {'insurance': 'yes', 'plan': {'name': 'SYNTHETIC PPO'}})['en']
        self.assertTrue(any('not $0' in c for c in v['cost']), v['cost'])

    def test_sbc_numbers_reach_both_rows(self):
        p = {'insurance': 'yes', 'plan': {'name': 'SYNTHETIC PPO'}, 'plan_benefits': SBC}
        d = answers.view('insurance', p)['en']
        self.assertIn('$25.00 copay', d['headline']); self.assertIn('$150.00 copay', d['headline'])
        a = answers.view('first_visit', p)['en']
        self.assertTrue(any('from your SBC' in c for c in a['cost']))

    def test_brookline_zip_uses_sourced_brookline_clinic_without_invented_distance(self):
        v = answers.view('first_visit', PROFILES['insured'])['en']
        self.assertIn('02445', v['clinics'][0]['address']); self.assertIn('near 02445', v['headline'])
        far = answers.view('first_visit', dict(PROFILES['insured'], zip='99999'))['en']
        self.assertNotIn('near 99999', far['headline']); self.assertIn('in Boston', far['headline'])

    def test_uncertain_coverage_sends_a_to_d_and_never_lists_clinics(self):
        for cov in ('not_sure', 'choosing'):
            v = answers.view('first_visit', PROFILES[cov])['en']
            self.assertEqual(v['clinics'], []); self.assertEqual(v['actions'][0]['id'], 'go-insurance'); self.assertEqual(v['stage'], 0)

    def test_choosing_ranks_only_complete_plans(self):
        compare = {'needs': {'primary': 2}, 'plans': [
            {'name': 'Plan A', 'premium': 100, 'oop_max': 3000, 'costs': {'primary': {'status': 'covered', 'cost': 30}}},
            {'name': 'Plan B', 'premium': 80, 'oop_max': 3000, 'costs': {'primary': {'status': 'covered', 'cost': 40}}}]}
        v = answers.view('insurance', dict(PROFILES['choosing'], plan_compare=compare))['en']
        self.assertIn('Plan B costs about $220 less', v['headline'])
        compare['plans'][0]['costs']['primary'] = {'status': 'unknown'}
        v = answers.view('insurance', dict(PROFILES['choosing'], plan_compare=compare))['en']
        self.assertIn('Can’t rank yet', v['headline'])

    def test_every_entry_has_a_card(self):
        for kind in ('first_visit', 'concern', 'follow_up', 'report', 'insurance'):
            self.assertIsNotNone(answers.view(kind, {}), kind)
        self.assertIsNone(answers.view('general', {}))


REPORT = [{'id': 'r1', 'label': 'SYNTHETIC lab', 'rows': [
    {'name': 'SYNTHETIC Marker', 'result': '12 mg/dL', 'reference': '1-10', 'flag': 'High'},
    {'name': 'SYNTHETIC Other', 'result': '3', 'reference': '1-5', 'flag': ''}]}]
FOLLOWS = {'follow_up': {'type': 'follow_up', 'what': 'come back for a blood test', 'who': 'Dr. SYNTHETIC', 'due': '2026-12-01'},
           'refill': {'type': 'refill', 'what': 'SYNTHETIC-mycin', 'who': '', 'due': '2026-11-20'},
           'results': {'type': 'results', 'what': '', 'who': '', 'due': ''}}


class RowCTests(unittest.TestCase):
    def c(self, profile, f, reports=()):
        return answers.view('follow_up', profile, {'followup': f, 'reports': list(reports)})['en']

    def test_starts_by_asking_what_you_have(self):
        v = self.c({}, None)
        self.assertTrue(v['followup_form']); self.assertTrue(v['report_upload']); self.assertEqual(v['stage'], 0)

    def test_each_type_changes_with_coverage(self):
        for name, f in FOLLOWS.items():
            heads = {cov: self.c(p, f, REPORT)['headline'] for cov, p in PROFILES.items()}
            self.assertEqual(len(set(heads.values())), 4, (name, heads))
            self.assertFalse(any('$0' in h for h in heads.values()), heads)

    def test_results_quote_flags_without_interpreting(self):
        v = self.c(PROFILES['insured'], FOLLOWS['results'], REPORT)
        self.assertIn('2 reviewed, 1 marked by the lab', v['headline'])
        self.assertEqual([x['flag'] for x in v['facts']], ['High', ''])
        self.assertEqual(len(v['questions']), 1); self.assertIn('marks SYNTHETIC Marker as High', v['questions'][0])
        text = str(v).lower()
        for word in ('abnormal', 'you have ', 'normal range'):
            self.assertNotIn(word, text)

    def test_sbc_lines_used_for_refill_and_visit(self):
        sbc = dict(SBC, services=dict(SBC['services'], generic={'kind': 'copay', 'amount': 10}))
        p = {'insurance': 'yes', 'plan': {'name': 'SYNTHETIC PPO'}, 'plan_benefits': sbc}
        self.assertIn('$10.00 copay', self.c(p, FOLLOWS['refill'])['headline'])
        self.assertIn('$25.00 copay', self.c(p, FOLLOWS['follow_up'])['cost'][0])

    def test_clean_followup_and_todos(self):
        with self.assertRaises(ValueError):
            answers.clean_followup({'type': 'follow_up', 'what': ''})
        with self.assertRaises(ValueError):
            answers.clean_followup({'type': 'refill', 'what': 'x', 'due': '12/01'})
        self.assertEqual(answers.clean_followup({'type': 'results'}, has_reports=True)['type'], 'results')
        profile = {'follow_ups': [{'what': 'come back for a blood test', 'due': '2026-01-01'}]}
        answers.add_todo(profile, FOLLOWS['follow_up']); answers.add_todo(profile, FOLLOWS['refill'])
        self.assertEqual(profile['follow_ups'], [{'what': 'come back for a blood test', 'due': '2026-12-01'}])  # updated, not duplicated
        self.assertEqual(profile['refills'], {'SYNTHETIC-mycin': '2026-11-20'}); self.assertIn('SYNTHETIC-mycin', profile['medications'])


def safety(*checks, description=''):
    from app.navigation import safety_check
    return safety_check({'checks': list(checks), 'description': description})


class RowBTests(unittest.TestCase):
    def b(self, profile, s):
        return answers.view('concern', profile, {'safety': s})['en']

    def test_safety_check_comes_first_for_everyone(self):
        heads = {self.b(p, None)['headline'] for p in PROFILES.values()}
        self.assertEqual(len(heads), 1)
        v = self.b(PROFILES['insured'], None)
        self.assertTrue(v['safety_form']); self.assertEqual(v['stage'], 0); self.assertFalse(any('$' in c for c in v['cost']))

    def test_non_emergency_levels_change_with_coverage(self):
        for checks in (('injury',), ('sore_throat',), ('refill',), ('checkup',)):
            s = safety(*checks)
            heads = {cov: self.b(p, s)['headline'] for cov, p in PROFILES.items()}
            self.assertEqual(len(set(heads.values())), 4, (checks, heads))
            if checks != ('checkup',):
                self.assertFalse(any('$0' in h for h in heads.values()), heads)

    def test_emergency_never_varies_or_shows_a_price(self):
        for checks, call in ((('chest_pain',), 'tel:911'), (('self_harm',), 'tel:988'), (('poison',), 'tel:18002221222')):
            s = safety(*checks)
            views = [self.b(p, s) for p in PROFILES.values()]
            self.assertEqual(len({v['headline'] for v in views}), 1, checks)
            for v in views:
                self.assertFalse(re.search(r'\$\d', v['headline'] + ''.join(v['cost'])), v)
                self.assertIn(call, [c['href'] for c in v['calls']]); self.assertEqual(v['clinics'], [])
        self.assertIn('988', self.b({}, safety('self_harm'))['headline'])

    def test_same_day_uses_sbc_urgent_and_er_lines(self):
        v = self.b({'insurance': 'yes', 'plan': {'name': 'SYNTHETIC PPO'}, 'plan_benefits': SBC}, safety('injury'))
        self.assertIn('$50.00 copay', v['headline']); self.assertIn('$150.00 copay', v['headline'])

    def test_refill_is_not_told_it_may_be_free(self):
        self.assertNotIn('$0', self.b(PROFILES['insured'], safety('refill'))['headline'])
        self.assertIn('$0', self.b(PROFILES['insured'], safety('checkup'))['headline'])

    def test_no_invented_urgent_care_location(self):
        self.assertEqual(self.b(PROFILES['uninsured'], safety('injury'))['clinics'], [])
        nushp = self.b(PROFILES['insured'], safety('injury'))
        self.assertEqual([c['id'] for c in nushp['clinics']], ['nu-uhcs'])  # sourced campus clinic only


class MeTests(unittest.TestCase):
    def test_apply_me_updates_only_shared_fields(self):
        profile = {'birth_year': 2000, 'medications': ['SYNTHETIC'], 'insurance': 'yes', 'plan': {'name': 'SYNTHETIC PPO'}, 'plan_benefits': SBC}
        answers.apply_me(profile, {'coverage': 'insured', 'plan': 'SYNTHETIC PPO', 'zip': '02445', 'language': 'Chinese'})
        self.assertEqual(profile['plan_benefits'], SBC)  # same plan keeps its reviewed SBC
        m = answers.apply_me(profile, {'coverage': 'uninsured', 'zip': '02445'})
        self.assertEqual(m['coverage'], 'uninsured'); self.assertIsNone(profile['plan']); self.assertNotIn('plan_benefits', profile)
        self.assertEqual((profile['birth_year'], profile['medications'], profile['language']), (2000, ['SYNTHETIC'], 'Chinese'))
        self.assertEqual(answers.apply_me(profile, {'coverage': 'not_sure'})['coverage'], 'not_sure')
        self.assertEqual(profile['insurance'], '')

    def test_apply_me_rejects_bad_values(self):
        for raw in ({'coverage': 'maybe'}, {'coverage': 'insured', 'zip': '2445'}, {'coverage': 'insured', 'language': 'Klingon'}):
            with self.assertRaises(ValueError):
                answers.apply_me({}, raw)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); cfg = Config(); cfg.store_path = Path(self.tmp.name) / 'v.fv'; cfg.exa_key = cfg.tavily_key = ''
        self.app = App(cfg); self.post('/api/vault/create', passphrase='synthetic-only-passphrase')

    def tearDown(self): self.tmp.cleanup()
    def post(self, path, **data): return self.app.dispatch('POST', path, data, {})

    def test_coverage_is_asked_once_and_carries_between_a_and_d(self):
        a = self.post('/api/journeys', kind='first_visit', goal='I think I have the school insurance')
        self.assertEqual(a['answer']['en']['coverage'], 'not_sure')  # "I think" is not a confirmed answer
        self.assertEqual(a['suggested_coverage'], 'insured')
        out = self.post('/api/me', coverage='insured', plan='NUSHP 2026–27', zip='02445', journey_id=a['id'])
        self.assertEqual(out['journey']['answer']['en']['coverage'], 'insured')
        self.assertNotEqual(out['journey']['answer']['en']['headline'], a['answer']['en']['headline'])
        d = self.post('/api/journeys', kind='insurance', goal='SYNTHETIC')
        self.assertEqual(d['answer']['en']['coverage'], 'insured'); self.assertIn('NUSHP', d['answer']['en']['headline'])
        self.assertEqual(self.app.state()['me']['zip'], '02445')
        lines = {c['kind']: c['next_action'] for c in self.app.state()['cases']}
        self.assertIn('Ask NUSHP for the 2026–27 SBC', lines['insurance'])  # not the old one-size-fits-all sentence
        self.assertIn('Call ', lines['first_visit'])

    def test_b_safety_check_is_stored_without_free_text(self):
        j = self.post('/api/journeys', kind='concern', goal='SYNTHETIC concern')
        self.assertTrue(j['answer']['en']['safety_form'])
        j = self.post('/api/journey/safety', id=j['id'], checks=['injury'], description='SYNTHETIC private words')
        self.assertEqual(j['safety']['level'], 'same_day'); self.assertEqual(j['answer']['en']['stage'], 2)
        self.assertNotIn('SYNTHETIC private words', str(self.app.store.data['cases'][j['id']]))
        self.assertIn('urgent care', j['answer']['en']['headline'])

    def test_b_goal_warning_shows_the_emergency_card(self):
        j = self.post('/api/journeys', kind='concern', goal='I have chest pain')
        self.assertIn('Call 911', j['answer']['en']['headline']); self.assertIn('tel:911', [c['href'] for c in j['answer']['en']['calls']])

    def test_c_followup_feeds_my_health_todos(self):
        j = self.post('/api/journeys', kind='follow_up', goal='SYNTHETIC')
        self.assertTrue(j['answer']['en']['followup_form'])
        from datetime import date, timedelta
        due = (date.today() + timedelta(days=10)).isoformat()
        j = self.post('/api/journey/followup', id=j['id'], type='follow_up', what='SYNTHETIC recheck', due=due)
        self.assertIn('SYNTHETIC recheck', j['answer']['en']['headline']); self.assertEqual(j['answer']['en']['stage'], 2)
        todos = self.app.dispatch('GET', '/api/profile', {}, {})['todos']
        self.assertIn('SYNTHETIC recheck', [t['title'] for t in todos])

    def test_emergency_goal_gets_no_cost_card(self):
        j = self.post('/api/journeys', kind='first_visit', goal='I have chest pain')
        self.assertIsNone(j['answer']); self.assertEqual(j['safety_notice']['level'], 'emergency')


if __name__ == '__main__':
    unittest.main()
