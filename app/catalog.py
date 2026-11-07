"""Small sourced Boston directory; synthetic examples live in a separate mode."""
from copy import deepcopy
from datetime import date

SOURCES_CHECKED = "2026-11-07"
REAL = [
    {"id": "fenway", "name": "Fenway Health · Primary Care", "kind": "Community clinic",
     "url": "https://fenwayhealth.org/care/medical/primary-care/",
     "address": "Boston, MA · confirm the appointment location", "city": "Boston", "state": "MA",
     "services": ["primary_care", "follow_up"], "source_note": "Official primary-care service page. New-patient availability, costs and network participation need confirmation."},
    {"id": "south-end", "name": "NeighborHealth · South End", "kind": "Community health center",
     "url": "https://www.neighborhealth.com/en/community/south-end/",
     "address": "1601 Washington Street, Boston, MA", "city": "Boston", "state": "MA",
     "services": [], "source_note": "Official location page. Confirm the requested adult service, clinician and appointment availability."},
]


def candidates(city, state, demo=False, service="primary_care"):
    today = date.today().isoformat()
    if demo:
        specs = [("harbor", "Harbor Community Clinic", "Community clinic", 120, 180, 4.6, 124, ["English", "Chinese"], 42.342, -71.09),
                 ("park", "Dr. Maya Chen · Parkside Practice", "Doctor's office", 165, 210, 4.9, 86, ["English", "Chinese"], 42.35, -71.075),
                 ("river", "Riverside Hospital · Outpatient Primary Care", "Hospital outpatient clinic", 290, 360, 4.7, 210, ["English", "Spanish"], 42.365, -71.065),
                 ("maple", "Maple Neighborhood Health", "Community clinic", 95, 150, 4.3, 62, ["English", "Spanish"], 42.329, -71.1)]
        return [dict(id=key, name=name, kind=kind, url="", address="Fictional Boston location", city="Boston", state="MA",
                     demo=True, services=[service], languages=languages, lat=lat, lon=lon, checked_on=today,
                     source_note="Fictional demonstration provider. All prices, ratings, locations and plan relationships are synthetic.",
                     cash={"amount": cash, "service": service, "scope_confirmed": True, "source": "Synthetic demo quote", "checked_on": today},
                     coverage={"Demo Student PPO": {"network": "demo", "allowed_amount": allowed, "service": service,
                                                   "scope_confirmed": True, "source": "Synthetic demo plan relationship", "checked_on": today}},
                     rating={"value": rating, "count": count, "source": "Synthetic patient reviews", "checked_on": today})
                for key, name, kind, cash, allowed, rating, count, languages, lat, lon in specs]
    if city.casefold() != "boston" or state.upper() != "MA":
        return []
    return [dict(deepcopy(item), demo=False, cash={}, coverage={}, rating=None, languages=[], checked_on=SOURCES_CHECKED)
            for item in REAL]
