"""Real-source student scenario: unknown costs and candidate-scoped confirmation."""
from pathlib import Path
import tempfile
import unittest

from app.config import Config
from app.server import App
from tests.test_person_first import health_first


class NeuScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Config()
        cfg.store_path = Path(self.tmp.name) / 'v.fv'
        cfg.exa_key = cfg.tavily_key = ''
        self.app = App(cfg)
        self.call('/api/vault/create', {'passphrase': 'disposable-test-passphrase'})
        person = health_first()
        person.update(city='Brookline', zip='02445', demo=False, scenario='neu_student',
                      insurance='yes', plan={'name': 'NUSHP — exact product/year to confirm', 'rule': 'copay'})
        token = self.call('/api/preview', person)['token']
        self.case = self.call('/api/search', {'token': token, 'approved': True, 'live': False})

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, path, body):
        return self.app.dispatch('POST', path, body, {})

    def test_real_candidates_do_not_invent_plan_prices_or_network(self):
        self.assertEqual(self.case['input']['scenario'], 'neu_student')
        self.assertGreaterEqual(len(self.case['results']), 2)
        for row in self.case['results']:
            self.assertFalse(row['provider']['demo'])
            self.assertIsNone(row['cost']['amount'])
            self.assertEqual(row['provider']['coverage'], {})
            self.assertTrue(row['provider']['phone'])
            self.assertIn('insurance', [t['key'] for t in row['confirmation']])
        self.assertFalse(self.case['sources'][0]['in_network_filter'])

    def test_preparation_is_scoped_and_invalid_provider_rejected(self):
        provider = self.case['providers'][0]
        prep = self.call('/api/case/preparation', {'id': self.case['id'], 'provider_id': provider['id']})
        self.assertIn(provider['name'], prep['text'])
        self.assertIn(provider['address'], prep['text'])
        self.assertEqual(prep['provider_id'], provider['id'])
        with self.assertRaisesRegex(ValueError, 'Provider not found'):
            self.call('/api/case/preparation', {'id': self.case['id'], 'provider_id': 'foreign-case-provider'})

    def test_quote_updates_only_target_and_removes_resolved_cash_question(self):
        provider = self.case['providers'][0]
        from datetime import date
        result = self.call('/api/case/quote', {'id': self.case['id'], 'provider_id': provider['id'],
                           'cash': 180, 'checked_on': date.today().isoformat(),
                           'source': 'Synthetic test response, not a real clinic quote', 'scope_confirmed': True})
        row = next(r for r in result['results'] if r['provider']['id'] == provider['id'])
        self.assertEqual(row['cost']['amount'], 180)
        self.assertNotIn('cash', [t['key'] for t in row['confirmation']])
        self.assertIn('insurance', [t['key'] for t in row['confirmation']])
        self.assertTrue(all(r['cost']['amount'] is None for r in result['results'] if r['provider']['id'] != provider['id']))
        self.assertEqual(self.app.store.data['profile'].get('plan'), None)

    def test_public_reference_is_separate_from_personal_cost_inputs(self):
        ref = self.case['plan_reference']
        self.assertEqual(ref['period'], {'start': '2026-09-01', 'end': '2027-08-31'})
        self.assertEqual(ref['annual_student_fee'], 3049)
        self.assertIn('2025–26', ref['benefit_status'])
        self.assertIsNone(self.case['input']['plan']['copay'])
        self.assertIsNone(self.case['input']['plan']['premium'])
        self.assertTrue(all(r['insured']['amount'] is None for r in self.case['results']))

    def test_student_scenario_does_not_borrow_saved_personal_benefits(self):
        self.app.store.data['profile']['plan_benefits'] = {'name': 'Unrelated private plan', 'services': {'primary': {'kind': 'copay', 'amount': 5}}}
        person = dict(self.case['input'])
        token = self.call('/api/preview', person)['token']
        self.assertIsNone(self.app.previews[token]['input']['benefits'])
