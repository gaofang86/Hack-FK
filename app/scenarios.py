"""Three coverage situations, three different kinds of help. Fixed rules, sourced, no model.

A. Has insurance      -> make the benefits work: what to confirm, what may be free, who to ask.
B. No insurance       -> lowest price first, then the help people don't know exists.
C. Choosing a plan    -> compare plans on the care you actually expect to need this year.
"""
from .benefits import money, number
from .expect import SOURCES as EXPECT_SOURCES

CHECKED = "2026-11-07"
SOURCES = {
    "preventive": {"title": "HealthCare.gov: preventive care benefits",
                   "url": "https://www.healthcare.gov/coverage/preventive-care-benefits/"},
    "total_costs": {"title": "HealthCare.gov: how your total costs work",
                    "url": "https://www.healthcare.gov/choose-a-plan/your-total-costs/"},
    "hrsa": {"title": "HRSA: find a community health center", "url": "https://findahealthcenter.hrsa.gov/"},
    "fap": {"title": "IRS: hospital financial assistance policies",
            "url": "https://www.irs.gov/charities-non-profits/financial-assistance-policies-faps"},
    "nafc": {"title": "NAFC: find a free or charitable clinic", "url": "https://nafcclinics.org/find-clinic/"},
    "gfe": EXPECT_SOURCES["gfe"],
    "neu_plan": {"title": "Northeastern student health plan", "url": "https://studenthealthplan.northeastern.edu/"},
    "connector": {"title": "Massachusetts Health Connector: compare plans", "url": "https://betterhealthconnector.com/compare-plans"},
    "healthcare_gov": {"title": "HealthCare.gov: see plans", "url": "https://www.healthcare.gov/see-plans/"},
}


def _src(key):
    return dict(SOURCES[key], checked_on=CHECKED)


def _plan_line(plan):
    if not plan:
        return "Add your plan details to see your share."
    if plan["rule"] == "copay":
        return f"Copay of ${plan['copay']:,.2f} for this kind of visit." if plan.get("copay") is not None else "Add the copay for this kind of visit."
    parts = []
    if plan.get("deductible_remaining") is not None:
        parts.append(f"${plan['deductible_remaining']:,.2f} of deductible left")
    if plan.get("coinsurance") is not None:
        parts.append(f"then you pay {plan['coinsurance']:g}%")
    return (", ".join(parts) + ".") if parts else "Add your remaining deductible and coinsurance."


def insured(person):
    plan, service = person.get("plan"), person.get("service")
    known = [{"label": "Your plan", "value": plan["name"] if plan else "Not entered"},
             {"label": "This visit", "value": _plan_line(plan)}]
    b = person.get("benefits")
    if b:
        from .sbc import describe
        for key, label in (("primary", "Primary care"), ("urgent", "Urgent care"), ("er", "Emergency room"), ("generic", "Generic drugs")):
            known.append({"label": label, "value": describe((b.get("services") or {}).get(key, {}))})
        if b.get("deductible") is not None:
            known.append({"label": "Deductible", "value": f"${b['deductible']:,.2f}" + (f" (${b['deductible_remaining']:,.2f} left)" if b.get("deductible_remaining") is not None else "")})
        if b.get("oop_max") is not None:
            known.append({"label": "Out-of-pocket limit", "value": f"${b['oop_max']:,.2f}"})
        known.append({"label": "Read from", "value": f"{b['source'].get('file') or 'SBC'} · {b['source'].get('read_on', '')}"})
    confirm = ["Is this clinic, at this location, in-network for my exact plan?",
               "Do I need a referral or prior authorization for this visit?",
               "What will I owe at the visit, and could any extra bill follow?"]
    if service == "same_day":
        confirm.insert(1, "What’s my urgent care copay, and what’s my emergency room copay?")
    if plan and plan.get("rule") == "deductible":
        confirm.append("How much of my deductible is left right now?")
    tips = [{"title": "Use in-network places", "why": "Out-of-network care can cost much more, or not be covered at all.",
             "source": _src("total_costs")},
            {"title": "Ask your plan about a nurse line or telehealth",
             "why": "Many plans include one. It can help you decide where to go, often at low or no cost."}]
    if person.get("need") == "checkup" or service == "primary_care":
        tips.insert(0, {"title": "Checkups and screenings may be free",
                        "why": "Many preventive services cost nothing at an in-network provider. Ask the clinic to bill it as preventive.",
                        "source": _src("preventive")})
    return {"kind": "insured", "title": "Make your benefits work for you",
            "lede": "Your plan decides what you pay. Here’s what we know, and what to confirm before you go.",
            "known": known, "ask": confirm, "tips": tips}


def uninsured(person):
    first = {"title": "First, check whether you’re already covered",
             "why": "Many schools enroll students in a health plan automatically. Look in your student account or the plan’s site.",
             "source": _src("neu_plan")}
    resources = [
        {"title": "Community health centers", "why": "They charge by income on a sliding scale, with or without insurance.", "source": _src("hrsa")},
        {"title": "Free and charitable clinics", "why": "Volunteer-run clinics that offer free or low-cost care.", "source": _src("nafc")},
        {"title": "Hospital financial assistance", "why": "Nonprofit hospitals must have a written financial assistance policy. Ask for it, even after a bill arrives.", "source": _src("fap")},
        {"title": "A written estimate", "why": "If you’re uninsured or paying yourself, you can ask for a Good Faith Estimate for scheduled care.", "source": _src("gfe")},
    ]
    scripts = ["Hi, I don’t have insurance. What’s your self-pay price for this visit?",
               "Do you offer a discount if I pay at the visit?",
               "Is there a sliding scale or financial assistance I can apply for?",
               "Could I get a written Good Faith Estimate before my appointment?",
               "If I get a bill I can’t pay at once, can I set up a payment plan?"]
    return {"kind": "uninsured", "title": "Lowest price, and help you can ask for",
            "lede": "Your options below are sorted by self-pay price. Unknown prices stay unknown, never $0.",
            "first": first, "resources": resources, "scripts": scripts}


def choosing(person):
    out = uninsured(person)
    out.update(kind="choosing", title="Should you get a plan? Compare on what you need",
               lede="Self-pay prices are below. To decide on a plan, compare plans on the care you expect this year.",
               compare=True)
    return out


def guidance(person):
    if person.get("insurance") == "yes":
        return insured(person)
    return choosing(person) if person.get("wants_insurance") else uninsured(person)


# ---- C: plan comparison on most-needed care -------------------------------------------------
NEEDS = {
    "primary": "Primary care visits", "prescriptions": "Prescription refills", "mental": "Counseling or therapy",
    "specialist": "Specialist visits", "urgent": "Urgent care visits", "er": "Emergency room visits", "labs": "Lab tests",
}


def suggested_needs(profile):
    """Pre-select needs from the profile; the user can change them."""
    out = {"primary": 2}
    if profile.get("medications"):
        out["prescriptions"] = 12
    if profile.get("conditions"):
        out["specialist"] = 2
    if profile.get("follow_ups"):
        out["primary"] = out["primary"] + len(profile["follow_ups"])
    return out


def compare_plans(raw):
    needs = {}
    for key, count in (raw.get("needs") or {}).items():
        if key in NEEDS:
            n = number(count, f"{NEEDS[key]} per year", 365)
            if n:
                needs[key] = int(n)
    if not needs:
        raise ValueError("Pick at least one kind of care you expect to need")
    plans = []
    for p in (raw.get("plans") or [])[:3]:
        name = str(p.get("name") or "").strip()[:120]
        if not name:
            continue
        premium = number(p.get("premium"), f"{name} monthly premium")
        oop = number(p.get("oop_max"), f"{name} out-of-pocket maximum")
        rows, care, unknown, uncovered = [], 0.0, [], []
        for key, count in needs.items():
            entry = (p.get("costs") or {}).get(key) or {}
            status = entry.get("status", "unknown")
            if status not in ("covered", "not_covered", "unknown"):
                raise ValueError("Choose covered, not covered or unknown")
            cost = number(entry.get("cost"), f"{name} {NEEDS[key]} cost")
            if status == "covered" and cost is not None:
                line = cost * count
                care += line
                rows.append({"need": NEEDS[key], "count": count, "each": cost, "total": money(line), "status": status})
            else:
                (uncovered if status == "not_covered" else unknown).append(NEEDS[key])
                rows.append({"need": NEEDS[key], "count": count, "each": None, "total": None, "status": status})
        capped = oop is not None and care > oop
        care_total = oop if capped else care
        year = None if premium is None else money(premium * 12 + care_total)
        plans.append({"name": name, "premium": premium, "oop_max": oop, "rows": rows,
                      "care_total": money(care_total), "capped": capped, "premium_year": None if premium is None else money(premium * 12),
                      "year_total": year, "unknown": unknown, "not_covered": uncovered,
                      "complete": year is not None and not unknown and not uncovered})
    if not plans:
        raise ValueError("Add at least one plan with a name")
    ranked = sorted([p for p in plans if p["complete"]], key=lambda p: p["year_total"])
    return {"needs": {NEEDS[k]: v for k, v in needs.items()}, "plans": plans,
            "best": ranked[0]["name"] if ranked else None,
            "note": "Uses only the numbers you entered. Copays and coinsurance before the deductible, family plans, subsidies and eligibility are not modeled. A plan with unknown or uncovered care can’t be ranked.",
            "sources": [_src("total_costs"), _src("connector"), _src("healthcare_gov")]}
