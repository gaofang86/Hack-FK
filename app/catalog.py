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


BROOKLINE = [
    {"id": "bwh-brookline", "name": "Brigham and Women's Primary Care Associates of Brookline",
     "kind": "Outpatient primary care", "url": "https://www.massgeneralbrigham.org/en/locations/brookline-ma/brigham-and-womens-primary-care-associates-of-brookline-loc0000280904",
     "address": "1 Brookline Place, Suite 225, Brookline, MA 02445", "phone": "857-307-4400",
     "city": "Brookline", "state": "MA", "services": ["primary_care", "follow_up"],
     "source_note": "Official location page lists adult primary-care services. Exact clinician, new-patient acceptance, NUSHP network, complete charges and appointments are unconfirmed."},
    {"id": "bilh-beacon", "name": "Beth Israel Lahey Health Primary Care – 1180 Beacon Street",
     "kind": "Primary care practice", "url": "https://bilh.org/locations/bilh-pc-1180-beacon",
     "address": "1180 Beacon Street, 8th floor, Brookline, MA 02446", "phone": "617-734-2433",
     "city": "Brookline", "state": "MA", "services": ["primary_care", "follow_up"],
     "source_note": "Official page lists adult physicals and primary-care services. In neighboring ZIP 02446; travel distance, new-patient acceptance, exact-plan network and price remain unconfirmed."},
]


def candidates(city, state, demo=False, service="primary_care"):
    today = date.today().isoformat()
    if demo and service == "same_day":
        specs = [("walkin", "Harbor Walk-in Urgent Care", "Urgent care clinic", 175, 240, 4.4, 318, ["English", "Chinese"], 42.347, -71.087),
                 ("campus", "Fictional University Health Center", "Campus health clinic", 40, 120, 4.2, 96, ["English", "Chinese", "Spanish"], 42.339, -71.089),
                 ("northside", "Northside Express Care", "Urgent care clinic", 210, 260, 4.6, 541, ["English", "Spanish"], 42.351, -71.079)]
    elif demo:
        specs = [("harbor", "Harbor Community Clinic", "Community clinic", 120, 180, 4.6, 124, ["English", "Chinese"], 42.342, -71.09),
                 ("park", "Dr. Maya Chen · Parkside Practice", "Doctor's office", 165, 210, 4.9, 86, ["English", "Chinese"], 42.35, -71.075),
                 ("river", "Riverside Hospital · Outpatient Primary Care", "Hospital outpatient clinic", 290, 360, 4.7, 210, ["English", "Spanish"], 42.365, -71.065),
                 ("maple", "Maple Neighborhood Health", "Community clinic", 95, 150, 4.3, 62, ["English", "Spanish"], 42.329, -71.1)]
    if demo:
        return [dict(id=key, name=name, kind=kind, url="", address="Fictional Boston location", city="Boston", state="MA",
                     demo=True, services=[service], languages=languages, lat=lat, lon=lon, checked_on=today,
                     source_note="Fictional demonstration provider. All prices, ratings, locations and plan relationships are synthetic.",
                     cash={"amount": cash, "service": service, "scope_confirmed": True, "source": "Synthetic demo quote", "checked_on": today},
                     coverage={"Demo Student PPO": {"network": "demo", "allowed_amount": allowed, "service": service,
                                                   "scope_confirmed": True, "source": "Synthetic demo plan relationship", "checked_on": today}},
                     rating={"value": rating, "count": count, "source": "Synthetic patient reviews", "checked_on": today})
                for key, name, kind, cash, allowed, rating, count, languages, lat, lon in specs]
    if service == "same_day" or city.casefold() not in ("boston", "brookline") or state.upper() != "MA":
        # No sourced same-day directory yet: real same-day results come only from live search.
        return []
    return [dict(deepcopy(item), demo=False, cash={}, coverage={}, rating=None, languages=[], checked_on=SOURCES_CHECKED)
            for item in (BROOKLINE if city.casefold() == "brookline" else REAL)]
