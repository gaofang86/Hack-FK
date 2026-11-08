"""Private case input, deterministic preference ordering, and quote updates."""
from datetime import date
import hashlib
import math
from urllib.parse import urlparse

from .benefits import cash_cost, clean_plan, comparison, insured_cost, number
from .triage import CHECKS, decide

SERVICES = {"primary_care": "Primary-care appointment", "follow_up": "Primary-care follow-up",
            "same_day": "Same-day visit for a non-emergency problem"}


def text(value, length=300):
    return str(value or "").strip()[:length]


def safe_url(value):
    value = text(value, 2000)
    parsed = urlparse(value)
    return value if parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username and not parsed.password else ""


def safety_check(raw):
    """Person-first safety step. Runs on this machine with fixed rules; never sent anywhere."""
    checks = raw.get("checks")
    if checks is None:
        return None
    if not isinstance(checks, list) or not all(isinstance(c, str) for c in checks):
        raise ValueError("Invalid health check")
    picked = [c for c in checks if c in CHECKS]
    severity = number(raw.get("severity"), "Pain score", 10)
    result = decide(picked, text(raw.get("description"), 3000), None if severity is None else int(severity))
    if not picked and not result["noticed"] and severity is None:
        result.update(level="routine", options=["primary_care", "campus_health", "telehealth"],
                      headline="No warning signs reported. This can be arranged as a regular appointment.",
                      why="You told us nothing feels wrong right now.",
                      rules=["You reported no current symptoms"])
    result["checks"] = picked
    return result


def clean_input(raw):
    city, state = text(raw.get("city"), 70), text(raw.get("state"), 2).upper()
    if not city or len(state) != 2 or not state.isalpha():
        raise ValueError("Enter a city and two-letter US state")
    if raw.get("insurance") not in ("yes", "no"):
        raise ValueError("Choose whether you have insurance")
    service = raw.get("service", "primary_care")
    if service not in SERVICES:
        raise ValueError("This version supports primary-care appointments, follow-ups and same-day care")
    visit_date = text(raw.get("visit_date"), 10)
    try:
        visit_date = date.fromisoformat(visit_date).isoformat()
        if date.fromisoformat(visit_date) < date.today():
            raise ValueError()
    except ValueError:
        raise ValueError("Choose today or a future visit date")
    age = number(raw.get("age"), "Age", 120)
    adult = age >= 18 if age is not None else raw.get("adult") is True
    safety = safety_check(raw)
    if safety and safety["level"] == "emergency":
        raise ValueError(safety["headline"])
    if safety and safety["level"] == "same_day" and service != "same_day":
        raise ValueError(safety["headline"] + " Choose “Find care today” to look for same-day care.")
    if not adult:
        raise ValueError("This version supports adults (18+). For a child or teen, contact a pediatric clinician.")
    if raw.get("routine_confirmed") is not True and safety is None:
        raise ValueError("This version is for adults arranging known non-emergency outpatient care. Contact a clinician if you need help deciding what care you need.")
    if raw.get("demo") is True and (city.casefold() != "boston" or state != "MA"):
        raise ValueError("The fictional example uses Boston. Start a new real search to change cities.")
    priority = raw.get("priority", "balanced")
    if priority not in ("balanced", "cost", "rating", "distance"):
        raise ValueError("Choose a valid ranking priority")
    zip_code = text(raw.get("zip"), 10)
    if zip_code and (len(zip_code) != 5 or not zip_code.isdigit()):
        raise ValueError("Enter a five-digit ZIP or leave it blank")
    months = number(raw.get("months", 1), "Premium months", 12)
    if months is None or months < 1 or not months.is_integer():
        raise ValueError("Premium months must be a whole number from 1 to 12")
    result = dict(city=city, state=state, zip=zip_code, service=service, visit_date=visit_date,
                  insurance=raw["insurance"], wants_insurance=raw.get("wants_insurance") is True,
                  priority=priority, budget=number(raw.get("budget"), "Visit budget"),
                  language=text(raw.get("language", "English"), 50), description=text(raw.get("description"), 3000),
                  history=text(raw.get("history"), 3000), medications=text(raw.get("medications"), 1000),
                  plan=clean_plan(raw.get("plan")), months=int(months), demo=raw.get("demo") is True,
                  scenario="neu_student" if raw.get("scenario") == "neu_student" else "",
                  routine_confirmed=True, adult=True, age=None if age is None else int(age),
                  need=raw.get("need") if raw.get("need") in ("checkup", "refill", "follow_up") else "",
                  safety=None if safety is None else {k: safety[k] for k in ("level", "headline", "rules", "checks")},
                  lat=None, lon=None)
    if raw.get("lat") is not None and raw.get("lon") is not None:
        try:
            lat, lon = float(raw["lat"]), float(raw["lon"])
        except (TypeError, ValueError):
            raise ValueError("Invalid coordinates")
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Invalid coordinates")
        result.update(lat=lat, lon=lon)
    return result


def distance(person, provider):
    if any(v is None for v in (person.get("lat"), person.get("lon"), provider.get("lat"), provider.get("lon"))):
        return None
    a, b = map(math.radians, (person["lat"], provider["lat"]))
    dlat = b - a
    dlon = math.radians(provider["lon"] - person["lon"])
    h = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlon / 2) ** 2
    return round(3958.8 * 2 * math.asin(min(1, math.sqrt(h))), 1)


def ranked(case):
    person, providers = case["input"], case["providers"]
    rows = []
    for provider in providers:
        cash = cash_cost(provider, person["service"])
        insured = insured_cost(provider, person.get("plan"), person["visit_date"], person["service"])
        chosen, pathway = cash, "Self-pay"
        if person["insurance"] == "yes" and insured["amount"] is not None:
            if cash["amount"] is None or insured["amount"] <= cash["amount"]:
                chosen, pathway = insured, "Your insurance"
        supported = person["service"] in provider.get("services", [])
        price = chosen["amount"]
        over_budget = person.get("budget") is not None and price is not None and price > person["budget"]
        language_match = person["language"].casefold() in [v.casefold() for v in provider.get("languages", [])]
        miles = distance(person, provider)
        rating = provider.get("rating")
        reasons = ["Requested service listed" if supported else "Confirm that this location offers your requested service"]
        if language_match:
            reasons.append(f"{person['language']} listed")
        elif person["language"] != "English":
            reasons.append("Ask about language or interpreter support")
        if price is not None:
            reasons.append("Above your visit budget" if over_budget else "Within your visit budget" if person.get("budget") is not None else "A scoped price is available")
        if person["insurance"] == "yes" and pathway == "Self-pay":
            reasons.append("Compare cash with your plan; cash payments may not count toward your deductible")
        if not provider.get("demo"):
            reasons.append("New-patient acceptance and appointment availability need confirmation")
        from .workflow import current_answers
        answers = current_answers(provider, person)
        unavailable = bool(answers.get("availability", {}).get("result") == "no" and not answers["availability"]["stale"])
        if unavailable:
            reasons.append("Office reported no suitable new-patient appointment; keep this as a backup, not an actionable choice")
        rows.append(dict(answers=answers, unavailable=unavailable, provider=provider, cash=cash, insured=insured, cost=chosen, pathway=pathway,
                         supported=supported, miles=miles, language_match=language_match, over_budget=over_budget,
                         reasons=reasons, confirmation=confirmation_tasks(person, provider, cash, insured), comparison=comparison(provider, person.get("plan"), person["visit_date"], person["service"], person["months"])))

    def key(row):
        p = row["provider"]
        price = row["cost"]["amount"]
        price_key = price if price is not None else math.inf
        review = p.get("rating")
        rating_key = -review["value"] if review else math.inf
        dist_key = row["miles"] if row["miles"] is not None else math.inf
        base = (row["unavailable"], not row["supported"], row["over_budget"])
        priority = person["priority"]
        if priority == "rating":
            return base + (rating_key, price_key, dist_key, p["name"])
        if priority == "distance":
            return base + (dist_key, price_key, rating_key, p["name"])
        if priority == "cost":
            return (row["unavailable"], not row["supported"], price is None, row["over_budget"], price_key, rating_key, dist_key, p["name"])
        return base + (not row["language_match"], price_key, rating_key, dist_key, p["name"])
    rows.sort(key=key)
    return rows


def from_search(result, service):
    rows = []
    for place in result["places"]:
        url = safe_url(place.get("url"))
        if not url:
            continue
        rows.append(dict(id=hashlib.sha256(url.encode()).hexdigest()[:16], name=text(place["title"], 150),
                         kind="Search lead · verify provider", url=url, address="Confirm the location on the source page",
                         demo=False, services=[], languages=[], cash={}, coverage={}, rating=None,
                         checked_on=date.today().isoformat(), source_note="Search result; requested service, provider identity and location need confirmation.",
                         facts=place.get("facts", [])))
    return rows


def update_quote(provider, raw, service):
    checked = text(raw.get("checked_on"), 10)
    try:
        checked = date.fromisoformat(checked).isoformat()
        if date.fromisoformat(checked) > date.today():
            raise ValueError()
    except ValueError:
        raise ValueError("Use the actual date checked (today or earlier)")
    source = text(raw.get("source"), 500)
    if not source:
        raise ValueError("Record where the quote or confirmation came from")
    scope = raw.get("scope_confirmed") is True
    cash = number(raw.get("cash"), "Cash quote")
    if cash is not None:
        provider["cash"] = dict(amount=cash, service=service, scope_confirmed=scope, source=source, checked_on=checked)
    if raw.get("service_confirmed") is True:
        provider["services"] = sorted(set(provider.get("services", []) + [service]))
    name = text(raw.get("plan_name"), 120)
    if name:
        provider.setdefault("coverage", {})[name] = dict(network="user_confirmed" if raw.get("network_confirmed") is True else "unknown",
            allowed_amount=number(raw.get("allowed_amount"), "Allowed charge"), service=service,
            scope_confirmed=scope, source=source, checked_on=checked)
    rating = number(raw.get("rating"), "Patient rating", 5)
    if rating is not None:
        rating_source = safe_url(raw.get("rating_source"))
        count = number(raw.get("rating_count"), "Review count")
        if not rating_source or count is None or not count.is_integer() or count < 1:
            raise ValueError("A patient rating needs its source URL and a positive whole review count")
        provider["rating"] = dict(value=rating, count=int(count), source=rating_source, checked_on=checked, user_entered=True)
    provider["confirmation_source"] = source


def confirmation_tasks(person, provider, cash=None, insured=None):
    """Questions are scoped to this candidate; unknown price is not medical unsuitability."""
    cash = cash if cash is not None else cash_cost(provider, person["service"])
    insured = insured if insured is not None else insured_cost(provider, person.get("plan"), person["visit_date"], person["service"])
    from .workflow import current_answers
    answers = current_answers(provider, person)
    tasks = []
    if person["service"] not in provider.get("services", []):
        tasks.append({"key": "service", "question": "Does this location offer the requested service for adults?"})
    if not provider.get("demo"):
        tasks.append({"key": "availability", "question": "Is the selected clinician accepting new adult patients, and what appointments can you confirm?"})
    if cash["amount"] is None:
        tasks.append({"key": "cash", "question": "What is the complete self-pay price for this visit, including facility and professional fees? Can I get a written estimate?"})
    if person["insurance"] == "yes" and insured["amount"] is None:
        plan = (person.get("plan") or {}).get("name") or "my exact plan (name still to confirm)"
        tasks.append({"key": "insurance", "question": f"Can the insurer and office confirm {plan} covers this clinician, location and service in-network? What benefit rule and allowed charge apply?", "reason": insured["reason"]})
    if person.get("language", "English") != "English":
        tasks.append({"key": "language", "question": f"Is {person['language']} language or interpreter support available, and is there a charge?"})
    if answers.get("referral", {}).get("result") == "yes" and not answers["referral"]["stale"]:
        action = answers.get("referral_action", {})
        if action.get("result") != "yes" or action.get("stale") or action.get("checked_on", "") < answers["referral"]["checked_on"]:
            tasks.append({"key": "referral_action", "question": "A referral or authorization was reported as required. Obtain it and confirm it applies to this appointment before booking."})
    tasks.append({"key": "referral", "question": "Is a referral or prior authorization required for this visit?"})
    return [t for t in tasks if t["key"] == "referral_action" or t["key"] not in answers or answers[t["key"]]["stale"] or answers[t["key"]]["result"] == "unknown"]
