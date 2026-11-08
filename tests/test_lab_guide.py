"""Plain-language lab guide: fixed sourced text, follows the report's own flags, never clears or diagnoses."""
import json
import unittest

from app.lab_guide import explain, entry, GUIDE, LEVELS, SOON, ROUTINE

FORBIDDEN = ("you have", "abnormal", "your risk", "risk score:", "likely", "indicates", "means you",
             "harmless", "nothing to worry", "no need to see", "you are fine", "diagnosis:")


def row(name, result, reference, flag=""):
    return dict(name=name, result=result, reference=reference, flag=flag)


class LabGuide(unittest.TestCase):
    def test_low_creatinine_explained_in_plain_language_with_steps_and_source(self):
        g = explain([row("Creatinine", "0.52 mg/dL", "0.57-1.00", "Low"), row("Glucose", "98 mg/dL", "70-99")])
        self.assertIn("1 of 2 results are within the report's ranges", g["headline"])
        self.assertIn("Creatinine is slightly below the lab's range", g["headline"])
        c = g["cards"][0]
        self.assertIn("muscle", c["what"])
        self.assertIn("less muscle mass", c["linked"])
        self.assertEqual((c["level"], g["level"], g["next_step"]), (ROUTINE, ROUTINE, LEVELS[ROUTINE]))
        self.assertTrue(any("protein" in s for s in c["steps"]))
        self.assertTrue(c["source"].startswith("https://medlineplus.gov/lab-tests/"))
        self.assertEqual([o["name"] for o in g["others"]], ["Glucose"])
        self.assertIn("911", g["red_flags"])

    def test_far_outside_range_or_electrolytes_ask_for_a_sooner_check(self):
        far = explain([row("Creatinine", "3.0 mg/dL", "0.57-1.00", "High")])
        self.assertEqual(far["cards"][0]["level"], SOON)
        self.assertIn("well above", far["cards"][0]["status"])
        self.assertEqual(explain([row("Potassium", "5.4 mmol/L", "3.5-5.2", "High")])["level"], SOON)

    def test_follows_the_reports_flags_only(self):
        g = explain([row("Creatinine", "9", "0.57-1.00", "")])  # unflagged by the lab: not explained as out of range
        self.assertEqual(g["cards"], [])
        self.assertIn("All 1 results are within the ranges printed on your report", g["headline"])

    def test_unknown_test_is_not_guessed(self):
        c = explain([row("Mystery marker", "5", "1-2", "High")])["cards"][0]
        self.assertEqual(c["level"], SOON)
        self.assertEqual(c["linked"], "")
        self.assertIn("Ask your clinician", c["steps"][0])

    def test_names_match_the_supported_panel_and_ratio_before_bun(self):
        self.assertEqual(entry("BUN/Creatinine Ratio")["title"], "BUN/Creatinine ratio")
        self.assertEqual(entry("BUN")["title"], "BUN (blood urea nitrogen)")
        for name in ("Carbon Dioxide, Total", "Protein, Total", "Globulin, Total", "Bilirubin, Total", "AST (SGOT)", "ALT (SGPT)", "eGFR"):
            self.assertIsNotNone(entry(name), name)

    def test_no_clearance_or_diagnostic_wording(self):
        text = json.dumps(GUIDE).lower() + json.dumps(explain([row("Creatinine", "0.52", "0.57-1.00", "Low")])).lower()
        for word in FORBIDDEN:
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
