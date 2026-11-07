"""On-device model via Ollama (default qwen2.5:3b). Loopback only, works with Wi-Fi off.

The model never decides anything. Triage rules, costs and bill amounts are computed
deterministically; the model only explains them, or translates a call script, in
your language. Every output says whether it came from the local model or a built-in
template (English, Chinese and Spanish templates are bundled for offline use).
"""
from .egress import EgressBlocked, EgressError


def lang_code(language):
    l = (language or "").lower()
    if any(k in l for k in ("中文", "chinese", "mandarin", "cantonese", "zh")):
        return "zh"
    if any(k in l for k in ("español", "espanol", "spanish", "es")) and "eng" not in l:
        return "es"
    if not l or "english" in l or l == "en":
        return "en"
    return "other"


T = {
    "zh": {
        "emergency": "这可能是紧急情况。请立即拨打 911 或去最近的急诊室。急诊室必须为你检查和稳定病情，不论你有没有保险。",
        "same_day": "今天就要看医生。一般去 urgent care（紧急护理诊所）或学校的健康中心最合适，比急诊室便宜很多。如果情况变严重，请去急诊室。",
        "soon": "建议在一两天内看医生。可以先找学校健康中心，或者预约视频问诊（telehealth），通常最便宜。",
        "routine": "这可以正常预约，不需要去急诊或 urgent care。",
        "script_title": "打电话时可以这样说（中文对照）",
        "hello": "您好，我叫 {name}。我想今天看医生，原因是：{reason}。",
        "insurance": "我的保险是 {insurer}，会员号是 {member_id}。",
        "ask": ["你们接受我的保险吗？是在网络内（in-network）吗？",
                "今天还能看吗？大概要等多久？",
                "这次看病我大概要付多少钱？",
                "我需要一位免费的医疗翻译，可以安排吗？"],
        "doctor_qs": ["您觉得是什么原因引起的？", "如果变严重了，我该怎么办？什么时候需要复诊？",
                      "这个检查或药我的保险能报销吗？有更便宜的仿制药吗？", "可以把这些写下来给我吗？"],
        "bill": "这份{kind}显示：{items}。",
        "bill_kind": {"eob": "保险说明（EOB，不是账单）", "bill": "账单"},
    },
    "es": {
        "emergency": "Esto podría ser una emergencia. Llame al 911 o vaya ahora a la sala de emergencias más cercana. Deben atenderle y estabilizarle aunque no tenga seguro.",
        "same_day": "Busque atención hoy. Una clínica de urgent care o la clínica de su universidad suele ser lo indicado, y cuesta mucho menos que la sala de emergencias. Si empeora, vaya a emergencias.",
        "soon": "Vea a alguien en uno o dos días. Empiece por la clínica de su universidad o una consulta por video (telehealth), que suelen ser lo más barato.",
        "routine": "Esto se puede atender con una cita normal.",
        "script_title": "Qué decir por teléfono (en español)",
        "hello": "Hola, me llamo {name}. Quisiera una consulta hoy por: {reason}.",
        "insurance": "Mi seguro es {insurer} y mi número de miembro es {member_id}.",
        "ask": ["¿Aceptan mi seguro? ¿Están dentro de la red (in-network)?",
                "¿Me pueden atender hoy? ¿Cuánto hay que esperar?",
                "¿Aproximadamente cuánto voy a pagar por la consulta?",
                "Necesito un intérprete médico gratuito. ¿Lo pueden organizar?"],
        "doctor_qs": ["¿Qué cree que lo está causando?", "¿Qué hago si empeora? ¿Cuándo debo volver?",
                      "¿Mi seguro cubre esta prueba o medicina? ¿Hay un genérico más barato?", "¿Me lo puede escribir?"],
        "bill": "Este {kind} muestra: {items}.",
        "bill_kind": {"eob": "explicación de beneficios (EOB, no es una factura)", "bill": "factura"},
    },
}
EN_ASK = ["Do you take my insurance? Are you in-network for my plan?",
          "Can I be seen today? How long is the wait?",
          "About how much will I pay for this visit?",
          "I'd like a free medical interpreter. Can you arrange one?"]
EN_DOCTOR_QS = ["What do you think is causing this?", "What should I do if it gets worse? When should I come back?",
                "Is this test or medicine covered by my insurance? Is there a cheaper generic?",
                "Can you write that down for me?"]


class LocalModel:
    def __init__(self, egress, config):
        self.egress, self.cfg = egress, config

    def status(self):
        try:
            tags = self.egress.local("GET", f"{self.cfg.ollama_url}/api/tags", timeout=3)
        except (EgressError, EgressBlocked, ValueError, TypeError) as e:
            return {"available": False, "model": self.cfg.ollama_model, "reason": str(e)}
        names = [m.get("name", "") for m in tags.get("models", [])]
        want = self.cfg.ollama_model
        ok = want in names or (":" not in want and any(n.split(":")[0] == want for n in names))
        return {"available": ok, "model": want, "installed": names,
                "reason": "" if ok else f"Run: ollama pull {want}"}

    def generate(self, prompt, system="", max_tokens=400):
        res = self.egress.local("POST", f"{self.cfg.ollama_url}/api/generate", json_body={
            "model": self.cfg.ollama_model, "prompt": prompt, "system": system, "stream": False,
            "options": {"temperature": 0.2, "num_predict": max_tokens},
        })
        return (res.get("response") or "").strip()

    def _try(self, prompt, system, fallback, max_tokens=400):
        if self.status()["available"]:
            try:
                text = self.generate(prompt, system, max_tokens)
                if text:
                    return {"text": text, "source": f"local model ({self.cfg.ollama_model})"}
            except (EgressError, EgressBlocked, ValueError, TypeError):
                pass
        return {"text": fallback(), "source": "built-in template"}

    # ---- tasks ----
    def explain_decision(self, decision, language):
        code = lang_code(language)

        def fallback():
            if code in T:
                return T[code][decision["level"]]
            return decision["headline"] + " " + decision["why"]

        system = ("You help international students navigate US healthcare. You do not diagnose and you never "
                  "change the level of care you are given. Answer in {lang}. Be calm and concrete. At most 5 short "
                  "sentences. Explain US terms like urgent care, copay and in-network in simple words.").format(lang=language)
        prompt = (f"Recommended level of care (fixed, do not change): {decision['level']}.\n"
                  f"Recommendation: {decision['headline']}\nWhy: {decision['why']}\n"
                  f"Rules that applied: {'; '.join(decision['rules']) or 'none'}\n"
                  f"Explain this to the student in {language}, and tell them what to do next.")
        return self._try(prompt, system, fallback, 320)

    def translate_script(self, lines, language):
        code = lang_code(language)
        if code == "en":
            return None
        joined = "\n".join(lines)

        def fallback():
            return ("(Install Ollama with a local model to translate this into " + language + ".)")

        system = (f"Translate each line into {language}. Keep names, numbers and insurance IDs unchanged. "
                  "Output only the translated lines, one per line, in the same order.")
        return self._try(joined, system, fallback, 400)

    def explain_bill(self, parsed, flag_list, language):
        code = lang_code(language)
        items = [f"{v['label']}: ${v['amount']:,.2f}" for v in parsed["amounts"].values()]

        def fallback():
            if code in T:
                t = T[code]
                return t["bill"].format(kind=t["bill_kind"][parsed["kind"]], items="; ".join(items) or "—")
            kind = "Explanation of Benefits (not a bill)" if parsed["kind"] == "eob" else "bill"
            return f"This {kind} shows: " + ("; ".join(items) or "no amounts we could read") + "."

        system = (f"You explain US medical bills to an international student in {language}. Use only the numbers "
                  "given. Do not invent amounts or legal claims. At most 6 short sentences. Explain terms like "
                  "deductible, coinsurance, allowed amount and EOB simply.")
        prompt = (f"Document type: {'Explanation of Benefits (not a bill)' if parsed['kind'] == 'eob' else 'bill'}.\n"
                  f"Amounts: {'; '.join(items) or 'none found'}.\n"
                  f"Checks: {' | '.join(f['text'] for f in flag_list)}\n"
                  f"Explain what this means and what the student should do next, in {language}.")
        return self._try(prompt, system, fallback, 360)
