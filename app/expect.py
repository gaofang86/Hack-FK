"""What to expect while the search runs: fixed rules on this machine, no model, no network.

Everything here is deterministic. Dollar figures are either the user's own entries or the
illustrative fees FAIR Health publishes in its consumer guide, applied to the user's plan
with the same arithmetic as benefits.py. Nothing here is a quote.
"""
from .benefits import money

SOURCES = {
    "fair_health": {
        "title": "FAIR Health Consumer: Emergency care and urgent care",
        "url": "https://www.fairhealthconsumer.org/en/insurance-basics/healthcare/emergency-care-and-urgent-care",
        "checked_on": "2026-11-07",
    },
    "gfe": {
        "title": "CMS: No Surprises — your rights, including Good Faith Estimates for uninsured or self-pay care",
        "url": "https://www.cms.gov/newsroom/fact-sheets/no-surprises-understand-your-rights-against-surprise-medical-bills",
        "checked_on": "2026-11-07",
    },
}

# FAIR Health's illustrative provider fees (in-network, routine care example). Not averages.
EXAMPLE_FEES = {"urgent_care": 300, "er": 1000}

VENUES = {
    "campus_health": {"name": "Campus health clinic",
                      "fits": "Often the first stop for students. Check your school's hours and any visit fee."},
    "telehealth": {"name": "Telehealth (video visit)",
                   "fits": "Works for many common problems. It can't examine an eye up close or X-ray an injury."},
    "urgent_care": {"name": "Urgent care clinic",
                    "fits": "Walk in the same day for sprains, cuts, infections and fevers. Not for major emergencies.",
                    "cost": "Usually much less than an emergency room.", "source": "fair_health"},
    "er": {"name": "Emergency room",
           "fits": "Go if it gets worse or you notice any warning sign.",
           "cost": "Costs much more than urgent care, and can send two bills: one from the hospital, one from the doctor.",
           "source": "fair_health"},
    "primary_care": {"name": "Primary care appointment",
                     "fits": "For planned care. Usually booked days or weeks ahead."},
}


def _share(plan, fee):
    """What the user would pay on an example fee under their entered plan, or None with a reason."""
    if plan["rule"] == "copay":
        if plan.get("copay") is None:
            return None, "Add your copay to see this."
        share = plan["copay"]
        how = f"Your entered copay of ${plan['copay']:,.2f}, if your plan uses it for this kind of visit"
    else:
        d, pct = plan.get("deductible_remaining"), plan.get("coinsurance")
        if d is None or pct is None:
            return None, "Add your remaining deductible and coinsurance to see this."
        first = min(fee, d)
        share = first + (fee - first) * pct / 100
        how = f"${first:,.2f} toward your deductible, then {pct:g}% of the rest"
    limit = plan.get("oop_remaining")
    if limit is not None and share > limit:
        share, how = limit, how + f", capped at your out-of-pocket limit of ${limit:,.2f}"
    return money(share), how


def illustration(person):
    """Example fees run through the user's own situation. Labeled as an illustration."""
    plan, rows = person.get("plan"), []
    for venue, fee in EXAMPLE_FEES.items():
        row = {"venue": VENUES[venue]["name"], "example_fee": fee}
        if person.get("insurance") == "yes" and plan:
            amount, how = _share(plan, fee)
            if venue == "er" and plan["rule"] == "copay":
                amount, how = None, "Emergency rooms usually have their own, higher copay. Find the “emergency room” line in your plan’s benefits summary."
            row.update(you_pay=amount, how=how)
        elif person.get("insurance") == "yes":
            row.update(you_pay=None, how="Add your plan details to see your share.")
        else:
            row.update(you_pay=fee, how="Without insurance you pay the full fee unless you ask for a self-pay discount.")
        rows.append(row)
    return {"rows": rows, "source": SOURCES["fair_health"],
            "label": "Illustration using FAIR Health’s example fees. Not a quote: real prices vary by place and by what’s done at the visit."}


def expectations(person):
    safety = person.get("safety") or {}
    same_day = person.get("service") == "same_day"
    order = ["urgent_care", "campus_health", "telehealth", "er"] if same_day else ["primary_care", "campus_health", "telehealth"]
    options = [dict(VENUES[v], id=v, source=SOURCES.get(VENUES[v].get("source", ""))) for v in order]
    tips = ["Bring a photo ID and your insurance card, if you have one.",
            "Bring a list of your medicines and allergies.",
            "Ask for a free interpreter if you’d like one. Most clinics must offer language help."]
    if person.get("insurance") != "yes":
        tips.append("Ask for the self-pay price before you’re seen. For scheduled care you can ask for a written Good Faith Estimate.")
    else:
        tips.append("Ask the front desk whether they take your exact plan before you’re seen.")
    return {
        "headline": safety.get("headline") or ("Care today" if same_day else "Planned care"),
        "options": options,
        "illustration": illustration(person) if same_day else None,
        "tips": tips,
        "sources": [SOURCES["fair_health"]] + ([SOURCES["gfe"]] if person.get("insurance") != "yes" else []),
        "computed": "Fixed rules on this device. No model and no network were used for this page.",
    }
