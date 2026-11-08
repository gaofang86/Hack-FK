"""The health profile accumulates in the vault and drives sourced to-dos."""
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

from app.config import Config
from app.egress import protected_values
from app.health import clean_profile, todos
from app.server import App
from tests.test_person_first import health_first

TODAY = date(2026, 11, 7)


def ids(profile, today=TODAY):
    return {t["id"] for t in todos(profile, today)}


class RuleTests(unittest.TestCase):
    def test_age_and_sex_rules(self):
        woman28 = clean_profile({"birth_year": 1998, "sex": "female"}, TODAY)
        got = ids(woman28)
        self.assertTrue({"bp", "mood", "hiv", "hepc", "cervical", "flu", "tdap"} <= got)
        self.assertNotIn("breast", got)      # 40-74
        self.assertNotIn("colon", got)       # 45-75
        self.assertNotIn("hpv", got)         # routine through 26
        self.assertNotIn("cervical", ids(clean_profile({"birth_year": 1998}, TODAY)))  # sex not given
        self.assertTrue({"breast", "colon"} <= ids(clean_profile({"birth_year": 1976, "sex": "female"}, TODAY)))
        self.assertIn("hpv", ids(clean_profile({"birth_year": 2004}, TODAY)))

    def test_every_preventive_item_names_a_source(self):
        for t in todos(clean_profile({"birth_year": 1976, "sex": "female"}, TODAY), TODAY):
            self.assertTrue(t["source"]["url"].startswith("https://"), t["id"])

    def test_refills_and_follow_ups_become_personal_todos(self):
        p = clean_profile({"birth_year": 1998, "medications": [{"name": "Inhaler", "refill_by": (TODAY + timedelta(days=5)).isoformat()},
                                                              {"name": "Vitamin D", "refill_by": (TODAY + timedelta(days=60)).isoformat()}],
                           "follow_ups": [{"what": "Asthma check", "due": (TODAY - timedelta(days=2)).isoformat()}]}, TODAY)
        items = {t["id"]: t for t in todos(p, TODAY)}
        self.assertIn("refill:Inhaler", items)
        self.assertNotIn("refill:Vitamin D", items)
        self.assertTrue(items["follow:Asthma check"]["urgent"])

    def test_validation(self):
        for bad in ({"birth_year": 1800}, {"sex": "other-value"}, {"insurance": "maybe"},
                    {"medications": [{"name": "X", "refill_by": "soon"}]}):
            with self.assertRaises(ValueError):
                clean_profile(bad, TODAY)


class ProfileApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Config(); cfg.store_path = Path(self.tmp.name) / "vault.fv"; cfg.exa_key = ""; cfg.tavily_key = ""
        self.cfg, self.app = cfg, App(cfg)
        self.call("/api/vault/create", {"passphrase": "disposable-test-passphrase"})

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, path, body=None):
        return self.app.dispatch("GET" if body is None else "POST", path, body or {}, {})

    def test_profile_persists_and_is_not_overwritten_by_search(self):
        self.call("/api/profile", {"birth_year": 1998, "conditions": "Asthma, Migraine", "allergies": ["Penicillin"],
                                   "medications": [{"name": "Inhaler"}], "follow_ups": [{"what": "Asthma check"}]})
        self.call("/api/vault/lock", {})
        self.call("/api/vault/unlock", {"passphrase": "disposable-test-passphrase"})
        token = self.call("/api/preview", health_first())["token"]
        self.call("/api/search", {"token": token, "approved": True, "live": False})
        view = self.call("/api/profile")
        self.assertEqual(view["profile"]["conditions"], ["Asthma", "Migraine"])
        self.assertEqual(view["profile"]["medications"], ["Inhaler"])
        self.assertTrue(view["complete"])
        self.assertTrue(self.call("/api/state")["profile_ready"])

    def test_profile_values_are_protected_from_egress(self):
        self.call("/api/profile", {"birth_year": 1998, "conditions": ["Asthma"], "follow_ups": [{"what": "Kidney follow-up"}]})
        fields = {(p.field, p.value) for p in protected_values(self.app.store.data)}
        self.assertIn(("conditions", "Asthma"), fields)
        self.assertIn(("follow_ups", "Kidney follow-up"), fields)

    def test_todo_done_and_forget(self):
        self.call("/api/profile", {"birth_year": 1998, "conditions": ["Asthma"]})
        view = self.call("/api/profile/todo", {"id": "flu", "done": True})
        self.assertTrue(next(t for t in view["todos"] if t["id"] == "flu")["done_on"])
        view = self.call("/api/profile/forget", {"field": "conditions", "value": "Asthma"})
        self.assertEqual(view["profile"]["conditions"], [])
        view = self.call("/api/profile/forget", {"field": "everything"})
        self.assertFalse(view["complete"])
        self.assertEqual(self.call("/api/state")["cases"], [])

    def test_start_over_needs_confirmation_and_erases(self):
        self.call("/api/profile", {"birth_year": 1998})
        self.call("/api/vault/lock", {})
        with self.assertRaises(ValueError):
            self.call("/api/vault/reset", {})
        state = self.call("/api/vault/reset", {"confirm": "erase"})
        self.assertFalse(state["vault_exists"])
        self.assertFalse(Path(self.cfg.store_path).exists())

    def test_preview_mode_does_not_idle_lock(self):
        self.app.preview_mode = True
        self.app.store.last_activity -= 10 ** 6
        self.assertTrue(self.call("/api/state")["unlocked"])
        self.app.preview_mode = False
        self.assertFalse(self.call("/api/state")["unlocked"])


if __name__ == "__main__":
    unittest.main()
