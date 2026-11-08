#!/usr/bin/env python3
"""Observe a separate app process from a local receiver; never use real patient data or APIs.

This is receiver-side observation of controlled loopback traffic, not an OS-wide
packet capture or proof of production process isolation.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def worker(folder, base):
    from datetime import date
    from app.config import Config
    from app.server import App
    from app.egress import EgressBlocked, EgressError
    cfg = Config(); cfg.store_path = Path(folder) / 'temporary.fv'
    cfg.exa_key = ''; cfg.tavily_key = 'synthetic-receiver-key'; cfg.tavily_base = base
    app = App(cfg)
    app.store.create('disposable-test-passphrase')
    private = 'SYNTHETIC PRIVATE HEALTH SENTINEL'
    app.store.data['profile']['conditions'] = [private]
    body = dict(city='Brookline', state='MA', zip='02445', insurance='no', service='primary_care',
                visit_date=date.today().isoformat(), adult=True, routine_confirmed=True, demo=False,
                description=private)
    preview = app.dispatch('POST', '/api/preview', body, {})
    result = app.dispatch('POST', '/api/search', {'token': preview['token'], 'approved': True, 'live': True}, {})
    before = len(app.store.data['ledger'])
    for url, headers, payload in ((base+'/search?note=SYNTHETIC%20PRIVATE%20HEALTH%20SENTINEL', {}, {}),
                                  (base+'/search', {'x-note': private}, {}),
                                  (base+'/search', {}, {'query': private})):
        try:
            app.egress.http('POST', url, service='Receiver test', purpose='Synthetic leak attempt', headers=headers, json_body=payload)
            raise AssertionError('Sensitive request was not blocked')
        except EgressBlocked:
            pass
    for path in ('/fail', '/redirect'):
        try:
            app.egress.http('POST', base+path, service='Receiver test', purpose='Failure/redirect test', json_body={'query': 'public clinic lookup'})
            raise AssertionError('Expected failure or refused redirect')
        except EgressError:
            pass
    app.egress.offline = True
    try:
        app.egress.http('POST', base+'/offline', service='Receiver test', purpose='Offline test')
        raise AssertionError('Offline request escaped')
    except EgressBlocked:
        pass
    prep = app.dispatch('POST', '/api/case/preparation', {'id': result['id'], 'provider_id': result['providers'][0]['id']}, {})
    ledger = app.store.data['ledger']
    assert len(ledger) >= before+6 and prep['source'] == 'built-in template'
    assert app.dispatch('GET', '/api/case', {}, {'id': [result['id']]})['providers']
    Path(folder, 'worker.json').write_text(json.dumps({'live_search': result['live_searched'],
        'ledger_sent': sum(e['status']=='sent' for e in ledger), 'ledger_errors': sum(e['status']=='error' for e in ledger),
        'ledger_blocks': sum(e['status']=='blocked' for e in ledger), 'offline_preparation': True}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--worker', nargs=2, metavar=('FOLDER', 'BASE'))
    args = parser.parse_args()
    if args.worker:
        worker(*args.worker); return
    seen = []
    class Receiver(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            payload = self.rfile.read(int(self.headers.get('Content-Length', '0'))).decode()
            seen.append({'path': self.path, 'payload': payload, 'headers': dict(self.headers)})
            if self.path == '/redirect':
                self.send_response(302); self.send_header('Location', '/escaped'); self.end_headers(); return
            self.send_response(503 if self.path == '/fail' else 200)
            self.send_header('Content-Type', 'application/json'); self.end_headers()
            self.wfile.write(json.dumps({'results': [{'url': 'https://example.org/synthetic-clinic', 'title': 'Synthetic receiver clinic', 'content': 'Primary care near Brookline 02445.'}]}).encode())
    with tempfile.TemporaryDirectory(prefix='firstvisit-privacy-') as folder:
        receiver = ThreadingHTTPServer(('127.0.0.1', 0), Receiver)
        threading.Thread(target=receiver.serve_forever, daemon=True).start()
        try:
            subprocess.run([sys.executable, __file__, '--worker', folder, f'http://127.0.0.1:{receiver.server_port}'], check=True, timeout=60, capture_output=True)
        finally:
            receiver.shutdown(); receiver.server_close()
        app_result = json.loads(Path(folder, 'worker.json').read_text())
    observed = json.dumps(seen)
    assert 'PRIVATE' not in observed
    assert all(r['path'] in ('/search', '/fail', '/redirect') for r in seen)
    assert sum(r['path']=='/search' for r in seen) >= 1
    assert app_result['ledger_errors'] == 2 and app_result['ledger_blocks'] == 4
    report = {'passed': True, 'scope': 'Independent receiver in parent process observes a separate app process over loopback. Not OS-wide capture or live external API validation.',
              'synthetic_only': True, 'receiver_requests': len(seen), 'receiver_paths': [r['path'] for r in seen],
              'private_sentinel_received': False, 'redirect_followed': False, 'offline_request_received': False, **app_result}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
