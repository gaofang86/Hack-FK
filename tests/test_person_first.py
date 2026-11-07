"""Person-first intake: health and a local safety check come before location and price."""
from pathlib import Path
import tempfile
import unittest

from app.config import Config
from app.server import App
from tests.test_navigation import person


def health_first(**changes):
    p = person()
    for legacy in ("adult", "routine_confirmed"):
        p.pop(legacy)
    p.update(age=28, checks=[], none_reported=True, severity="", description="")
    p.update(changes)
    return p


class PersonFirstTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Config(); cfg.store_path = Path(self.tmp.name) / "vault.fv"; cfg.exa_key = ""; cfg.tavily_key = ""
        self.app = App(cfg)

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, path, body=None):
        return self.app.dispatch("GET" if body is None else "POST", path, body or {}, {})

    def unlock(self):
        self.call("/api/vault/create", {"passphrase": "disposable-test-passphrase"})

    def test_safety_check_runs_without_vault_and_stores_nothing(self):
        result = self.call("/api/safety", {"checks": ["chest_pain"]})
        self.assertEqual(result["level"], "emergency")
        self.assertTrue(result["choices"])
        self.assertFalse(Path(self.tmp.name, "vault.fv").exists())

    def test_nothing_wrong_is_routine(self):
        self.assertEqual(self.call("/api/safety", {"checks": []})["level"], "routine")

    def test_free_text_red_flag_is_caught(self):
        result = self.call("/api/safety", {"checks": [], "description": "I have been thinking I want to kill myself"})
        self.assertEqual(result["level"], "emergency")
        self.assertIn("988", " ".join(h["how"] for h in result["hotlines"]))

    def test_emergency_cannot_reach_price_comparison(self):
        self.unlock()
        for body in (health_first(checks=["chest_pain"], none_reported=False),
                     health_first(checks=["injury"], none_reported=False),
                     health_first(checks=["severe_pain"], none_reported=False)):
            with self.assertRaises(ValueError):
                self.call("/api/preview", body)

    def test_age_replaces_adult_checkbox(self):
        self.unlock()
        with self.assertRaises(ValueError):
            self.call("/api/preview", health_first(age=16))
        token = self.call("/api/preview", health_first(age=28))["token"]
        case = self.call("/api/search", {"token": token, "approved": True, "live": False})
        self.assertEqual(case["input"]["age"], 28)
        self.assertEqual(case["input"]["safety"]["level"], "routine")

    def test_soon_level_continues_and_symptoms_join_dlp_terms(self):
        self.unlock()
        token = self.call("/api/preview", health_first(checks=["sore_throat"], none_reported=False))["token"]
        case = self.call("/api/search", {"token": token, "approved": True, "live": False})
        stored = self.app.store.data["cases"][case["id"]]
        self.assertIn("sore throat", stored["symptom_terms"])


if __name__ == "__main__":
    unittest.main()
