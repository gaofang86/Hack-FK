"""Settings come from environment variables (or a .env file next to run.py).

Every external service has a base URL so tests can point it at local fakes.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:  # python-dotenv is optional
    pass


def _get(name, default=""):
    return os.getenv(name, default).strip()


class Config:
    def __init__(self):
        self.data_dir = Path(_get("FIRSTVISIT_DATA_DIR", str(ROOT / "data")))
        self.store_path = self.data_dir / "vault.fv"
        self.host = "127.0.0.1"           # never bind to a public interface
        self.port = int(_get("FIRSTVISIT_PORT", "8766"))

        # Search sponsors: used only to find places, never sent anything about your health.
        self.exa_key = _get("EXA_API_KEY")
        self.exa_base = _get("EXA_BASE_URL", "https://api.exa.ai")
        self.tavily_key = _get("TAVILY_API_KEY")
        self.tavily_base = _get("TAVILY_BASE_URL", "https://api.tavily.com")

        # Local model (Ollama) - must be on this machine
        self.ollama_url = _get("OLLAMA_URL", "http://127.0.0.1:11434")
        self.ollama_model = _get("OLLAMA_MODEL", "qwen2.5:3b")

        self.idle_lock_minutes = int(_get("IDLE_LOCK_MINUTES", "15"))

    # Hosts the egress guard will talk to. Anything else is refused.
    def allowed_hosts(self):
        hosts = set()
        for url in (self.exa_base, self.tavily_base):
            if url:
                hosts.add(urlparse(url).netloc.lower())
        return hosts

    def services(self):
        return {"exa": bool(self.exa_key), "tavily": bool(self.tavily_key),
                "ollama_model": self.ollama_model}
