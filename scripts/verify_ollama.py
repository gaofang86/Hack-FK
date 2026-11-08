#!/usr/bin/env python3
"""PLAN.md section 9 acceptance for the local model, with synthetic data only.

Checks: loopback-only model endpoint, Chinese translation of the fixed call script
from the real installed model (private history is not sent to the model),
use with the app's offline switch on, labeled template fallback when the model is
unreachable, and unchanged cost comparison / no outbound requests during drafting.
Run it with Wi-Fi off to also record that the internet was unreachable.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import re
import socket
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Config  # noqa: E402
from app.server import App  # noqa: E402

PRIVATE = 'SYNTHETIC PRIVATE HISTORY SENTINEL'


def internet_reachable():
    """Run by this script, not the app: one TCP connect attempt to a public resolver."""
    try:
        socket.create_connection(('1.1.1.1', 443), timeout=3).close()
        return True
    except OSError:
        return False


def new_case(app):
    body = dict(city='Brookline', state='MA', zip='02445', insurance='no', service='primary_care',
                visit_date=date.today().isoformat(), adult=True, routine_confirmed=True, demo=False,
                language='Chinese', description=PRIVATE, history=PRIVATE)
    preview = app.dispatch('POST', '/api/preview', body, {})
    return app.dispatch('POST', '/api/search', {'token': preview['token'], 'approved': True, 'live': False}, {})


def comparison(app, ident):
    case = app.dispatch('GET', '/api/case', {}, {'id': [ident]})
    case.pop('preparation', None)
    return json.dumps(case, sort_keys=True, default=str)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='firstvisit-ollama-') as folder:
        cfg = Config(); cfg.store_path = Path(folder) / 'temporary.fv'; cfg.exa_key = cfg.tavily_key = ''
        app = App(cfg)
        app.store.create('disposable-test-passphrase')
        status = app.model.status()
        assert status['available'], f"Model not ready: {status['reason']}"

        case = new_case(app)
        provider = case['providers'][0]['id']
        before = comparison(app, case['id'])
        app.egress.offline = True  # public network blocked inside the app; loopback model still allowed
        ledger_before = len(app.store.data['ledger'])
        sent_to_model, call_local = [], app.egress.local
        def recording_local(method, url, **kw):
            sent_to_model.append(json.dumps(kw.get('json_body'), ensure_ascii=False))
            return call_local(method, url, **kw)
        app.egress.local = recording_local
        draft = app.dispatch('POST', '/api/case/preparation', {'id': case['id'], 'provider_id': provider, 'use_model': True}, {})
        assert draft['source'] == f'local model ({cfg.ollama_model})', draft
        chinese = len(re.findall(r'[一-鿿]', draft['text']))
        assert chinese >= 10, 'Draft is not in Chinese'
        assert comparison(app, case['id']) == before, 'Model drafting changed the comparison'
        assert len(app.store.data['ledger']) == ledger_before, 'Drafting created gateway traffic'
        assert PRIVATE not in ''.join(sent_to_model), 'Private history was sent to the model'
        assert 'Are you accepting new adult patients' in draft['text'] or 'accepting new adult patients' in draft['text']

        app.model.cfg.ollama_url = 'http://example.org:11434'  # non-loopback endpoint must be refused
        remote = app.dispatch('POST', '/api/case/preparation', {'id': case['id'], 'provider_id': provider, 'use_model': True}, {})
        assert remote['source'].startswith('built-in template') and 'localhost' in remote['fallback_reason']

        app.model.cfg.ollama_url = 'http://127.0.0.1:9'  # closed loopback port: model unreachable
        down = app.dispatch('POST', '/api/case/preparation', {'id': case['id'], 'provider_id': provider, 'use_model': True}, {})
        assert down['source'].startswith('built-in template') and down['fallback_reason']

    report = {'passed': True, 'synthetic_only': True, 'checked_at': date.today().isoformat(),
              'scope': 'Real local Ollama model called by the app in-process. Not a clinical review of draft content.',
              'model': cfg.ollama_model, 'loopback_only': True, 'non_loopback_endpoint_refused': True,
              'chinese_characters_in_draft': chinese, 'app_offline_mode_on': True,
              'internet_reachable_during_check': internet_reachable(),
              'private_history_sent_to_model': False, 'comparison_unchanged_by_model': True, 'gateway_requests_during_draft': 0,
              'unreachable_model_fell_back_to_labeled_template': True,
              'draft_excerpt': draft['text'][:240]}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
