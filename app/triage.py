"""Where to go, decided by fixed, readable rules on this laptop.

This is care *navigation*, not diagnosis. The rules choose between kinds of places
(911/ER, urgent care, campus clinic, telehealth, primary care) using the general
"when to go to the ER vs urgent care" guidance that US hospitals and insurers publish.
Every recommendation names the rule that produced it. The local model never decides
the level of care; it only explains the decision in your language.
"""
import re

# id -> (label shown to the user, words that reveal it, level)
# Levels: emergency > same_day > soon > routine
CHECKS = {
    # emergency: call 911
    "chest_pain": ("Chest pain, pressure or tightness", ["chest pain"], "emergency"),
    "breathing": ("Hard to breathe, or can't finish a sentence", ["trouble breathing"], "emergency"),
    "stroke": ("Face drooping, arm weakness, slurred or confused speech", ["stroke symptoms"], "emergency"),
    "fainted": ("Fainted, had a seizure, or is hard to wake up", ["fainting", "seizure"], "emergency"),
    "bleeding": ("Bleeding that won't stop with pressure", ["heavy bleeding"], "emergency"),
    "allergy_severe": ("Swelling of lips, tongue or throat after food, medicine or a sting",
                       ["allergic reaction"], "emergency"),
    "head_injury": ("Head injury with confusion, vomiting or passing out", ["head injury"], "emergency"),
    "worst_headache": ("Sudden, severe 'worst ever' headache", ["severe headache"], "emergency"),
    "self_harm": ("Thinking about hurting or killing yourself", ["self-harm"], "crisis"),
    "poison": ("Swallowed something poisonous or too much medicine", ["poisoning", "overdose"], "poison"),
    # same day
    "high_fever": ("Fever of 103°F / 39.4°C or higher", ["high fever"], "same_day"),
    "injury": ("Possible broken bone, bad sprain, or a cut that may need stitches",
               ["sprain", "fracture", "cut"], "same_day"),
    "urination": ("Burning or pain when you pee", ["urinary pain"], "same_day"),
    "fluids": ("Vomiting or diarrhea and can't keep fluids down", ["vomiting", "diarrhea"], "same_day"),
    "eye": ("Eye injury, or a red painful eye", ["eye pain"], "same_day"),
    "severe_pain": ("Pain you would rate 7 or more out of 10", ["severe pain"], "same_day"),
    # soon (1-2 days)
    "fever": ("Fever under 103°F / 39.4°C", ["fever"], "soon"),
    "sore_throat": ("Sore throat or ear pain", ["sore throat", "ear pain"], "soon"),
    "rash": ("New rash or skin problem", ["rash"], "soon"),
    "cough": ("Cough, cold or flu symptoms", ["cough", "cold", "flu"], "soon"),
    "mental": ("Feeling anxious, low or overwhelmed (not in danger)", ["anxiety", "depression"], "soon"),
    # routine
    "refill": ("Need a prescription refill or a new prescription", ["prescription"], "routine"),
    "checkup": ("Checkup, vaccines, or a form signed", ["checkup", "vaccine"], "routine"),
}

# Words in the free-text description that suggest an emergency the user didn't tick.
RED_FLAG_WORDS = {
    "chest_pain": r"chest (pain|pressure|tight)",
    "breathing": r"(can'?t|cannot|hard to|trouble|difficulty) breath",
    "stroke": r"slurred|face (droop|numb)|one side (of my )?(body|face)",
    "fainted": r"faint|passed out|seizure|unconscious",
    "self_harm": r"suicid|kill myself|end my life|hurt myself|self[- ]harm",
    "poison": r"overdos|poison|swallowed",
    "allergy_severe": r"(throat|tongue|lips?) (is |are )?(swell|swollen|closing)",
    "bleeding": r"won'?t stop bleeding|bleeding (a lot|heavily)",
    "worst_headache": r"worst headache",
}

LEVEL_ORDER = ["routine", "soon", "same_day", "emergency"]

VENUES = {
    "911": "Call 911",
    "er": "Emergency room",
    "urgent_care": "Urgent care clinic",
    "campus_health": "Campus health clinic",
    "telehealth": "Telehealth (video visit)",
    "primary_care": "Primary care appointment",
}

HOTLINES = {
    "crisis": {"name": "988 Suicide & Crisis Lifeline", "how": "Call or text 988 (24/7, free, interpreters available)"},
    "poison": {"name": "Poison Control", "how": "Call 1-800-222-1222 (24/7, free)"},
    "emergency": {"name": "Emergency services", "how": "Call 911"},
}


def _level(checks, severity):
    levels = [CHECKS[c][2] for c in checks if c in CHECKS]
    if "crisis" in levels or "emergency" in levels:
        return "emergency"
    if "poison" in levels:
        return "emergency"
    if severity is not None and severity >= 7:
        levels.append("same_day")
    known = [lv for lv in levels if lv in LEVEL_ORDER]
    return max(known, key=LEVEL_ORDER.index) if known else "soon"


def scan_text(description):
    """Red-flag words in the description that the user didn't tick. Runs only on this laptop."""
    hits = []
    for cid, pat in RED_FLAG_WORDS.items():
        if re.search(pat, description or "", re.I):
            hits.append(cid)
    return hits


def decide(checks, description="", severity=None, days=None):
    """Return the recommended level of care with ordered options and the rules that fired."""
    checks = [c for c in checks if c in CHECKS]
    noticed = [c for c in scan_text(description) if c not in checks]
    level = _level(checks + noticed, severity)
    kinds = {CHECKS[c][2] for c in checks + noticed}
    rules = [f"You said: {CHECKS[c][0].lower()}" for c in checks]
    rules += [f"Your description mentions something that sounds like: {CHECKS[c][0].lower()}" for c in noticed]
    if severity is not None and severity >= 7:
        rules.append(f"You rated it {severity}/10")
    if days is not None and days >= 10 and level in ("soon", "routine"):
        level = "soon"
        rules.append(f"It has lasted {days} days, so it's worth seeing someone rather than waiting")

    hotlines = []
    if "crisis" in kinds:
        hotlines.append(HOTLINES["crisis"])
    if "poison" in kinds:
        hotlines.append(HOTLINES["poison"])

    if level == "emergency":
        options = ["911", "er"]
        headline = "This could be an emergency. Call 911 or go to the nearest emergency room now."
        if kinds == {"crisis"}:
            headline = ("Please reach out right now: call or text 988. If you might act on these thoughts "
                        "or are in danger, call 911.")
        elif kinds <= {"poison"}:
            headline = ("Call Poison Control now at 1-800-222-1222. If the person is hard to wake, "
                        "has trouble breathing, or has a seizure, call 911.")
        why = ("Hospital emergency rooms must check and stabilize you whether or not you have insurance "
               "or can pay (a federal law called EMTALA). Under the No Surprises Act, most plans must "
               "charge you in-network cost sharing for emergency care, even at an out-of-network hospital.")
    elif level == "same_day":
        options = ["urgent_care", "campus_health", "er"]
        headline = "Get seen today. An urgent care clinic or your campus clinic is usually the right place."
        why = ("Urgent care clinics treat things like sprains, cuts, high fevers and infections without an "
               "appointment, often with X-rays on site, and usually cost much less than an ER. Go to the ER "
               "instead if it gets worse or you notice any emergency sign.")
    elif level == "soon":
        options = ["campus_health", "telehealth", "urgent_care"]
        headline = "See someone in the next day or two. Start with your campus clinic or a video visit."
        why = ("Common illnesses like colds, sore throats and rashes can usually be handled by your campus "
               "clinic or a telehealth visit, which are typically the cheapest options on student plans.")
    else:
        options = ["campus_health", "primary_care", "telehealth"]
        headline = "This can be booked as a regular appointment."
        why = "Refills, checkups and forms are handled by appointment, not urgent or emergency care."

    if "mental" in kinds and level != "emergency":
        rules.append("Your campus counseling service can also see you; ask the campus clinic for it")

    return {
        "level": level,
        "headline": headline,
        "why": why,
        "options": options,
        "rules": rules,
        "noticed": noticed,
        "hotlines": hotlines,
        "disclaimer": ("FirstVisit helps you decide where to go. It doesn't diagnose. If you think "
                       "it's an emergency, call 911."),
    }


def symptom_terms(checks):
    """Words that would reveal what's wrong; added to the DLP filter so searches can't carry them."""
    terms = []
    for c in checks:
        if c in CHECKS:
            terms += CHECKS[c][1]
    return terms


def checks_view():
    return [{"id": k, "label": v[0], "level": v[2]} for k, v in CHECKS.items()]
