"""Where to find real, in-network providers. One interface, swappable implementations.

FirstVisit decides *what* to search for (kind of care, visit reason, place, plan). A source
turns that into results. Today the source is a prefilled Zocdoc results link that opens in
the user's own browser: the app itself sends nothing. When Zocdoc API credentials arrive,
a ZocdocApi source with the same `describe()` shape can return providers directly.

The Zocdoc IDs below were read from zocdoc.com result URLs on 2026-11-07. They are not a
documented interface and may change; the date is shown with every link.
"""
from urllib.parse import urlencode

CHECKED = "2026-11-07"
BASE = "https://www.zocdoc.com/search"

# (dr_specialty, reason_visit, what it means on Zocdoc)
VISITS = {
    "illness": ("153", "75", "Primary care · Illness"),
    "checkup": ("153", "76", "Primary care · Annual physical"),
    "follow_up": ("153", "1309", "Primary care · General follow up"),
    "urgent": ("513", "1542", "Urgent care · Urgent care consultation"),
}

# Explicit user-selected products only. Never infer an exact product from a plan name.
PLANS = [
    {"id": "bcbsma_blue_care_elect_ppo", "carrier": "573", "plan": "31215",
     "label": "Blue Cross Blue Shield of Massachusetts · Blue Care Elect (PPO)"},
]


def visit_kind(person):
    if person.get("service") == "same_day":
        return "urgent"
    if person.get("service") == "follow_up" or person.get("need") == "follow_up":
        return "follow_up"
    if person.get("need") == "checkup":
        return "checkup"
    return "illness"


def zocdoc_plan(person):
    if person.get("insurance") != "yes" or not person.get("plan"):
        return None
    product = person["plan"].get("zocdoc_product", "")
    return next((p for p in PLANS if p["id"] == product), None)


class ZocdocLink:
    name = "Zocdoc"
    kind = "link"

    def describe(self, person):
        specialty, reason, meaning = VISITS[visit_kind(person)]
        where = person.get("zip") or f"{person.get('city', '')}, {person.get('state', '')}".strip(", ")
        plan = zocdoc_plan(person)
        params = {"address": where, "dr_specialty": specialty, "reason_visit": reason,
                  "insurance_carrier": plan["carrier"] if plan else "", "insurance_plan": plan["plan"] if plan else "-1",
                  "day_filter": "AnyDay", "language": "-1", "offset": "0", "sort_type": "Default"}
        shares = [f"Location: {where}", f"Kind of visit: {meaning}"]
        if plan:
            shares.append(f"Insurance: {plan['label']}")
            note = "Filters by the exact product you selected. This is not confirmation of clinician participation; verify your plan, clinician, location and service."
        elif person.get("insurance") == "yes":
            note = "No exact product was selected here. Pick your exact plan on Zocdoc; a typed plan name never activates an insurance filter."
        else:
            note = "No insurance filter. Ask each office for its self-pay price."
        return {"source": self.name, "kind": self.kind, "url": f"{BASE}?{urlencode(params)}", "shares": shares,
                "in_network_filter": bool(plan), "note": note, "checked_on": CHECKED,
                "how": "Opening this link sends the listed search fields to Zocdoc in your browser. Its own privacy practices apply; browser traffic is outside FirstVisit’s gateway ledger."}


SOURCES = [ZocdocLink()]


def describe_all(person):
    return [s.describe(person) for s in SOURCES]
