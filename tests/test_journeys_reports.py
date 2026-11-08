"""Shared journeys, optional reports, review gating, persistence and egress boundaries."""
import base64
from copy import deepcopy
from datetime import date
import io
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from app.config import Config
from app.server import App
from app.egress import dlp_violations
from tests.test_person_first import health_first


def synthetic_pdf():
    writer = PdfWriter();page=writer.add_blank_page(612,792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 40 700 Td (Lab results) Tj 0 -20 Td (SYNTHETIC Marker 12.34 mg/dL 01) Tj 0 -20 Td (Normal: 1-20) Tj 0 -20 Td (Final) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    buf=io.BytesIO();writer.write(buf)
    return base64.b64encode(buf.getvalue()).decode()


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();cfg=Config();cfg.store_path=Path(self.tmp.name)/'vault.fv';cfg.exa_key=cfg.tavily_key=''
        self.app=App(cfg);self.post('/api/vault/create',passphrase='synthetic-only-passphrase')
    def tearDown(self):self.tmp.cleanup()
    def post(self,path,**data):return self.app.dispatch('POST',path,data,{})
    def get(self,path,**query):return self.app.dispatch('GET',path,{}, {k:[v] for k,v in query.items()})
    def task(self,kind='first_visit'):return self.post('/api/journeys',kind=kind,goal='SYNTHETIC personal goal sentinel')
    def attach(self,j):
        p=self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=synthetic_pdf(),file_name='synthetic.pdf')
        return p,self.post('/api/reports/confirm',token=p['token'],confirmed=True,rows=p['rows'])
    def test_all_scenarios_start_without_report_or_full_profile(self):
        for kind in ('general','first_visit','concern','report','follow_up'):
            j=self.task(kind);self.assertEqual(j['kind'],kind);self.assertEqual(j['reports'],[])
            self.assertIn('Questions for my clinician',j['personal_preparation'])
        self.assertEqual(len(self.get('/api/state')['cases']),5)
        self.assertFalse(self.get('/api/state')['profile_ready'])
    def test_review_is_required_and_report_does_not_create_medical_tasks(self):
        j=self.task('report');p=self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=synthetic_pdf())
        self.assertFalse(self.app.store.data.get('reports'))
        with self.assertRaises(ValueError):self.post('/api/reports/confirm',token=p['token'],rows=p['rows'])
        reviewed=self.post('/api/reports/confirm',token=p['token'],confirmed=True,rows=p['rows'])
        self.assertEqual(len(reviewed['reports']),1)
        self.assertNotIn('follow_ups',self.app.store.data['profile'])
        self.assertEqual(reviewed['status'],'planning')
        self.assertNotIn('SYNTHETIC personal',self.app.store.path.read_bytes().decode(errors='ignore'))
    def test_search_extends_same_task_without_sending_goal_or_report(self):
        j=self.task('report');p,j=self.attach(j)
        before_id=j['id'];raw=health_first();raw['demo']=False
        preview=self.post('/api/preview',**raw,journey_id=j['id'])
        for q in preview['queries']:
            self.assertNotIn('12.34',q['query']);self.assertNotIn('sentinel',q['query'])
        case=self.post('/api/search',token=preview['token'],approved=True,live=False)
        self.assertEqual(case['id'],before_id);self.assertEqual(len(case['report_ids']),1)
        self.assertEqual(case['goal'],j['goal'])
        note=self.post('/api/case/preparation',id=case['id'])
        self.assertIn('12.34 mg/dL',note['personal_note'])
        self.assertNotIn('12.34',note['text'])
        self.assertTrue(dlp_violations({'query':'12.34 mg/dL'},self.app.store.data))
        self.assertTrue(dlp_violations({'query':j['goal']},self.app.store.data))
    def test_forget_clears_report_and_derived_preparation_then_cannot_restore(self):
        j=self.task();_,j=self.attach(j);rid=j['reports'][0]['id']
        self.app.get_journey(j['id'])['preparation']={'personal_note':'12.34 mg/dL'}
        self.post('/api/reports/forget',report_id=rid)
        j=self.get('/api/journey',id=j['id'])
        self.assertEqual(j['reports'],[]);self.assertNotIn('12.34',j['personal_preparation']);self.assertNotIn('preparation',j)
        self.post('/api/vault/lock');self.post('/api/vault/unlock',passphrase='synthetic-only-passphrase')
        self.assertEqual(self.get('/api/journey',id=j['id'])['reports'],[])
    def test_lock_and_forget_everything_clear_drafts_and_saved_reports(self):
        j=self.task();p,j=self.attach(j)
        self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=synthetic_pdf())
        self.post('/api/vault/lock');self.assertFalse(self.app.report_previews)
        self.post('/api/vault/unlock',passphrase='synthetic-only-passphrase')
        self.post('/api/profile/forget',field='everything')
        self.assertFalse(self.app.store.data.get('reports'));self.assertFalse(self.app.store.data['cases'])
    def test_task_goal_cannot_bypass_emergency_or_same_day_guard(self):
        emergency=self.post('/api/journeys',kind='first_visit',goal='I have chest pain')
        self.assertEqual(emergency['safety_notice']['level'],'emergency')
        raw=health_first();raw['demo']=False
        with self.assertRaises(ValueError):self.post('/api/preview',**raw,journey_id=emergency['id'])
        today=self.post('/api/journeys',kind='concern',goal='I have a current concern')
        same_day=health_first(checks=['high_fever'],none_reported=False)
        same_day['demo']=False
        with self.assertRaises(ValueError):self.post('/api/preview',**same_day,journey_id=today['id'])

    def test_invalid_reports_and_mismatched_review_do_not_mutate(self):
        j=self.task();before=deepcopy(self.app.store.data)
        for encoded in ('not-base64',base64.b64encode(b'not PDF').decode()):
            with self.assertRaises(ValueError):self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=encoded)
        self.assertEqual(before,self.app.store.data)
        p=self.post('/api/reports/preview',journey_id=j['id'],pdf_base64=synthetic_pdf())
        with self.assertRaises(ValueError):self.post('/api/reports/confirm',token=p['token'],confirmed=True,rows=[])
        self.assertFalse(self.app.store.data.get('reports'))
