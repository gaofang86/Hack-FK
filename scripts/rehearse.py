#!/usr/bin/env python3
"""Disposable rehearsal: fictional personal inputs, sourced NEU candidates, no public API calls."""
from datetime import date
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config
from app.server import App, serve


def main():
    with tempfile.TemporaryDirectory(prefix='firstvisit-rehearsal-') as folder:
        cfg = Config(); cfg.store_path = Path(folder)/'rehearsal.fv'; cfg.port=8767
        cfg.exa_key = cfg.tavily_key = ''
        app=App(cfg); app.preview_mode=True
        def post(path, data): return app.dispatch('POST', path, data, {})
        post('/api/vault/create', {'passphrase':'firstvisit-preview-only'})
        post('/api/profile', {'birth_year':2002,'language':'Chinese','insurance':'no'})
        intake=dict(city='Brookline',state='MA',zip='02445',insurance='yes',age=24,checks=[],
                    service='follow_up',visit_date=date.today().isoformat(),language='Chinese',scenario='neu_student',
                    plan={'name':'Northeastern University Student Health Plan (NUSHP) 2026–27 — exact product to confirm','rule':'copay'})
        token=post('/api/preview', intake)['token']
        post('/api/search', {'token':token,'approved':True,'live':False})
        print('Disposable rehearsal: fictional profile + real clinic sources, no real prices or confirmed network.',flush=True)
        print('Open home → Continue journey. Unlock phrase: firstvisit-preview-only',flush=True)
        serve(app)


if __name__=='__main__':main()
