"""Three coverage situations get different help; plan comparison is plain arithmetic."""
from pathlib import Path
import tempfile
import unittest

from app.config import Config
from app.scenarios import compare_plans, guidance, suggested_needs
from app.server import App
from tests.test_person_first import health_first


class GuidanceTests(unittest.TestCase):
    def test_each_situation_gets_its_own_help(self):
        a = guidance({"insurance": "yes", "plan": {"name": "P", "rule": "copay", "copay": 30}, "service": "same_day"})
        self.assertEqual(a["kind"], "insured")
        self.assertTrue(any("urgent care copay" in q for q in a["ask"]))
        self.assertIn("$30.00", a["known"][1]["value"])
        b = guidance({"insurance": "no", "wants_insurance": False, "service": "primary_care"})
        self.assertEqual(b["kind"], "uninsured")
        self.assertEqual(len(b["resources"]), 4)
        self.assertTrue(all(r["source"]["url"].startswith("https://") for r in b["resources"]))
        c = guidance({"insurance": "no", "wants_insurance": True})
        self.assertEqual(c["kind"], "choosing")
        self.assertTrue(c["compare"])

    def test_needs_are_suggested_from_profile(self):
        got = suggested_needs({"medications": ["Inhaler"], "conditions": ["Asthma"], "follow_ups": [{"what": "x"}]})
        self.assertEqual(got, {"primary": 3, "prescriptions": 12, "specialist": 2})


class CompareTests(unittest.TestCase):
    def plan(self, name, premium, oop, primary, rx):
        return {"name": name, "premium": premium, "oop_max": oop,
                "costs": {"primary": {"status": "covered", "cost": primary}, "prescriptions": {"status": "covered", "cost": rx}}}

    def test_yearly_total_and_best(self):
        r = compare_plans({"needs": {"primary": 3, "prescriptions": 12},
                           "plans": [self.plan("Low premium", 100, 5000, 50, 40), self.plan("High premium", 200, 3000, 10, 5)]})
        low, high = r["plans"]
        self.assertEqual(low["year_total"], 100 * 12 + 3 * 50 + 12 * 40)   # 1830
        self.assertEqual(high["year_total"], 200 * 12 + 3 * 10 + 12 * 5)   # 2490
        self.assertEqual(r["best"], "Low premium")

    def test_out_of_pocket_cap(self):
        r = compare_plans({"needs": {"primary": 10}, "plans": [self.plan("Capped", 0, 200, 50, 0)]})
        self.assertTrue(r["plans"][0]["capped"])
        self.assertEqual(r["plans"][0]["care_total"], 200)

    def test_unknown_or_uncovered_is_never_ranked(self):
        p = self.plan("Gap", 10, 1000, 10, 10)
        p["costs"]["prescriptions"] = {"status": "not_covered"}
        q = self.plan("Unsure", 10, 1000, 10, 10)
        q["costs"]["prescriptions"] = {"status": "unknown"}
        r = compare_plans({"needs": {"primary": 1, "prescriptions": 1}, "plans": [p, q]})
        self.assertIsNone(r["best"])
        self.assertEqual(r["plans"][0]["not_covered"], ["Prescription refills"])
        self.assertEqual(r["plans"][1]["unknown"], ["Prescription refills"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            compare_plans({"needs": {}, "plans": [{"name": "A"}]})
        with self.assertRaises(ValueError):
            compare_plans({"needs": {"primary": 1}, "plans": [{"name": ""}]})


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Config(); cfg.store_path = Path(self.tmp.name) / "vault.fv"; cfg.exa_key = ""; cfg.tavily_key = ""
        self.app = App(cfg)
        self.call("/api/vault/create", {"passphrase": "disposable-test-passphrase"})

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, path, body=None):
        return self.app.dispatch("GET" if body is None else "POST", path, body or {}, {})

    def test_results_carry_scenario_and_comparison_is_saved(self):
        token = self.call("/api/preview", health_first(insurance="no", wants_insurance=True))["token"]
        case = self.call("/api/search", {"token": token, "approved": True, "live": False})
        self.assertEqual(case["scenario"]["kind"], "choosing")
        body = {"needs": {"primary": 2}, "plans": [{"name": "A", "premium": 50, "costs": {"primary": {"status": "covered", "cost": 20}}}]}
        self.assertEqual(self.call("/api/plans/compare", body)["result"]["best"], "A")
        saved = self.call("/api/plans")
        self.assertEqual(saved["saved"]["plans"][0]["name"], "A")
        self.assertEqual(saved["result"]["plans"][0]["year_total"], 640)


if __name__ == "__main__":
    unittest.main()
