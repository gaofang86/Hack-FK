#!/usr/bin/env python3
"""Opt-in real Ollama acceptance using synthetic office replies and a disposable vault."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config
from app.server import App


def verify():
    with tempfile.TemporaryDirectory(prefix='firstvisit-agent-') as folder:
        cfg = Config()
        cfg.store_path = Path(folder) / 'synthetic.fv'
        cfg.exa_key = cfg.tavily_key = ''
        app = App(cfg)
        def post(path, **data):
            return app.dispatch('POST', path, data, {})
        post('/api/vault/create', passphrase='disposable-agent-test-only')
        token = post('/api/preview', city='Brookline', state='MA', zip='02445',
                     insurance='no', age=24, routine_confirmed=True, service='follow_up',
                     visit_date=date.today().isoformat(), language='Chinese')['token']
        case = post('/api/search', token=token, approved=True, live=False)
        provider = case['providers'][0]
        post('/api/offline', offline=True)
        status = app.model.status()
        report = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), model=status,
                      scope='Real local Ollama with app offline switch on, synthetic text only, disposable vault; no microphone, browser, live provider or insurer verification.', checks=[])
        raw_outputs = []
        structured = app.model.structured
        def observe(*args, **kwargs):
            output = structured(*args, **kwargs)
            raw_outputs.append(output)
            return output
        app.model.structured = observe
        samples = [
            ('这家诊所有中文翻译，但目前不收新病人。', 'proposal', {'language': 'yes', 'availability': 'no'}),
            ('这家诊所说暂时不确定能不能安排中文翻译。', 'proposal', {'language': 'unknown'}),
            ('诊所说需要转诊，但是我还没有拿到转诊。', 'proposal', {'referral': 'yes', 'referral_action': 'no'}),
            ('前台回复：可以安排普通话口译，暂不接诊初诊患者。', 'proposal', {'language': 'yes', 'availability': 'no'}),
            ('The office confirmed Mandarin interpretation is available, but they are not accepting new patients.', 'proposal', {'language': 'yes', 'availability': 'no'}),
            ('诊所说可以安排西班牙语翻译，但是不能提供中文翻译。', 'proposal', {'language': 'no'}),
            ('这家诊所有中文翻译吗？', 'unsupported', {}),
            ('我现在下一步应该做什么？', 'read', {}),
            ('帮我解释一下现在的费用，哪些还是未知的？', 'read', {}),
        ]
        for message, state, facts in samples:
            started = time.monotonic()
            try:
                result = post('/api/agent/turn', id=case['id'], provider_id=provider['id'], message=message)
            except ValueError as error:
                result = dict(state='invalid_output', error=str(error))
            extracted = {r['key']: r['result'] for r in result.get('replies', [])}
            # A question about unconfirmed language may be routed to the overview tool.
            valid_state = result['state'] == state or (message.endswith('吗？') and result['state'] == 'read')
            report['checks'].append(dict(input=message, state=result['state'], facts=extracted,
                                         passed=valid_state and extracted == facts, raw_output=raw_outputs[-1] if raw_outputs else None,
                                         elapsed_seconds=round(time.monotonic() - started, 2)))
        result = post('/api/agent/turn', id=case['id'], provider_id=provider['id'], message=samples[0][0])
        if result['state'] == 'proposal':
            saved = post('/api/agent/confirm', id=case['id'], token=result['token'], confirmed=True,
                         source='Synthetic office reply for local acceptance, not an actual clinic contact',
                         checked_on=date.today().isoformat(), results={r['key']: r['result'] for r in result['replies']})
            row = next(r for r in saved['case']['results'] if r['provider']['id'] == provider['id'])
            report['checks'].append(dict(name='confirmed two-fact workflow', passed=saved['saved'] == 2 and row['language_match'] and row['unavailable'] and row['cost']['amount'] is None))
        else:
            report['checks'].append(dict(name='confirmed two-fact workflow', passed=False))
        privacy = app.dispatch('GET', '/api/privacy', {}, {})
        report['external_attempts'] = privacy['attempted']
        report['passed'] = status['available'] and all(c['passed'] for c in report['checks']) and privacy['attempted'] == 0
        app.store.lock_vault()
        app.agent.clear()
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('verification/agent-local.json'))
    args = parser.parse_args()
    result = verify()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['passed'] else 1)
