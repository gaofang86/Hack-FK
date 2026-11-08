"""Your health profile: what FirstVisit remembers about you, kept only in the encrypted vault.

The profile grows with each visit. It drives the to-dos and better choices on the home page.
Every rule below is fixed and names its official source. Nothing here diagnoses; it only
suggests what to ask about.
"""
from datetime import date, timedelta

from .benefits import clean_plan, number

SOURCES = {
    "uspstf": {"title": "USPSTF A and B recommendations",
               "url": "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation-topics/uspstf-a-and-b-recommendations"},
    "cdc_adult": {"title": "CDC adult immunization schedule",
                  "url": "https://www.cdc.gov/vaccines/hcp/imz-schedules/adult-age.html"},
    "preventive": {"title": "HealthCare.gov: preventive care benefits",
                   "url": "https://www.healthcare.gov/coverage/preventive-care-benefits/"},
    "hrsa": {"title": "HRSA: find a community health center",
             "url": "https://findahealthcenter.hrsa.gov/"},
}
CHECKED = "2026-11-07"

# (id, title, why, source, who): who(age, sex) -> bool. Sex is optional; sex-specific items need it.
SCREENINGS = [
    ("bp", "Blood pressure check", "Recommended for adults 18 and older.", "uspstf", lambda a, s: a >= 18),
    ("mood", "Depression and anxiety check-in", "Recommended for adults; anxiety screening up to age 64.", "uspstf", lambda a, s: a >= 18),
    ("hiv", "HIV test", "Recommended at least once for ages 15 to 65.", "uspstf", lambda a, s: 15 <= a <= 65),
    ("hepc", "Hepatitis C test", "Recommended at least once for ages 18 to 79.", "uspstf", lambda a, s: 18 <= a <= 79),
    ("hepb", "Ask about a hepatitis B test", "Recommended for people at higher risk, including many people born where hepatitis B is common.", "uspstf", lambda a, s: a >= 18),
    ("tb", "Ask about a TB test", "Recommended for people at higher risk, such as those who lived where tuberculosis is common.", "uspstf", lambda a, s: a >= 18),
    ("cervical", "Cervical cancer screening", "Recommended for women 21 to 65.", "uspstf", lambda a, s: s == "female" and 21 <= a <= 65),
    ("breast", "Breast cancer screening (mammogram)", "Recommended every 2 years for women 40 to 74.", "uspstf", lambda a, s: s == "female" and 40 <= a <= 74),
    ("colon", "Colorectal cancer screening", "Recommended for adults 45 to 75.", "uspstf", lambda a, s: 45 <= a <= 75),
    ("diabetes", "Ask about a diabetes check", "Recommended for adults 35 to 70 who have overweight or obesity.", "uspstf", lambda a, s: 35 <= a <= 70),
]
VACCINES = [
    ("flu", "Flu shot this season", "One dose every year for adults.", "cdc_adult", lambda a, s: a >= 18),
    ("tdap", "Tetanus booster (Td/Tdap)", "Once as Tdap, then a booster every 10 years.", "cdc_adult", lambda a, s: a >= 18),
    ("hpv", "HPV vaccine, if you haven’t finished it", "Routine through age 26.", "cdc_adult", lambda a, s: 18 <= a <= 26),
]


def _text(value, n=200):
    return str(value or "").strip()[:n]


def _date(value, label):
    value = _text(value, 10)
    if not value:
        return ""
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise ValueError(f"Use a valid date for {label}")


def _strings(values, n=30):
    if isinstance(values, str):
        values = values.replace("\n", ",").split(",")
    return [v for v in (_text(x, 120) for x in (values or [])[:n]) if v]


def clean_profile(raw, today=None):
    today = today or date.today()
    birth_year = number(raw.get("birth_year"), "Birth year", today.year)
    if birth_year is not None and not 1900 <= birth_year <= today.year:
        raise ValueError("Enter a four-digit birth year")
    sex = raw.get("sex") or ""
    if sex not in ("", "female", "male"):
        raise ValueError("Choose female, male, or leave it blank")
    insurance = raw.get("insurance") or ""
    if insurance not in ("", "yes", "no"):
        raise ValueError("Choose whether you have insurance")
    meds, refills = [], {}
    for m in (raw.get("medications") or [])[:30]:
        name = _text(m.get("name") if isinstance(m, dict) else m, 120)
        if name:
            meds.append(name)
            if isinstance(m, dict) and m.get("refill_by"):
                refills[name] = _date(m["refill_by"], f"{name} refill")
    follow = []
    for f in (raw.get("follow_ups") or [])[:30]:
        what = _text(f.get("what") if isinstance(f, dict) else f, 160)
        if what:
            follow.append({"what": what, "due": _date(f.get("due") if isinstance(f, dict) else "", what)})
    return {"birth_year": None if birth_year is None else int(birth_year), "sex": sex,
            "language": _text(raw.get("language") or "English", 50),
            "conditions": _strings(raw.get("conditions")), "allergies": _strings(raw.get("allergies")),
            "medications": meds, "refills": refills, "follow_ups": follow,
            "insurance": insurance, "wants_insurance": raw.get("wants_insurance") is True,
            "plan": clean_plan(raw.get("plan"))}


def record_visit(profile, raw, today=None):
    """Add one visit to the timeline and fold what changed into the profile."""
    today = today or date.today()
    when = _date(raw.get("date"), "visit date") or today.isoformat()
    if when > today.isoformat():
        raise ValueError("Record a visit that has already happened")
    reason = _text(raw.get("reason"), 200)
    if not reason:
        raise ValueError("Say what the visit was for")
    update = clean_profile({"medications": raw.get("medications"), "follow_ups": raw.get("follow_ups"),
                            "conditions": raw.get("conditions")}, today)
    meds = profile.setdefault("medications", [])
    for name in update["medications"]:
        if name not in meds:
            meds.append(name)
    profile.setdefault("refills", {}).update(update["refills"])
    finished = set(_strings(raw.get("completed_follow_ups")))
    follow = [f for f in profile.get("follow_ups", []) if f["what"] not in finished]
    known = {f["what"] for f in follow}
    follow += [f for f in update["follow_ups"] if f["what"] not in known]
    profile["follow_ups"] = follow
    conds = profile.setdefault("conditions", [])
    conds += [c for c in update["conditions"] if c not in conds]
    visit = {"id": raw.get("id") or f"v{len(profile.get('visits', [])) + 1}-{when}", "date": when, "reason": reason,
             "place": _text(raw.get("place"), 160), "notes": _text(raw.get("notes"), 2000),
             "added": {"medications": update["medications"], "follow_ups": [f["what"] for f in update["follow_ups"]],
                       "conditions": update["conditions"], "completed": sorted(finished)},
             "case_id": _text(raw.get("case_id"), 40)}
    profile.setdefault("visits", []).append(visit)
    profile["visits"].sort(key=lambda v: v["date"], reverse=True)
    return visit


def age(profile, today=None):
    year = profile.get("birth_year")
    return None if not year else (today or date.today()).year - year


def todos(profile, today=None):
    """Personal to-dos first (refills, follow-ups), then sourced preventive suggestions."""
    today = today or date.today()
    done = profile.get("done", {})
    items = []
    for med, by in (profile.get("refills") or {}).items():
        if by and med in profile.get("medications", []):
            days = (date.fromisoformat(by) - today).days
            if days <= 14:
                items.append({"id": f"refill:{med}", "kind": "refill", "title": f"Refill {med}",
                              "why": "Overdue. Ask your pharmacy or clinician today." if days < 0 else f"Runs out by {by}.",
                              "urgent": days <= 3})
    for f in profile.get("follow_ups") or []:
        if f.get("due"):
            days = (date.fromisoformat(f["due"]) - today).days
            if days <= 30:
                items.append({"id": f"follow:{f['what']}", "kind": "follow_up", "title": f["what"],
                              "why": "Overdue. Book it soon." if days < 0 else f"Due by {f['due']}.", "urgent": days < 0})
    a, s = age(profile, today), profile.get("sex", "")
    if a is not None:
        for kind, rules in (("screening", SCREENINGS), ("vaccine", VACCINES)):
            for rid, title, why, src, who in rules:
                if who(a, s):
                    items.append({"id": rid, "kind": kind, "title": title, "why": why,
                                  "source": dict(SOURCES[src], checked_on=CHECKED)})
    for item in items:
        item["done_on"] = done.get(item["id"])
    return items


def better_choices(profile):
    out = []
    if profile.get("insurance") == "yes":
        out.append({"title": "Preventive care is often free with your plan",
                    "why": "Many checkups, screenings and vaccines cost nothing at an in-network provider.",
                    "source": dict(SOURCES["preventive"], checked_on=CHECKED)})
    elif profile.get("insurance") == "no":
        out.append({"title": "Community health centers charge by income",
                    "why": "Federally funded health centers offer a sliding fee scale, with or without insurance.",
                    "source": dict(SOURCES["hrsa"], checked_on=CHECKED)})
    out.append({"title": "Start small when it isn’t urgent",
                "why": "A campus clinic or video visit usually costs far less than an emergency room."})
    if profile.get("conditions"):
        out.append({"title": "Keep one regular clinician for your ongoing conditions",
                    "why": "Seeing the same person makes follow-ups and refills easier."})
    if profile.get("medications"):
        out.append({"title": "Ask whether a generic version is available",
                    "why": "Generic medicines usually cost much less than brand names."})
    return out


def view(profile, today=None):
    from .sbc import plan_for
    b = profile.get("plan_benefits")
    by_service = {s: plan_for(b, s) for s in ("primary_care", "follow_up", "same_day")} if b else {}
    return {"plan_by_service": by_service, "benefits": b,"profile": {k: v for k, v in profile.items() if k != "done"}, "age": age(profile, today),
            "todos": todos(profile, today), "choices": better_choices(profile),
            "complete": bool(profile.get("birth_year"))}
