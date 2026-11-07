"""Audit direct network imports. Usage: python scripts/audit_egress.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.codecheck import check

result = check()
print(json.dumps(result, indent=2))
sys.exit(0 if result["passed"] else 1)
