"""External candidate and confirmation workflow regressions."""
from datetime import date, timedelta
from unittest.mock import patch

from app.egress import dlp_violations
from app.benefits import cash_cost
import unittest
from tests import test_neu_scenario as fixtures


class CompletionTests(unittest.TestCase):
    setUp = fixtures.NeuScenarioTests.setUp
    tearDown = fixtures.NeuScenarioTests.tearDown
    call = fixtures.NeuScenarioTests.call
    def candidate(self, **changes):
        data = dict(id=self.case['id'], name='Test external practice', address='Test public clinic address',
                    url='https://example.org/public-clinic', source='Synthetic official-directory test entry',
                    checked_on=date.today().isoformat())
        data.update(changes)
        result = self.call('/api/case/candidate', data)
        return result, result['providers'][-1]

    def answer(self, provider, **changes):
        data = dict(id=self.case['id'], provider_id=provider['id'], key='availability', result='yes',
                    answer='Synthetic office reply: appointments available next week', source='Fictional test receptionist',
                    checked_on=date.today().isoformat())
        data.update(changes)
        return self.call('/api/case/answer', data)

    def test_candidate_starts_unconfirmed_and_persists(self):
        result, provider = self.candidate()
        row = next(r for r in result['results'] if r['provider']['id'] == provider['id'])
        self.assertFalse(row['supported'])
        self.assertIsNone(row['cost']['amount'])
        self.call('/api/vault/lock', {})
        self.call('/api/vault/unlock', {'passphrase': 'disposable-test-passphrase'})
        self.assertEqual(self.app.get_case(self.case['id'])['providers'][-1]['url'], provider['url'])

    def test_invalid_or_duplicate_candidate_does_not_mutate(self):
        before = len(self.app.get_case(self.case['id'])['providers'])
        for url in ('javascript:alert(1)', 'https://user:pass@example.org'):
            with self.assertRaises(ValueError):
                self.candidate(url=url)
        self.assertEqual(len(self.app.get_case(self.case['id'])['providers']), before)
        self.candidate()
        with self.assertRaises(ValueError):
            self.candidate()

    def test_answer_is_scoped_and_stale_requires_reconfirmation(self):
        provider = self.case['providers'][0]
        result = self.answer(provider)
        row = next(r for r in result['results'] if r['provider']['id'] == provider['id'])
        self.assertNotIn('availability', [t['key'] for t in row['confirmation']])
        other = next(r for r in result['results'] if r['provider']['id'] != provider['id'])
        self.assertIn('availability', [t['key'] for t in other['confirmation']])
        # Latest same-date answer supersedes the earlier answer; older evidence cannot erase it.
        result = self.answer(provider, result='unknown', answer='Call back to confirm')
        row = next(r for r in result['results'] if r['provider']['id'] == provider['id'])
        self.assertIn('availability', [t['key'] for t in row['confirmation']])
        fresh_provider = self.case['providers'][1]
        result = self.answer(fresh_provider, checked_on=(date.today()-timedelta(days=31)).isoformat())
        row = next(r for r in result['results'] if r['provider']['id'] == fresh_provider['id'])
        self.assertTrue(row['answers']['availability']['stale'])
        self.assertIn('availability', [t['key'] for t in row['confirmation']])

    def test_no_availability_demotes_candidate_and_does_not_book(self):
        provider = self.case['providers'][0]
        result = self.answer(provider, result='no', answer='No new-patient appointments')
        self.assertEqual(result['results'][-1]['provider']['id'], provider['id'])
        self.assertTrue(result['results'][-1]['unavailable'])
        self.assertEqual(result['status'], 'comparing')

    def test_foreign_provider_and_future_answer_are_atomic(self):
        with self.assertRaises(ValueError):
            self.answer({'id': 'foreign'})
        with self.assertRaises(ValueError):
            self.answer(self.case['providers'][0], checked_on=(date.today()+timedelta(days=1)).isoformat())
        self.assertFalse(self.app.get_case(self.case['id'])['providers'][0].get('answers'))

    def test_private_replies_are_protected_and_probe_never_connects(self):
        self.answer(self.case['providers'][0], answer='Private synthetic follow-up detail')
        self.assertIn('confirmation_answers', dlp_violations({'query': 'Private synthetic follow-up detail'}, self.app.store.data))
        with patch('app.egress._OPENER.open', side_effect=AssertionError('Must never connect')):
            result = self.call('/api/privacy/probe', {})
        self.assertTrue(result['blocked'])
        self.assertFalse(result['network_called'])
        self.assertIn('DLP', self.app.store.data['ledger'][-1]['reason'])

    def test_cash_quote_expires(self):
        provider = {'cash': {'amount': 100, 'service': 'primary_care', 'scope_confirmed': True,
                            'checked_on': (date.today()-timedelta(days=31)).isoformat()}}
        self.assertIsNone(cash_cost(provider, 'primary_care')['amount'])


    def test_profile_source_metadata_and_forgetting_remove_derived_benefits(self):
        self.call('/api/profile', {'birth_year': 2000, 'conditions': ['Synthetic condition'], 'insurance': 'yes', 'plan': {'name': 'Old plan'}})
        profile = self.app.store.data['profile']
        self.assertTrue(profile['fact_sources']['conditions:Synthetic condition']['reviewed_on'])
        profile['plan_benefits'] = {'name': 'Old plan', 'services': {}}
        self.call('/api/profile/forget', {'field': 'plan'})
        self.assertNotIn('plan_benefits', profile)
        self.call('/api/profile/forget', {'field': 'conditions', 'value': 'Synthetic condition'})
        self.assertNotIn('conditions:Synthetic condition', profile['fact_sources'])


    def test_required_referral_stays_actionable_until_obtained(self):
        provider = self.case['providers'][0]
        result = self.answer(provider, key='referral', result='yes', answer='Referral required')
        row = next(r for r in result['results'] if r['provider']['id'] == provider['id'])
        self.assertIn('referral_action', [t['key'] for t in row['confirmation']])
        result = self.answer(provider, key='referral_action', result='no', answer='Not obtained yet')
        row = next(r for r in result['results'] if r['provider']['id'] == provider['id'])
        self.assertIn('referral_action', [t['key'] for t in row['confirmation']])
        result = self.answer(provider, key='referral_action', result='yes', answer='Synthetic authorization confirmed for this visit')
        row = next(r for r in result['results'] if r['provider']['id'] == provider['id'])
        self.assertNotIn('referral_action', [t['key'] for t in row['confirmation']])
