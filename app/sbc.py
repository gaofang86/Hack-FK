"""Read a plan's Summary of Benefits and Coverage (SBC) on this machine.

Every US health plan must publish an SBC on the same federal template, with the same
questions and the same rows (deductible, out-of-pocket limit, primary care, specialist,
urgent care, emergency room, drugs...). That makes it readable with fixed rules: no model,
no network. Each value comes back with the exact line it was read from, and nothing is
saved until the user reviews it.
"""
import base64
import hashlib
import io
import re
from datetime import date

MONEY = r"\$\s?([0-9][0-9,]*(?:\.[0-9]{2})?)"

QUESTIONS = {
    "deductible": r"what\s+is\s+the\s+overall\s+deductible\??",
    "oop_max": r"what\s+is\s+the\s+out-?\s*of-?\s*pocket\s+limit\s+for\s+this\s+plan\??",
}
SERVICES = {
    "primary": (r"primary\s+care\s+visit\s+to\s+treat\s+an\s+injury\s+or\s+illness", "Primary care visit"),
    "specialist": (r"specialist\s+visit", "Specialist visit"),
    "preventive": (r"preventive\s+care\s*/\s*screening\s*/\s*immuni[sz]ation", "Preventive care"),
    "urgent": (r"urgent\s+care", "Urgent care"),
    "er": (r"emergency\s+room\s+care", "Emergency room"),
    "generic": (r"generic\s+drugs", "Generic drugs"),
    "mental": (r"outpatient\s+services", "Mental health outpatient"),
}


def pdf_text(data):
    from pypdf import PdfReader  # local library; the file is read on this machine only
    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) > 30:
        raise ValueError("That PDF is longer than an SBC (30 pages max)")
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _flat(text):
    return re.sub(r"[ \t ]+", " ", text.replace("\r", "")).strip()


def _amount(s):
    return float(s.replace(",", ""))


def parse_cost(snippet):
    """The in-network cost in a row: a copay, a coinsurance, free, or not covered."""
    s = snippet.lower()
    first = {}
    for kind, pat in (("free", r"no\s*charge|\$0\s*copay|covered\s*in\s*full"),
                      ("copay", MONEY + r"\s*(?:copay|co-pay|copayment)"),
                      ("coinsurance", r"([0-9]{1,3})\s*%\s*coinsurance"),
                      ("not_covered", r"not\s*covered")):
        m = re.search(pat, s)
        if m:
            first[kind] = m
    if not first:
        return {"kind": "unknown"}
    kind, m = min(first.items(), key=lambda kv: kv[1].start())
    before = s[max(0, m.start() - 40):m.start()]
    after_ded = bool(re.search(r"deductible\s*(?:,\s*)?then|after\s*(?:the\s*)?deductible", before + s[m.start():m.end() + 30]))
    if kind == "free":
        return {"kind": "free"}
    if kind == "not_covered":
        return {"kind": "not_covered"}
    if kind == "copay":
        return {"kind": "copay", "amount": _amount(m.group(1)), "after_deductible": after_ded}
    return {"kind": "coinsurance", "pct": float(m.group(1)), "after_deductible": after_ded}


def describe(cost):
    k = cost.get("kind")
    if k == "free":
        return "No charge"
    if k == "copay":
        return f"${cost['amount']:,.2f} copay" + (" after deductible" if cost.get("after_deductible") else "")
    if k == "coinsurance":
        return f"{cost['pct']:g}% coinsurance" + (" after deductible" if cost.get("after_deductible") else "")
    if k == "not_covered":
        return "Not covered"
    return "Not found"


class _Finder:
    """Find template phrases even when PDF text extraction splits words or drops spaces."""
    def __init__(self, flat):
        self.flat = flat
        self.pos = [i for i, c in enumerate(flat) if not c.isspace()]
        self.compact = "".join(flat[i] for i in self.pos).lower()

    def find(self, pattern, start=0):
        pat = re.sub(r"\\s[+*]", "", pattern).replace(" ", "")
        cstart = next((k for k, i in enumerate(self.pos) if i >= start), len(self.pos))
        m = re.compile(pat).search(self.compact, cstart)
        if not m:
            return None
        end = self.pos[m.end() - 1] + 1
        return self.pos[m.start()], end


def _evidence(text, start, n=160):
    return _flat(text[start:start + n])


def parse_sbc(text):
    if not text or len(text.strip()) < 200:
        raise ValueError("Couldn’t read text from that file. Try the plan’s official SBC PDF, or paste its text.")
    flat = _flat(text)
    low = flat.lower()
    finder = _Finder(flat)
    looks_like_sbc = "summary of benefits and coverage" in low or "what is the overall deductible" in low
    out = {"is_sbc": looks_like_sbc, "fields": {}, "services": {}}
    for key, pat in QUESTIONS.items():
        hit = finder.find(pat)
        if not hit:
            out["fields"][key] = {"value": None, "evidence": ""}
            continue
        window = flat[hit[1]:hit[1] + 220]
        money = re.search(MONEY, window)
        out["fields"][key] = {"value": _amount(money.group(1)) if money else None,
                              "evidence": _evidence(flat, hit[0], 200)}
    period = re.search(r"coverage\s+period\s*:?\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})\s*[-–]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", low)
    if period:
        def iso(v):
            mth, day, yr = (int(x) for x in v.split("/"))
            return date(yr, mth, day).isoformat()
        try:
            out["fields"]["start"] = {"value": iso(period.group(1)), "evidence": _evidence(flat, period.start(), 60)}
            out["fields"]["end"] = {"value": iso(period.group(2)), "evidence": _evidence(flat, period.start(), 60)}
        except ValueError:
            pass
    guess = ""
    for line in text.splitlines()[:40]:
        l = line.strip()
        if re.search(r"summary of benefits|what this plan|coverage period|important questions|the summary", l, re.I):
            continue
        if re.search(r"\b(plan|ppo|hmo|epo|pos)\b", l, re.I):
            guess = re.split(r"\s+coverage\s+for\s*:|\s+plan\s+type\s*:", l, flags=re.I)[0].strip()
            break
    out["fields"]["name"] = {"value": guess[:120] or None, "evidence": guess[:160]}
    anchors = {"mental": r"mental\s+health", "urgent": r"immediate\s+medical\s+attention"}
    for key, (pat, label) in SERVICES.items():
        start = 0
        if key in anchors:
            a = finder.find(anchors[key])
            start = a[1] if a else 0
        hit = finder.find(pat, start)
        if not hit:
            out["services"][key] = {"label": label, "cost": {"kind": "unknown"}, "text": "Not found", "evidence": ""}
            continue
        window = flat[hit[1]:hit[1] + 160]
        cost = parse_cost(window)
        out["services"][key] = {"label": label, "cost": cost, "text": describe(cost),
                                "evidence": _evidence(flat, hit[0], 180)}
    found = sum(1 for s in out["services"].values() if s["cost"]["kind"] != "unknown")
    found += sum(1 for k in ("deductible", "oop_max") if out["fields"].get(k, {}).get("value") is not None)
    out["found"] = found
    if found < 3:
        raise ValueError("This doesn’t look like a Summary of Benefits and Coverage. Upload the plan’s SBC PDF.")
    return out


def read_upload(body):
    """Accept a PDF (base64) or pasted text. Returns the parsed result plus a fingerprint, never the file."""
    if body.get("pdf_base64"):
        try:
            data = base64.b64decode(body["pdf_base64"], validate=True)
        except Exception:
            raise ValueError("That file didn’t upload correctly")
        if len(data) > 6_000_000:
            raise ValueError("That PDF is too large (6 MB max)")
        if not data.startswith(b"%PDF"):
            raise ValueError("Upload a PDF file")
        text = pdf_text(data)
        digest = hashlib.sha256(data).hexdigest()
    else:
        text = str(body.get("text") or "")[:200_000]
        digest = hashlib.sha256(text.encode()).hexdigest()
    result = parse_sbc(text)
    result["source"] = {"file": str(body.get("file_name") or "pasted text")[:120], "sha256": digest,
                        "read_on": date.today().isoformat(), "how": "Read on this device with fixed rules. No model, no network."}
    return result


def to_plan(confirmed):
    """Turn the reviewed values into the profile's plan + per-service benefits."""
    def num(v):
        return None if v in (None, "") else float(v)
    services = {}
    for key, c in (confirmed.get("services") or {}).items():
        if key not in SERVICES:
            continue
        kind = c.get("kind", "unknown")
        if kind not in ("free", "copay", "coinsurance", "not_covered", "unknown"):
            raise ValueError("Unknown cost type")
        entry = {"kind": kind}
        if kind == "copay":
            entry.update(amount=num(c.get("amount")), after_deductible=bool(c.get("after_deductible")))
            if entry["amount"] is None:
                entry = {"kind": "unknown"}
        elif kind == "coinsurance":
            entry.update(pct=num(c.get("pct")), after_deductible=bool(c.get("after_deductible")))
            if entry["pct"] is None:
                entry = {"kind": "unknown"}
        services[key] = entry
    return services


VISIT_ROW = {"primary_care": "primary", "follow_up": "primary", "same_day": "urgent"}


def plan_for(benefits, service):
    """The benefits.py plan rule for one visit type, built from the reviewed SBC row."""
    if not benefits or not benefits.get("name"):
        return None
    row = (benefits.get("services") or {}).get(VISIT_ROW.get(service, "primary"), {"kind": "unknown"})
    base = {"name": benefits["name"], "start": benefits.get("start", ""), "end": benefits.get("end", ""),
            "premium": benefits.get("premium"), "eligible": True, "oop_remaining": benefits.get("oop_remaining")}
    kind = row.get("kind")
    if kind == "free":
        return dict(base, rule="copay", copay=0)
    if kind == "copay" and not row.get("after_deductible"):
        return dict(base, rule="copay", copay=row["amount"])
    if kind == "coinsurance":
        return dict(base, rule="deductible", coinsurance=row["pct"],
                    deductible_remaining=benefits.get("deductible_remaining") if row.get("after_deductible") else 0)
    return dict(base, rule="copay", copay=None)


def share(cost, fee, deductible_remaining, oop_remaining):
    """What you'd pay on an example fee for one SBC row. None if the row doesn't say."""
    kind = (cost or {}).get("kind")
    ded = deductible_remaining or 0
    if kind == "free":
        amount, how = 0.0, "No charge for this in-network, per your plan’s SBC"
    elif kind == "copay" and not cost.get("after_deductible"):
        amount, how = cost["amount"], f"${cost['amount']:,.2f} copay, per your plan’s SBC"
    elif kind == "copay":
        amount = fee if fee <= ded else ded + cost["amount"]
        how = f"Deductible first (${ded:,.2f} left), then a ${cost['amount']:,.2f} copay"
    elif kind == "coinsurance":
        first = min(fee, ded) if cost.get("after_deductible") else 0
        amount = first + (fee - first) * cost["pct"] / 100
        how = (f"${first:,.2f} toward your deductible, then {cost['pct']:g}%" if cost.get("after_deductible")
               else f"{cost['pct']:g}% coinsurance, per your plan’s SBC")
    elif kind == "not_covered":
        return fee, "Your plan’s SBC says this isn’t covered, so you’d pay the full fee"
    else:
        return None, "Your plan’s SBC didn’t show this. Check the plan."
    if oop_remaining is not None and amount > oop_remaining:
        amount, how = oop_remaining, how + f", capped at ${oop_remaining:,.2f}"
    return round(amount, 2), how
