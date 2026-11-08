"""Agent boundary, atomic review, local protocol and confirmation-to-ranking tests."""
from copy import deepcopy
from datetime import date, timedelta
import json
from unittest.mock import patch
import unittest

from app.agent import SCHEMA
from app.egress import EgressError
from tests import test_neu_scenario as fixtures


class AgentTests(unittest.TestCase):
    setUp = fixtures.NeuScenarioTests.setUp
    tearDown = fixtures.NeuScenarioTests.tearDown
    call = fixtures.NeuScenarioTests.call

    def turn(self, output=None, **kwargs):
        body = dict(id=self.case['id'], provider_id=self.case['providers'][0]['id'],
                    message='这家诊所有中文翻译，但目前不收新病人。')
        body.update(kwargs)
        output = output or dict(action='propose_reply', replies=[
            dict(key='language', result='yes', evidence='有中文翻译'),
            dict(key='availability', result='no', evidence='目前不收新病人')])
        with patch.object(self.app.agent.model, 'structured', return_value=output):
            return self.call('/api/agent/turn', body)

    def confirm(self, draft, **kwargs):
        body = dict(id=self.case['id'], token=draft['token'], confirmed=True,
                    results={r['key']: r['result'] for r in draft['replies']},
                    source='Synthetic office reply', checked_on=date.today().isoformat())
        body.update(kwargs)
        return self.call('/api/agent/confirm', body)

    def test_chinese_two_fact_review_then_ranking_and_persistence(self):
        before = deepcopy(self.app.get_case(self.case['id']))
        draft = self.turn()
        self.assertEqual(draft['state'], 'proposal')
        self.assertEqual(before, self.app.get_case(self.case['id']))
        result = self.confirm(draft)
        self.assertEqual(result['saved'], 2)
        rows = result['case']['results']
        changed = rows[-1]
        self.assertEqual(changed['provider']['id'], draft['provider']['id'])
        self.assertTrue(changed['language_match'])
        self.assertTrue(changed['unavailable'])
        self.assertNotIn('language', [q['key'] for q in changed['confirmation']])
        self.assertIsNone(changed['cost']['amount'])
        self.call('/api/vault/lock', {})
        self.call('/api/vault/unlock', {'passphrase': 'disposable-test-passphrase'})
        self.assertEqual(len(self.app.get_case(self.case['id'])['providers'][0]['answers']), 2)

    def test_invalid_review_is_atomic_and_token_replay_refused(self):
        draft = self.turn()
        for changes in ({'confirmed': False}, {'source': ''}, {'checked_on': '2999-01-01'},
                        {'results': {'insurance': 'yes'}}, {'results': {}}):
            with self.assertRaises(ValueError):
                self.confirm(draft, **changes)
            self.assertFalse(self.app.get_case(self.case['id'])['providers'][0].get('answers'))
        self.confirm(draft, results={'language': 'unknown'})
        with self.assertRaises(ValueError):
            self.confirm(draft)

    def test_question_cannot_be_saved_even_when_model_proposes_a_reply(self):
        result = self.turn(dict(action='propose_reply', replies=[dict(key='language', result='yes', evidence='有中文翻译')]), message='这家诊所有中文翻译吗？')
        self.assertEqual(result['state'], 'unsupported')
        self.assertFalse(self.app.agent.pending)

    def test_untrusted_model_cannot_select_tools_or_invent_evidence(self):
        for output in (dict(action='book', replies=[]),
                       dict(action='propose_reply', replies=[dict(key='insurance', result='yes', evidence='有中文翻译')]),
                       dict(action='propose_reply', replies=[dict(key='language', result='yes', evidence='made up')]),
                       dict(action='costs', replies=[dict(key='language', result='yes', evidence='有中文翻译')]),
                       dict(action='propose_reply', replies=[dict(key='language', result='yes', evidence='有中文翻译', price=0)])):
            with self.assertRaises(ValueError):
                self.turn(output)
        with self.assertRaises(ValueError):
            self.turn(provider_id='foreign')
        self.assertFalse(self.app.get_case(self.case['id'])['providers'][0].get('answers'))

    def test_changed_expired_superseded_and_locked_proposals_refused(self):
        draft = self.turn()
        self.app.get_case(self.case['id'])['input']['language'] = 'Spanish'
        with self.assertRaises(ValueError):
            self.confirm(draft)
        draft = self.turn()
        self.app.agent.pending[draft['token']]['expires'] = 0
        with self.assertRaises(ValueError):
            self.confirm(draft)
        draft = self.turn()
        self.turn()
        with self.assertRaises(ValueError):
            self.confirm(draft)
        self.call('/api/vault/lock', {})
        self.assertFalse(self.app.agent.pending)

    def test_reads_work_offline_without_model_and_do_not_mutate_case(self):
        self.call('/api/offline', {'offline': True})
        before = deepcopy(self.app.get_case(self.case['id']))
        with patch.object(self.app.agent.model, 'structured', side_effect=AssertionError('must not call model')):
            for tool in ('overview', 'costs'):
                result = self.call('/api/agent/turn', {'id': self.case['id'], 'tool': tool})
                self.assertEqual(result['state'], 'read')
                self.assertTrue(all(r['cost']['amount'] is None for r in result['rows']))
        self.assertEqual(before, self.app.get_case(self.case['id']))

    def test_model_failure_is_honest_and_local_chat_protocol_is_scoped(self):
        with patch.object(self.app.agent.model, 'structured', side_effect=EgressError('offline local service')):
            result = self.call('/api/agent/turn', {'id': self.case['id'], 'message': '下一步？'})
        self.assertEqual(result['state'], 'unavailable')
        self.assertFalse(self.app.agent.pending)
        with patch.object(self.app.egress, 'local', return_value={'message': {'content': json.dumps({'action': 'overview', 'replies': []})}}) as local:
            self.app.agent.model.structured('下一步？', SCHEMA, 'system')
            args, kw = local.call_args
            self.assertTrue(args[1].endswith('/api/chat'))
            self.assertEqual(kw['json_body']['format'], SCHEMA)
            self.assertNotIn('NUSHP', json.dumps(kw['json_body']))
            self.assertFalse(kw['json_body']['stream'])
            self.assertIs(kw['json_body']['think'], False)

    def test_language_answer_changes_fit_but_not_cost_priority_and_expires(self):
        case = self.app.get_case(self.case['id'])
        case['input'].update(language='Chinese', priority='balanced', insurance='no')
        first, second = case['providers'][:2]
        for p in (first, second):
            p['services'] = [case['input']['service']]
            p['languages'] = []
        first['cash'] = dict(amount=100, service=case['input']['service'], scope_confirmed=True,
                             checked_on=date.today().isoformat(), source='Synthetic')
        second['cash'] = dict(first['cash'], amount=200)
        output = dict(action='propose_reply', replies=[dict(key='language', result='yes', evidence='有中文翻译')])
        draft = self.turn(output, provider_id=second['id'])
        result = self.confirm(draft)
        self.assertEqual(result['case']['results'][0]['provider']['id'], second['id'])
        self.assertIn('user-recorded', result['case']['results'][0]['reasons'][1])
        case['input']['priority'] = 'cost'
        self.assertEqual(self.app.shown(case)['results'][0]['provider']['id'], first['id'])
        case['input']['priority'] = 'balanced'
        second['answers'][0]['checked_on'] = (date.today() - timedelta(days=31)).isoformat()
        row = next(r for r in self.app.shown(case)['results'] if r['provider']['id'] == second['id'])
        self.assertFalse(row['language_match'])
        self.assertIn('language', [q['key'] for q in row['confirmation']])
        second['languages'] = ['Chinese']
        second['answers'][0].update(checked_on=date.today().isoformat(), result='no')
        row = next(r for r in self.app.shown(case)['results'] if r['provider']['id'] == second['id'])
        self.assertFalse(row['language_match'])
