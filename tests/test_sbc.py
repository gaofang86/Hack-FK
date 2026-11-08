"""Reading a plan's standard Summary of Benefits and Coverage, and using it."""
import base64
from pathlib import Path
import tempfile
import unittest

from app.config import Config
from app.expect import illustration
from app.sbc import parse_cost, parse_sbc, plan_for, read_upload, share
from app.server import App
from tests.test_person_first import health_first

SAMPLE = (Path(__file__).parent / "fixtures" / "sample_sbc.txt").read_text()


class ParseTests(unittest.TestCase):
    def test_reads_the_standard_rows(self):
        r = parse_sbc(SAMPLE)
        self.assertTrue(r["is_sbc"])
        self.assertEqual(r["fields"]["deductible"]["value"], 250)
        self.assertEqual(r["fields"]["oop_max"]["value"], 3000)
        self.assertEqual(r["fields"]["start"]["value"], "2026-08-15")
        self.assertEqual(r["fields"]["name"]["value"], "Fictional University Student Health Plan PPO")
        got = {k: v["cost"] for k, v in r["services"].items()}
        self.assertEqual(got["primary"], {"kind": "copay", "amount": 25, "after_deductible": False})
        self.assertEqual(got["urgent"]["amount"], 50)
        self.assertEqual(got["er"]["amount"], 150)
        self.assertEqual(got["preventive"], {"kind": "free"})
        self.assertEqual(got["mental"]["amount"], 25)
        for svc in r["services"].values():
            self.assertTrue(svc["evidence"])   # every value shows the line it came from

    def test_cost_phrases(self):
        self.assertEqual(parse_cost("Deductible, then 20% coinsurance 40% coinsurance"),
                         {"kind": "coinsurance", "pct": 20, "after_deductible": True})
        self.assertEqual(parse_cost("No charge 30% coinsurance"), {"kind": "free"})
        self.assertEqual(parse_cost("Not covered Not covered")["kind"], "not_covered")
        self.assertEqual(parse_cost("$1,250 copay/visit")["amount"], 1250)
        self.assertEqual(parse_cost("See your plan")["kind"], "unknown")

    def test_rejects_things_that_are_not_an_sbc(self):
        with self.assertRaises(ValueError):
            parse_sbc("Dear student, welcome to campus. " * 20)
        with self.assertRaises(ValueError):
            read_upload({"pdf_base64": base64.b64encode(b"not a pdf at all").decode()})

    def test_source_is_a_fingerprint_not_the_file(self):
        r = read_upload({"text": SAMPLE, "file_name": "plan.pdf"})
        self.assertEqual(len(r["source"]["sha256"]), 64)
        self.assertNotIn("text", r)


class UseTests(unittest.TestCase):
    benefits = {"name": "Fictional PPO", "start": "", "end": "", "deductible_remaining": 250, "oop_remaining": 3000,
                "services": {"primary": {"kind": "copay", "amount": 25}, "urgent": {"kind": "copay", "amount": 50},
                             "er": {"kind": "copay", "amount": 150}, "specialist": {"kind": "coinsurance", "pct": 20, "after_deductible": True}}}

    def test_plan_rule_per_visit_type(self):
        self.assertEqual(plan_for(self.benefits, "primary_care")["copay"], 25)
        self.assertEqual(plan_for(self.benefits, "same_day")["copay"], 50)

    def test_what_to_expect_uses_real_rows(self):
        rows = {r["venue"]: r["you_pay"] for r in illustration({"insurance": "yes", "benefits": self.benefits})["rows"]}
        self.assertEqual(rows, {"Urgent care clinic": 50, "Emergency room": 150})

    def test_share_math(self):
        self.assertEqual(share({"kind": "coinsurance", "pct": 20, "after_deductible": True}, 1000, 250, 3000)[0], 400)
        self.assertEqual(share({"kind": "coinsurance", "pct": 20, "after_deductible": True}, 1000, 250, 300)[0], 300)
        self.assertEqual(share({"kind": "not_covered"}, 300, 0, None)[0], 300)
        self.assertIsNone(share({"kind": "unknown"}, 300, 0, None)[0])


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

    def test_upload_review_save_and_use(self):
        r = self.call("/api/plan/sbc", {"text": SAMPLE, "file_name": "sbc.pdf"})
        self.assertNotIn("plan_benefits", self.app.store.data["profile"])   # nothing saved before review
        services = {k: v["cost"] for k, v in r["services"].items()}
        view = self.call("/api/plan/benefits", {"name": r["fields"]["name"]["value"], "start": "2026-08-15", "end": "2027-08-14",
                                                "deductible": 250, "deductible_used": 50, "oop_max": 3000,
                                                "services": services, "source": r["source"]})
        self.assertEqual(view["benefits"]["deductible_remaining"], 200)
        self.assertEqual(view["plan_by_service"]["same_day"]["copay"], 50)
        self.assertEqual(view["profile"]["insurance"], "yes")
        body = health_first(checks=["eye"], none_reported=False, service="same_day", insurance="yes",
                            plan=view["plan_by_service"]["same_day"])
        preview = self.call("/api/preview", body)
        rows = {x["venue"]: x["you_pay"] for x in preview["expect"]["illustration"]["rows"]}
        self.assertEqual(rows["Emergency room"], 150)
        case = self.call("/api/search", {"token": preview["token"], "approved": True, "live": False})
        known = {k["label"]: k["value"] for k in case["scenario"]["known"]}
        self.assertEqual(known["Urgent care"], "$50.00 copay")

    def test_used_more_than_deductible_is_refused(self):
        with self.assertRaises(ValueError):
            self.call("/api/plan/benefits", {"name": "X", "deductible": 100, "deductible_used": 200, "services": {}})


if __name__ == "__main__":
    unittest.main()
