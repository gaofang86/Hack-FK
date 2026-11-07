"""Read a medical bill or Explanation of Benefits (EOB) on this laptop.

Paste the text of a bill or EOB. Amounts are pulled out with fixed patterns so the
numbers you see are the numbers on the page, each with the line it came from. The
local model only explains them. Nothing here is ever sent anywhere: account and
claim numbers found in the text are added to the DLP filter as well.
"""
import re

AMOUNT = r"\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)"
FIELDS = [
    ("billed", "Amount the provider charged",
     r"(?:total charges?|amount billed|billed amount|provider charged|charges)"),
    ("allowed", "Amount your plan allows",
     r"(?:allowed amount|plan allowance|approved amount|negotiated (?:rate|amount)|amount allowed)"),
    ("plan_paid", "Amount your plan paid",
     r"(?:plan paid|insurance paid|paid by (?:plan|insurance)|insurer paid|amount paid by plan)"),
    ("deductible", "Applied to your deductible", r"(?:applied to deductible|deductible)"),
    ("copay", "Copay", r"(?:copay(?:ment)?)"),
    ("coinsurance", "Coinsurance", r"(?:coinsurance)"),
    ("you_owe", "What you may owe",
     r"(?:patient responsibility|you (?:may )?owe|your responsibility|amount (?:you owe|due)|balance due|patient balance|please pay)"),
]
IDENT = re.compile(r"(?:account|acct|claim|invoice|patient|member|statement)\s*(?:no\.?|number|#|id)?\s*[:#]?\s*([A-Z0-9-]{5,})", re.I)
CPT = re.compile(r"\b(9\d{4}|[1-8]\d{4})\b(?=[^\n]{0,80}(?:visit|exam|office|x-?ray|test|panel|level|emergency|consult))", re.I)


def _num(s):
    return float(s.replace(",", "").replace("$", "").strip())


def parse(text):
    text = text or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    found = {}
    for key, label, pat in FIELDS:
        rx = re.compile(pat + r"[^\n$\d]{0,30}" + AMOUNT, re.I)
        for ln in lines:
            m = rx.search(ln)
            if m:
                try:
                    found[key] = {"label": label, "amount": _num(m.group(1)), "line": ln[:160]}
                except ValueError:
                    continue
                break
    low = text.lower()
    is_eob = ("explanation of benefits" in low or "this is not a bill" in low or bool(re.search(r"\beob\b", low)))
    out_of_network = bool(re.search(r"out[- ]of[- ]network|non[- ]?participating|not in network", low))
    emergency = bool(re.search(r"emergency (room|department|services)|\ber visit\b", low))
    collections = "collection" in low
    denied = bool(re.search(r"\bdenied\b|not covered|claim (was )?rejected", low))
    idents = sorted({m.group(1) for m in IDENT.finditer(text) if re.search(r"\d", m.group(1))})
    codes = sorted({m.group(1) for m in CPT.finditer(text)})
    return {"kind": "eob" if is_eob else "bill", "amounts": found, "out_of_network": out_of_network,
            "emergency": emergency, "collections": collections, "denied": denied,
            "identifiers": idents, "codes": codes}


def flags(p, related_eob=None):
    """Plain checks a careful person would make before paying."""
    out = []
    a = p["amounts"]
    if p["kind"] == "eob":
        out.append({"level": "info", "text": "This is an Explanation of Benefits, not a bill. Don't pay from it. "
                    "Keep it and compare it with the bill when the bill arrives."})
    else:
        out.append({"level": "info", "text": "Before paying a bill, wait for your insurer's Explanation of Benefits "
                    "(EOB) for the same visit and check that 'what you owe' matches."})
    if "you_owe" in a and related_eob and "you_owe" in related_eob["amounts"]:
        due, eob_due = a["you_owe"]["amount"], related_eob["amounts"]["you_owe"]["amount"]
        if due > eob_due + 0.5:
            out.append({"level": "warn", "text": f"The bill asks for ${due:,.2f}, but your EOB says you owe "
                        f"${eob_due:,.2f}. Call the billing office and ask why."})
    if "billed" in a and "allowed" in a and a["billed"]["amount"] > a["allowed"]["amount"] and p["kind"] == "bill" \
            and "you_owe" in a and a["you_owe"]["amount"] >= a["billed"]["amount"] - a["allowed"]["amount"] - 0.5 \
            and not p["out_of_network"]:
        out.append({"level": "warn", "text": "You may be billed for the difference between the charge and the "
                    "allowed amount. In-network providers generally can't bill you that difference. Ask the billing office."})
    if p["out_of_network"] and p["emergency"]:
        out.append({"level": "warn", "text": "Out-of-network emergency care: under the federal No Surprises Act, most "
                    "plans must charge you in-network cost sharing, and the hospital can't bill you the rest. "
                    "Ask the billing office and your insurer to reprocess it; you can also call the No Surprises "
                    "Help Desk at 1-800-985-3059."})
    elif p["out_of_network"]:
        out.append({"level": "warn", "text": "Marked out-of-network. If this was at an in-network hospital or clinic "
                    "and you didn't agree in writing to out-of-network care, the No Surprises Act may protect you. "
                    "Ask your insurer."})
    if p["denied"]:
        out.append({"level": "warn", "text": "Something was denied. You have the right to ask your insurer why and to "
                    "appeal. Ask for the reason in writing."})
    if p["kind"] == "bill" and not p["codes"]:
        out.append({"level": "info", "text": "Ask for an itemized bill with procedure (CPT) codes so you can see "
                    "each charge."})
    if p["collections"]:
        out.append({"level": "warn", "text": "This mentions collections. Call the billing office now to ask for a "
                    "hold while you check the bill, and ask whether you qualify for financial assistance."})
    if p["kind"] == "bill":
        out.append({"level": "info", "text": "Nonprofit hospitals must have a financial assistance (charity care) "
                    "policy (IRS rule 501(r)). Ask whether you qualify; it's often based on income."})
    return out


def questions(p):
    q = ["Can you send me an itemized bill with the CPT codes?",
         "Has this been sent to my insurance, and has my insurance finished processing it?"]
    if p["out_of_network"]:
        q.append("Was this provider in my plan's network? If not, why wasn't I told before treatment?")
    if p["denied"]:
        q.append("Why was this denied, and how do I appeal?")
    q.append("Can I set up a payment plan with no interest?")
    q.append("Do I qualify for financial assistance?")
    return q
