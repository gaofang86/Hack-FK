"""My health: overview, needs attention (report flags verbatim, due items, sourced checks) and plan direction."""
import base64
import json
from datetime import date
from pathlib import Path
import tempfile
import unittest

from app.config import Config
from app.server import App
from app.health_overview import overview, expected_use, plan_direction, FLAG_NOTE, UNKNOWN
from app.scenarios import NEEDS, compare_plans

DEMO = Path(__file__).resolve().parent.parent / "docs" / "demo" / "firstvisit-lab-demo.pdf"
TODAY = date(2026, 11, 8)
FORBIDDEN = ("you have", "abnormal", "your risk", "risk score:", "likely", "indicates", "means you")


def report(rows, rid="r1"):
    return {"id": rid, "label": "SYNTHETIC panel", "rows": rows, "source": {"reviewed_on": "2026-11-01"}}


class OverviewRules(unittest.TestCase):
    def test_flag_is_quoted_verbatim_with_a_question_not_a_diagnosis(self):
        rows = [{"name": "Marker A", "result": "0.52 mg/dL", "reference": "0.57-1.00", "flag": "Low"},
                {"name": "Marker B", "result": "98 mg/dL", "reference": "70-99", "flag": ""}]
        out = overview({"birth_year": 2002}, [report(rows)], TODAY)
        flags = out["attention"]["report_flags"]
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual((f["name"], f["result"], f["reference"], f["flag"]), ("Marker A", "0.52 mg/dL", "0.57-1.00", "Low"))
        self.assertEqual(f["note"], FLAG_NOTE)
        self.assertIn("Flag copied from the report, not a diagnosis", f["note"])
        self.assertIn("Marker A 0.52 mg/dL", f["ask"])
        self.assertTrue(f["ask"].endswith("?"))
        self.assertEqual(out["overview"]["reports"][0]["flagged"], 1)

    def test_no_diagnostic_wording_anywhere(self):
        rows = [{"name": "Marker A", "result": "9", "reference": "1-5", "flag": "High"}]
        profile = {"birth_year": 1975, "sex": "female", "conditions": ["SYNTHETIC item"], "medications": ["Med A"],
                   "follow_ups": [{"what": "Recheck labs", "due": "2026-11-01"}]}
        out = overview(profile, [report(rows)], TODAY)
        out.pop("scope")  # the disclaimer itself names what is not done
        text = json.dumps(out).lower()
        for word in FORBIDDEN:
            self.assertNotIn(word, text)

    def test_flags_are_never_derived_from_numbers(self):
        # Outside the range but the report printed no flag: nothing is listed.
        out = overview({}, [report([{"name": "X", "result": "500", "reference": "1-5", "flag": ""}])], TODAY)
        self.assertEqual(out["attention"]["report_flags"], [])

    def test_attention_lists_due_items_and_sourced_checks_only(self):
        profile = {"birth_year": 2000, "medications": ["Med A"], "refills": {"Med A": "2026-11-10"},
                   "follow_ups": [{"what": "Visit B", "due": "2026-11-01"}, {"what": "Later C", "due": "2027-06-01"}],
                   "done": {"flu": "2026-10-01"}}
        a = overview(profile, [], TODAY)["attention"]
        self.assertEqual({t["kind"] for t in a["due"]}, {"refill", "follow_up"})
        self.assertEqual([t["title"] for t in a["due"] if t["kind"] == "follow_up"], ["Visit B"])
        self.assertTrue(all(t.get("source", {}).get("url") for t in a["preventive"]))
        self.assertNotIn("flu", [t["id"] for t in a["preventive"]])
        self.assertIn("flu", [t["id"] for t in a["done"]])
        self.assertFalse(a["needs_birth_year"])
        self.assertTrue(overview({}, [], TODAY)["attention"]["needs_birth_year"])

    def test_overview_does_not_repeat_care_tasks(self):
        out = overview({"birth_year": 2000}, [], TODAY)
        self.assertNotIn("cases", json.dumps(out))
        self.assertEqual(set(out), {"overview", "attention", "plan_direction", "scope"})

    def test_expected_use_counts_from_facts_on_file(self):
        profile = {"medications": ["Med A", "Med B"], "conditions": ["SYNTHETIC item"],
                   "follow_ups": [{"what": "Get blood work", "due": ""}, {"what": "See clinician again", "due": ""}]}
        flagged = [report([{"name": "X", "result": "9", "reference": "1-5", "flag": "High"}])]
        use = {u["need"]: u for u in expected_use(profile, flagged)}
        self.assertEqual(use["primary"]["count"], 3)  # checkup + one visit follow-up + one visit to ask about the flag
        self.assertEqual(use["labs"]["count"], 1)
        self.assertEqual(use["prescriptions"]["count"], 24)
        self.assertEqual(use["specialist"]["count"], 2)
        self.assertTrue(all(len(u["basis"]) >= 1 for u in use.values()))
        self.assertTrue(set(use) <= set(NEEDS))
        self.assertEqual(expected_use({}, [])[0]["count"], 1)

    def test_needs_feed_the_plan_comparison(self):
        d = plan_direction({"medications": ["Med A"], "follow_ups": [{"what": "Lab test", "due": ""}]}, [])
        result = compare_plans({"needs": d["needs"], "plans": [{"name": "Plan X"}]})
        self.assertIn("Lab tests", result["needs"])
        self.assertIsNone(result["best"])  # nothing known about the plan: unranked, never $0

    def test_plan_direction_tips_follow_expected_use(self):
        low = [t["title"] for t in plan_direction({}, [])["look_for"]]
        self.assertTrue(any("little care" in t for t in low))
        heavy = [t["title"] for t in plan_direction({"medications": ["M"], "conditions": ["C"],
                                                     "follow_ups": [{"what": "Blood test", "due": ""}]}, [])["look_for"]]
        self.assertTrue(any("formulary" in t for t in heavy))
        self.assertTrue(any("Specialist" in t for t in heavy))
        self.assertTrue(any("lab" in t.lower() for t in heavy))

    def test_current_plan_uses_reviewed_sbc_and_unknown_is_never_zero(self):
        profile = {"insurance": "yes", "plan": {"name": "SYNTHETIC PPO"}, "medications": ["M"],
                   "follow_ups": [{"what": "Blood test", "due": ""}],
                   "plan_benefits": {"name": "SYNTHETIC PPO", "source": {"file": "sbc.pdf"},
                                     "services": {"primary": {"kind": "copay", "amount": 25.0}}}}
        rows = {c["need"]: c for c in plan_direction(profile, [])["current_plan"]}
        self.assertEqual(rows["primary"]["value"], "$25.00 copay")
        self.assertEqual(rows["primary"]["from"], "sbc.pdf")
        self.assertEqual(rows["labs"]["value"], UNKNOWN)
        self.assertEqual(rows["prescriptions"]["value"], UNKNOWN)
        self.assertEqual({c["value"] for c in rows.values()}, {"$25.00 copay", UNKNOWN})
        self.assertEqual(plan_direction({"insurance": "no"}, [])["current_plan"], [])


class HealthReportEndpoints(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); cfg = Config(); cfg.store_path = Path(self.tmp.name) / "vault.fv"
        cfg.exa_key = cfg.tavily_key = ""
        self.app = App(cfg); self.post("/api/vault/create", passphrase="synthetic-only-passphrase")
        self.pdf = base64.b64encode(DEMO.read_bytes()).decode()

    def tearDown(self): self.tmp.cleanup()
    def post(self, path, **data): return self.app.dispatch("POST", path, data, {})
    def get(self, path): return self.app.dispatch("GET", path, {}, {})

    def test_demo_report_added_from_my_health(self):
        self.post("/api/profile", birth_year=2002)
        p = self.post("/api/health/reports/preview", pdf_base64=self.pdf, file_name="firstvisit-lab-demo.pdf")
        self.assertTrue(p["for_health"])
        self.assertEqual(self.get("/api/health/overview")["overview"]["reports"], [])  # nothing saved before review
        with self.assertRaises(ValueError):
            self.post("/api/health/reports/confirm", token=p["token"], rows=p["rows"])  # explicit confirmation required
        out = self.post("/api/health/reports/confirm", token=p["token"], confirmed=True, rows=p["rows"])
        flags = out["attention"]["report_flags"]
        self.assertEqual([(f["name"], f["result"], f["reference"], f["flag"]) for f in flags],
                         [("Creatinine", "0.52 mg/dL", "0.57-1.00", "Low")])
        self.assertEqual(out["overview"]["reports"][0]["rows"], 17)
        saved = self.app.store.data["reports"]
        self.assertEqual(len(saved), 1)
        self.assertNotIn("pdf_base64", json.dumps(saved))
        self.assertEqual([c for c in self.app.store.data["cases"].values() if c.get("report_ids")], [])
        rid = next(iter(saved))
        self.post("/api/reports/forget", report_id=rid)
        self.assertEqual(self.get("/api/health/overview")["attention"]["report_flags"], [])

    def test_task_and_health_previews_do_not_cross(self):
        j = self.post("/api/journeys", kind="follow_up", goal="SYNTHETIC goal")
        task_preview = self.post("/api/reports/preview", journey_id=j["id"], pdf_base64=self.pdf, file_name="a.pdf")
        with self.assertRaises(ValueError):
            self.post("/api/health/reports/confirm", token=task_preview["token"], confirmed=True, rows=task_preview["rows"])
        health_preview = self.post("/api/health/reports/preview", pdf_base64=self.pdf, file_name="a.pdf")
        with self.assertRaises(Exception):
            self.post("/api/reports/confirm", token=health_preview["token"], confirmed=True, rows=health_preview["rows"])
        self.assertEqual(self.app.store.data.get("reports", {}), {})


if __name__ == "__main__":
    unittest.main()
