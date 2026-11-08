"""Local model wrapper: no hidden reasoning, and empty or failed output falls back to a labeled template."""
import unittest

from app.config import Config
from app.egress import EgressError
from app.llm import LocalModel


class StubEgress:
    def __init__(self, response=None, error=None, installed=("qwen3.5:2b",)):
        self.response, self.error, self.installed, self.calls = response, error, installed, []

    def local(self, method, url, json_body=None, timeout=120):
        self.calls.append((method, url, json_body))
        if url.endswith("/api/tags"):
            return {"models": [{"name": n} for n in self.installed]}
        if self.error:
            raise self.error
        return {"response": self.response}


def model(egress):
    cfg = Config()
    cfg.ollama_url, cfg.ollama_model = "http://127.0.0.1:11434", "qwen3.5:2b"
    return LocalModel(egress, cfg)


class LocalModelTests(unittest.TestCase):
    def test_agent_model_is_explicit_and_does_not_change_translation_model(self):
        cfg = Config()
        cfg.ollama_model = "qwen3.5:2b"
        cfg.ollama_agent_model = "qwen2.5:3b"
        from app.server import App
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            cfg.store_path = Path(folder) / "test.fv"
            app = App(cfg)
            self.assertEqual(app.model.model_name, "qwen3.5:2b")
            self.assertEqual(app.agent.model.model_name, "qwen2.5:3b")
            self.assertNotEqual(app.model, app.agent.model)
            self.assertEqual(cfg.services()["ollama_agent_model"], "qwen2.5:3b")

    def test_disables_thinking_and_labels_model_output(self):
        egress = StubEgress(response="您好，我想预约。")
        result = model(egress)._try("prompt", "system", lambda: "TEMPLATE")
        self.assertEqual(result["source"], "local model (qwen3.5:2b)")
        self.assertIs(egress.calls[-1][2]["think"], False)

    def test_empty_output_falls_back_with_reason(self):
        result = model(StubEgress(response=""))._try("prompt", "system", lambda: "TEMPLATE")
        self.assertEqual(result["text"], "TEMPLATE")
        self.assertIn("built-in template", result["source"])
        self.assertIn("no text", result["fallback_reason"])

    def test_unreachable_or_missing_model_falls_back_with_reason(self):
        down = model(StubEgress(error=EgressError("Local model unavailable")))._try("p", "s", lambda: "TEMPLATE")
        self.assertEqual(down["text"], "TEMPLATE")
        missing = model(StubEgress(installed=()))._try("p", "s", lambda: "TEMPLATE")
        self.assertIn("ollama pull qwen3.5:2b", missing["fallback_reason"])

    def test_bilingual_script_keeps_english_and_requires_every_line(self):
        lines = ["Hello.", "Do you take new patients?"]
        good = model(StubEgress(response="1. 您好。\n2. 你们接收新病人吗？"))
        result = good.bilingual_script(lines, "Chinese", "TEMPLATE")
        self.assertEqual(result["text"], "Hello.\n您好。\n\nDo you take new patients?\n你们接收新病人吗？")
        partial = model(StubEgress(response="1. 您好。")).bilingual_script(lines, "Chinese", "TEMPLATE")
        self.assertEqual(partial["text"], "TEMPLATE")
        self.assertIn("line up", partial["fallback_reason"])
        english = model(StubEgress()).bilingual_script(lines, "English", "TEMPLATE")
        self.assertEqual(english["text"], "TEMPLATE")
        self.assertNotIn("fallback_reason", english)


if __name__ == "__main__":
    unittest.main()
