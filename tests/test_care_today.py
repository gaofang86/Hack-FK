"""Same-day care path and the deterministic 'what to expect' page."""
from datetime import date
from pathlib import Path
import tempfile
import unittest

from app.config import Config
from app.expect import EXAMPLE_FEES, expectations, illustration
from app.server import App
from tests.test_person_first import health_first


def plan(**changes):
    base = dict(name="Demo Student PPO", rule="deductible", start=date.today().isoformat(), end="",
                deductible_remaining=100, coinsurance=20, oop_remaining=3000, copay=None, premium=None, eligible=False)
    base.update(changes)
    return base


class CareTodayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Config(); cfg.store_path = Path(self.tmp.name) / "vault.fv"; cfg.exa_key = ""; cfg.tavily_key = ""
        self.app = App(cfg)
        self.app.dispatch("POST", "/api/vault/create", {"passphrase": "disposable-test-passphrase"}, {})

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, path, body):
        return self.app.dispatch("POST", path, body, {})

    def test_same_day_needs_care_today_choice(self):
        with self.assertRaises(ValueError):
            self.call("/api/preview", health_first(checks=["eye"], none_reported=False))

    def test_same_day_reaches_urgent_care_results_and_expectations(self):
        body = health_first(checks=["eye"], none_reported=False, service="same_day")
        preview = self.call("/api/preview", body)
        self.assertEqual(preview["expect"]["options"][0]["id"], "urgent_care")
        self.assertIsNotNone(preview["expect"]["illustration"])
        case = self.call("/api/search", {"token": preview["token"], "approved": True, "live": False})
        kinds = {r["provider"]["kind"] for r in case["results"]}
        self.assertIn("Urgent care clinic", kinds)
        self.assertNotIn("Doctor's office", kinds)

    def test_emergency_still_blocked_even_when_choosing_care_today(self):
        with self.assertRaises(ValueError):
            self.call("/api/preview", health_first(checks=["chest_pain"], none_reported=False, service="same_day"))

    def test_real_same_day_has_no_invented_directory(self):
        body = health_first(checks=["eye"], none_reported=False, service="same_day", demo=False)
        preview = self.call("/api/preview", body)
        case = self.call("/api/search", {"token": preview["token"], "approved": True, "live": False})
        self.assertEqual(case["results"], [])

    def test_illustration_math_is_deterministic(self):
        rows = {r["venue"]: r for r in illustration({"insurance": "yes", "plan": plan()})["rows"]}
        # $300 example: $100 deductible + 20% of $200 = $140. $1,000: $100 + 20% of $900 = $280.
        self.assertEqual(rows["Urgent care clinic"]["you_pay"], 140)
        self.assertEqual(rows["Emergency room"]["you_pay"], 280)
        capped = {r["venue"]: r for r in illustration({"insurance": "yes", "plan": plan(oop_remaining=200)})["rows"]}
        self.assertEqual(capped["Emergency room"]["you_pay"], 200)

    def test_copay_plan_does_not_guess_er_cost(self):
        rows = {r["venue"]: r for r in illustration({"insurance": "yes", "plan": plan(rule="copay", copay=35)})["rows"]}
        self.assertEqual(rows["Urgent care clinic"]["you_pay"], 35)
        self.assertIsNone(rows["Emergency room"]["you_pay"])

    def test_uninsured_sees_full_example_fee_and_gfe_source(self):
        result = expectations({"insurance": "no", "service": "same_day"})
        self.assertEqual([r["you_pay"] for r in result["illustration"]["rows"]], list(EXAMPLE_FEES.values()))
        self.assertTrue(any("cms.gov" in s["url"] for s in result["sources"]))


if __name__ == "__main__":
    unittest.main()
