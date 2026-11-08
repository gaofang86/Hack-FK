"""Explicit, service-scoped estimates. Unknown inputs never become a free visit."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import math


def number(value, label, maximum=1000000):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{label} must be a number")
    if not math.isfinite(result) or not 0 <= result <= maximum:
        raise ValueError(f"{label} must be between 0 and {maximum}")
    return result


def money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def clean_plan(raw):
    if not raw:
        return None
    name = str(raw.get("name", "")).strip()[:120]
    if not name:
        return None
    rule = raw.get("rule", "copay")
    if rule not in ("copay", "deductible"):
        raise ValueError("Choose a supported benefit rule")
    out = {"name": name, "rule": rule, "eligible": raw.get("eligible") is True}
    for key in ("start", "end"):
        value = raw.get(key, "")
        if value:
            try:
                value = date.fromisoformat(value).isoformat()
            except (TypeError, ValueError):
                raise ValueError("Use valid coverage dates")
        out[key] = value
    if out["start"] and out["end"] and out["end"] < out["start"]:
        raise ValueError("Coverage end must follow its start")
    for key in ("premium", "copay", "deductible_remaining", "oop_remaining"):
        out[key] = number(raw.get(key), key.replace("_", " "))
    out["coinsurance"] = number(raw.get("coinsurance"), "Coinsurance", 100)
    return out


def unknown(reason, status="unknown"):
    return {"amount": None, "status": status, "reason": reason, "breakdown": []}


def insured_cost(provider, plan, visit_date, service):
    if not plan:
        return unknown("Add the exact plan and service benefit to estimate your share.")
    if not plan.get("start"):
        return unknown("Confirm the coverage start date.")
    if visit_date < plan["start"]:
        return unknown("Coverage starts after this visit. This plan cannot be assumed to pay for it.", "not_active")
    if plan.get("end") and visit_date > plan["end"]:
        return unknown("This visit falls after the entered coverage end date.", "not_active")
    evidence = provider.get("coverage", {}).get(plan["name"], {})
    if evidence.get("network") not in ("user_confirmed", "demo"):
        return unknown("Confirm this exact plan, provider, location and service are in-network.")
    if evidence.get("service") != service or not evidence.get("scope_confirmed"):
        return unknown("Confirm the quoted service and all applicable visit charges.")
    if not evidence.get("checked_on"):
        return unknown("Add the date the network and price information was checked.")
    if (date.fromisoformat(visit_date) - date.fromisoformat(evidence["checked_on"])).days > 30:
        return unknown("Network/price information is over 30 days old; reconfirm it for this visit.")
    limit = plan.get("oop_remaining")
    if plan["rule"] == "copay":
        if plan.get("copay") is None:
            return unknown("Enter the copay for this service; this rule assumes the deductible does not apply.")
        share = plan["copay"]
        steps = [{"label": "Service copay (deductible does not apply)", "amount": share}]
    else:
        allowed = evidence.get("allowed_amount")
        deductible, pct = plan.get("deductible_remaining"), plan.get("coinsurance")
        if any(v is None for v in (allowed, deductible, pct, limit)):
            return unknown("Need the allowed charge, remaining deductible, coinsurance and remaining out-of-pocket limit.")
        deductible_part = min(allowed, deductible)
        coinsurance_part = (allowed - deductible_part) * pct / 100
        share = deductible_part + coinsurance_part
        steps = [{"label": "Applied to remaining deductible", "amount": money(deductible_part)},
                 {"label": "Coinsurance on the remainder", "amount": money(coinsurance_part)}]
    if limit is not None and limit < share:
        steps.append({"label": "Reduction at remaining out-of-pocket limit", "amount": money(limit - share)})
        share = limit
    return {"amount": money(share), "status": "demo" if evidence["network"] == "demo" else "conditional",
            "reason": "Based on entered benefits and service-specific network/charge information. Additional services are excluded.",
            "breakdown": steps, "source": evidence.get("source", ""), "checked_on": evidence["checked_on"]}


def cash_cost(provider, service):
    quote = provider.get("cash", {})
    if quote.get("amount") is None or quote.get("service") != service or not quote.get("scope_confirmed"):
        return unknown("Ask for a quote covering this visit, including any facility or professional fees.")
    try:
        checked = date.fromisoformat(quote.get("checked_on", ""))
    except ValueError:
        return unknown("Add the date this quote was checked.")
    if (date.today() - checked).days > 30 or checked > date.today():
        return unknown("The cash quote needs reconfirmation (missing, future or over 30 days old).")
    return {"amount": quote["amount"], "status": "demo" if provider.get("demo") else "user_quote",
            "reason": "Scoped visit quote; extra testing or treatment may cost more.",
            "source": quote.get("source", ""), "checked_on": quote.get("checked_on", ""), "breakdown": []}


def comparison(provider, plan, visit_date, service, months=1):
    cash = cash_cost(provider, service)
    insured = insured_cost(provider, plan, visit_date, service)
    result = {"cash": cash, "insured": insured, "months": months, "premium_total": None,
              "total_with_plan": None, "visit_difference": None, "net_difference": None,
              "eligible": bool(plan and plan.get("eligible")),
              "scope": "One specified visit plus the selected number of premium payments. Other care, subsidies not entered in the premium, and future claims are not modeled."}
    if not plan or plan.get("premium") is None:
        result["note"] = "Add the premium you would actually pay to compare the total. Eligibility and subsidies are not inferred."
        return result
    result["premium_total"] = money(plan["premium"] * months)
    if insured["amount"] is not None:
        result["total_with_plan"] = money(insured["amount"] + result["premium_total"])
        if cash["amount"] is not None:
            result["visit_difference"] = money(cash["amount"] - insured["amount"])
            result["net_difference"] = money(cash["amount"] - result["total_with_plan"])
    result["note"] = "Hypothetical until enrollment, eligibility, effective dates and provider participation are confirmed. Never delay needed care to wait for coverage."
    return result
