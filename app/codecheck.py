"""Static import audit for direct network libraries (not proof of runtime isolation).

Parses every module under app/ and lists imports of networking libraries.
server.py may import http.server (inbound, bound to 127.0.0.1) and nothing else.
"""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parent
NETWORK = {"urllib.request", "urllib3", "http.client", "socket", "smtplib", "ssl", "requests",
           "httpx", "aiohttp", "ftplib", "telnetlib", "websocket", "websockets", "asyncio.streams"}
ALLOWED = {"egress.py": NETWORK, "server.py": {"http.server", "socketserver"}}


def _imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
            for a in node.names:
                yield f"{node.module}.{a.name}"


def check():
    violations, scanned = [], []
    for path in sorted(APP.glob("*.py")):
        scanned.append(path.name)
        tree = ast.parse(path.read_text(), filename=path.name)
        allowed = ALLOWED.get(path.name, set())
        for name in _imports(tree):
            hit = next((n for n in NETWORK | {"http.server", "socketserver"}
                        if name == n or name.startswith(n + ".")), None)
            if hit and hit not in allowed:
                violations.append({"file": path.name, "import": name})
    return {"passed": not violations, "violations": violations, "scanned": scanned}
