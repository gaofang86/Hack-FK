#!/usr/bin/env python3
"""Install a source copy into a fresh temporary venv, verify, then remove test-only files."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def run(command, cwd, timeout=180):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{command[1:]} failed:\n{result.stdout[-2000:]}\n{result.stderr[-3000:]}')
    return (result.stdout+result.stderr).strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'verification/install.json')
    args=parser.parse_args()
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='firstvisit-clean-install-') as folder:
        folder=Path(folder); source=folder/'source'; source.mkdir()
        for name in ('app','static','tests','scripts'):
            shutil.copytree(ROOT/name, source/name, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        for name in ('requirements.txt','run.py'):
            shutil.copy2(ROOT/name,source/name)
        env=folder/'venv'
        run([sys.executable,'-m','venv',str(env)],source)
        python=str(env/'bin/python')
        run([python,'-m','pip','install','--disable-pip-version-check','-r','requirements.txt'],source)
        tests=run([python,'-m','unittest','discover','-q'],source)
        audit=json.loads(run([python,'scripts/audit_egress.py'],source))
        if not audit['passed']: raise RuntimeError('Network import audit failed')
        run(['node','--check','static/app.js'],source)
        privacy=json.loads(run([python,'scripts/verify_privacy.py'],source))
        versions=run([python,'-m','pip','freeze'],source).splitlines()
        report={'passed':True,'checked_at_utc':datetime.now(timezone.utc).isoformat(),
                'scope':'Fresh temporary source copy and virtual environment; no .env, patient vault, model or real API credentials copied.',
                'python':sys.version.split()[0],'elapsed_seconds':round(time.monotonic()-started,1),
                'tests':tests,'network_import_audit':audit['passed'],'javascript_syntax':True,
                'privacy_receiver':privacy['passed'],'installed_dependencies':versions,
                'not_verified':['real Tavily/Exa APIs','Ollama','target-user interviews','current NUSHP cost sharing','clinician network participation']}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
