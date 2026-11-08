#!/usr/bin/env python3
"""Local acceptance for an explicitly supplied PDF. Output contains counts, never lab values."""
import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config
from app.server import App
from app.egress import dlp_violations
from tests.test_person_first import health_first


def verify(path):
    with tempfile.TemporaryDirectory(prefix='firstvisit-report-') as folder:
        cfg=Config();cfg.store_path=Path(folder)/'temporary.fv';cfg.exa_key=cfg.tavily_key=''
        app=App(cfg)
        def post(endpoint,**body):return app.dispatch('POST',endpoint,body,{})
        post('/api/vault/create',passphrase='disposable-source-check-only')
        app.egress.offline=True
        j=post('/api/journeys',kind='report',goal='Prepare questions for a visit using a report')
        preview=post('/api/reports/preview',journey_id=j['id'],file_name='Local demonstration report',pdf_base64=base64.b64encode(path.read_bytes()).decode())
        assert not app.store.data.get('reports')
        j=post('/api/reports/confirm',token=preview['token'],confirmed=True,rows=preview['rows'])
        assert len(j['reports'])==1
        assert all(row['evidence'] for row in j['reports'][0]['rows'])
        assert 'follow_ups' not in app.store.data['profile']
        intake=health_first();intake['demo']=False
        p=post('/api/preview',**intake,journey_id=j['id'])
        case=post('/api/search',token=p['token'],approved=True,live=False)
        assert case['id']==j['id'] and case['report_ids']==j['report_ids']
        note=post('/api/case/preparation',id=j['id'])
        values=[r['result'] for r in j['reports'][0]['rows']]
        assert all(v in note['personal_note'] for v in values)
        assert not any(v in note['text'] for v in values)
        assert dlp_violations({'query':values[0]},app.store.data)
        assert not app.store.data['ledger']
        count=len(values)
        post('/api/vault/lock');post('/api/vault/unlock',passphrase='disposable-source-check-only')
        assert len(app.journey_view(app.get_journey(j['id']))['reports'][0]['rows'])==count
        post('/api/reports/forget',report_id=j['reports'][0]['id'])
        after=app.journey_view(app.get_journey(j['id']))
        assert not after['reports'] and not any(v in after['personal_preparation'] for v in values)
        assert 'preparation' not in after
        post('/api/vault/lock')
    return dict(passed=True,checked_at_utc=datetime.now(timezone.utc).isoformat(),rows=count,
                review_before_save=True,same_journey_continued=True,report_did_not_create_diagnosis_or_follow_up=True,
                private_preparation_separate_from_booking=True,report_value_egress_blocked=True,
                encrypted_persistence=True,forget_removed_derived_preparation=True,external_requests=0,
                scope='Explicitly supplied text PDF, local app in-process, disposable encrypted vault, app offline mode. No lab values or file paths in this report. No browser, microphone or medical interpretation verified.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--pdf',type=Path,required=True);parser.add_argument('--out',type=Path)
    args=parser.parse_args();result=verify(args.pdf)
    if args.out:args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
