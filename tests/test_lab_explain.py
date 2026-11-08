"""Local-model lab explanations: strict structure, checked against the MedlinePlus fact sheet, fact-sheet fallback."""
from pathlib import Path
import tempfile
import unittest

from app import explain
from app.config import Config
from app.server import App

CREAT = dict(name="Creatinine", result="0.52 mg/dL", reference="0.57-1.00", flag="Low")
GOOD_EN = ("[MEANING]\nThis test measures a waste product from muscles that the kidneys filter out. A low result is often "
           "linked to less muscle mass or low food intake.\n[WHEN]\nBring it up at your next routine visit.\n[STEPS]\n"
           "- Eat regular, balanced meals with enough protein.\n- Do muscle-strengthening activity at least 2 days a week.")
GOOD_ZH = ("[MEANING]\n肌酐是肌肉代谢产生的正常废物，由肾脏过滤排出。偏低的结果通常与肌肉量较少或饮食摄入不足有关。\n[WHEN]\n下次常规就诊时问医生。\n"
           "[STEPS]\n- 均衡饮食，摄入足够蛋白质。\n- 每周至少 2 天做肌肉锻炼。")


class Stub:
    model_name = "stub-local"

    def __init__(self, reply="", available=True):
        self.reply, self.available, self.prompts = reply, available, []

    def status(self):
        return {"available": self.available, "reason": "" if self.available else "Run: ollama pull stub"}

    def generate(self, prompt, system, n):
        self.prompts.append((prompt, system))
        return self.reply


class LabExplain(unittest.TestCase):
    def test_structured_answer_passes_and_prompt_is_strict(self):
        stub = Stub(GOOD_EN)
        r = explain.explain_report(stub, [CREAT, dict(name="Glucose", result="98", reference="70-99", flag="")], "en")
        x = r["explanations"][0]
        self.assertIn("less muscle mass", x["meaning"])
        self.assertEqual(len(x["steps"]), 2)
        self.assertIn("checked against the MedlinePlus fact sheet", r["source"])
        prompt, system = stub.prompts[0]
        self.assertIn("[MEANING]", system); self.assertIn("never about what this person has", system)
        self.assertIn("Fact sheet (fixed)", prompt); self.assertNotIn("Glucose", prompt)  # only the flagged row is sent
        self.assertEqual(len(stub.prompts), 1)

    def test_chinese_answer_must_be_in_chinese(self):
        self.assertIsNotNone(explain.explain_report(Stub(GOOD_ZH), [CREAT], "zh")["explanations"][0])
        self.assertIsNone(explain.explain_report(Stub(GOOD_EN), [CREAT], "zh")["explanations"][0])

    def test_rejects_clearance_diagnosis_new_numbers_conditions_urgency_and_broken_structure(self):
        bad = [GOOD_EN.replace("A low result", "This is harmless. A low result"),
               GOOD_EN.replace("A low result is often linked", "It means you have kidney trouble. A low result is often linked"),
               GOOD_EN.replace("at least 2 days", "at least 5 days"),
               GOOD_EN.replace("low food intake", "cancer"),
               GOOD_EN.replace("next routine visit", "doctor immediately"),
               GOOD_EN.replace("[WHEN]", "WHEN:"),
               "Creatinine is low. Eat protein."]
        for reply in bad:
            r = explain.explain_report(Stub(reply), [CREAT], "en")
            self.assertIsNone(r["explanations"][0], reply[:60])
            self.assertIn("fallback_reason", r)
            self.assertEqual(r["guide"]["cards"][0]["title"], "Creatinine")  # fact sheet still available

    def test_sooner_level_must_be_kept(self):
        k = dict(name="Potassium", result="5.4 mmol/L", reference="3.5-5.2", flag="High")
        same = ("[MEANING]\nPotassium is an electrolyte the heart and muscles need. A high result can come from the blood sample "
                "or some medicines.\n[WHEN]\nContact your clinician's office within the next few days.\n[STEPS]\n- Ask whether a repeat test is needed.")
        self.assertIsNotNone(explain.explain_report(Stub(same), [k], "en")["explanations"][0])
        self.assertIsNone(explain.explain_report(Stub(GOOD_EN), [k], "en")["explanations"][0])

    def test_no_model_call_when_nothing_flagged_or_model_missing(self):
        stub = Stub(GOOD_EN)
        self.assertEqual(explain.explain_report(stub, [dict(CREAT, flag="")], "en")["explanations"], [])
        self.assertEqual(stub.prompts, [])
        off = explain.explain_report(Stub(available=False), [CREAT], "en")
        self.assertEqual(off["explanations"], [None]); self.assertIn("ollama pull", off["fallback_reason"])


class ExplainEndpoint(unittest.TestCase):
    def test_cached_per_report_and_cleared_when_forgotten(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(); cfg.store_path = Path(d) / "t.fv"; cfg.exa_key = cfg.tavily_key = ""
            app = App(cfg); app.store.create("disposable-test-passphrase")
            app.store.data.setdefault("reports", {})["r1"] = {"id": "r1", "label": "SYNTHETIC", "rows": [CREAT], "source": {}}
            app.model = Stub(GOOD_EN)
            first = app.dispatch("POST", "/api/reports/explain", {"report_ids": ["r1"], "lang": "en"}, {})
            again = app.dispatch("POST", "/api/reports/explain", {"report_ids": ["r1"], "lang": "en"}, {})
            self.assertIs(first, again); self.assertEqual(len(app.model.prompts), 1)
            with self.assertRaises(ValueError):
                app.dispatch("POST", "/api/reports/explain", {"report_ids": ["nope"]}, {})
            app.dispatch("POST", "/api/reports/forget", {"report_id": "r1"}, {})
            self.assertEqual(app.report_explanations, {})


if __name__ == "__main__":
    unittest.main()
