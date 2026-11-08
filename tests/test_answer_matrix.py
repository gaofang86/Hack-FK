"""RESTRUCTURE.md §6: same entry, one parameter changed -> a visibly different answer.

Rows A (first_visit) and D (insurance) are P1. B and C keep the existing task page for now.
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
        for kind in answers.CARD_KINDS:
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

    def test_b_and_c_are_not_cards_yet(self):
        self.assertIsNone(answers.view('concern', {})); self.assertIsNone(answers.view('follow_up', {}))


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

    def test_emergency_goal_gets_no_cost_card(self):
        j = self.post('/api/journeys', kind='first_visit', goal='I have chest pain')
        self.assertIsNone(j['answer']); self.assertEqual(j['safety_notice']['level'], 'emergency')


if __name__ == '__main__':
    unittest.main()
