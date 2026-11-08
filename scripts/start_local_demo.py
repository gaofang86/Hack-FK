#!/usr/bin/env python3
"""Persistent private local demo; no preset passphrase, no public search credentials.

Report PDFs are selected by the user in the UI. No personal report is bundled or
read by this launcher. Existing sessions on port 8767 are left alone.
"""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Config
from app.server import App, serve

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8768)
    parser.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[2]/'local-demo-assets'/'private-state')
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Choose a valid port')
    cfg=Config();cfg.port=args.port;cfg.data_dir=args.data_dir;cfg.store_path=args.data_dir/'vault.fv';cfg.exa_key=cfg.tavily_key=''
    print('Private local demo. Choose your own vault passphrase; no public search credentials loaded.',flush=True)
    print('Optional browser-service dictation has a separate disclosure; it is not app-gateway traffic.',flush=True)
    serve(App(cfg))
