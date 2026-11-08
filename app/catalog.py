"""Small sourced Boston directory; synthetic examples live in a separate mode."""
from copy import deepcopy
from datetime import date

SOURCES_CHECKED = "2026-11-08"
REAL = [
    {"id": "fenway", "name": "Fenway Health · Primary Care", "kind": "Community clinic",
     "url": "https://fenwayhealth.org/care/medical/primary-care/",
     "address": "1340 Boylston Street, Boston, MA 02215", "phone": "617-267-0900", "city": "Boston", "state": "MA",
     "booking_url": "https://fenwayhealth.org/mychart/online-scheduling/",
     "services": ["primary_care", "follow_up"], "source_note": "Official primary-care service page says primary care providers are at the main Health Center (Ansin Building, 1340 Boylston Street) and lists 617.267.0900. New-patient availability, costs and network participation need confirmation."},
    {"id": "south-end", "name": "NeighborHealth · South End", "kind": "Community health center",
     "url": "https://www.neighborhealth.com/en/community/south-end/",
     "address": "1601 Washington Street, Boston, MA", "city": "Boston", "state": "MA",
     "booking_url": "https://mychart.ebnhc.org/mychart/Authentication/Login",
     "services": [], "source_note": "Official location page. Confirm the requested adult service, clinician and appointment availability."},
    {"id": "nu-uhcs", "name": "Northeastern University Health and Counseling Services (UHCS)", "kind": "University health center",
     "url": "https://uhcs.northeastern.edu/",
     "address": "70 Forsyth Street, Suite 135, Boston, MA", "phone": "617-373-2772", "city": "Boston", "state": "MA",
     "services": ["primary_care", "follow_up"],
     "source_note": "Official UHCS page describes medical and mental health care for Northeastern's Boston campus; its appointments page says to call 617.373.2772 and bring NUID and insurance card. Eligibility, costs, insurance billing and appointment availability are unconfirmed."},
    {"id": "bidmc-hca", "name": "BIDMC Healthcare Associates (HCA) Primary Care", "kind": "Hospital outpatient primary care",
     "url": "https://bidmc.org/locations/healthcare-associates-boston",
     "address": "330 Brookline Avenue, Shapiro Clinical Center 6th Floor, Boston, MA 02215", "phone": "617-754-9600", "city": "Boston", "state": "MA",
     "services": ["primary_care", "follow_up"],
     "source_note": "Official BIDMC location page calls HCA BIDMC's primary care practice and says to call 617-754-9600 to request an appointment. Age groups served, new-patient acceptance, exact-plan network, price and appointments are unconfirmed."},
    {"id": "bwh-jen-center", "name": "Brigham and Women's Phyllis Jen Center for Primary Care", "kind": "Hospital outpatient primary care",
     "url": "https://www.massgeneralbrigham.org/en/locations/boston-ma/brigham-and-womens-phyllis-jen-center-for-primary-care-loc0000280300",
     "address": "75 Francis Street, Suite ASB1-2, Boston, MA 02115", "phone": "617-732-6040", "city": "Boston", "state": "MA",
     "services": ["primary_care", "follow_up"],
     "source_note": "Official Mass General Brigham location page says its providers are trained in the general medical care of adults. New-patient acceptance, exact-plan network, price and appointments are unconfirmed."},
    {"id": "mgh-back-bay", "name": "Massachusetts General Back Bay Healthcare Center", "kind": "Outpatient primary care",
     "url": "https://www.massgeneralbrigham.org/en/locations/boston-ma/massachusetts-general-back-bay-healthcare-center-loc0000280754",
     "address": "388 Commonwealth Avenue, Boston, MA 02215", "phone": "617-267-7171", "city": "Boston", "state": "MA",
     "services": ["primary_care", "follow_up"],
     "source_note": "Official Mass General Brigham location page says it provides primary and preventive care for patients of every age. New-patient acceptance, exact-plan network, price and appointments are unconfirmed."},
    {"id": "bmc-adult-pc", "name": "Boston Medical Center · Adult Primary Care (Crosstown Center)", "kind": "Hospital outpatient primary care",
     "url": "https://www.bmc.org/adult-primary-care",
     "address": "801 Massachusetts Avenue, 5th and 6th Floors, Boston, MA 02118", "phone": "617-414-5951", "city": "Boston", "state": "MA",
     "services": ["primary_care", "follow_up"],
     "source_note": "Official BMC page lists comprehensive adult primary care at Crosstown Center, including an Immigrant and Refugee Health Program. New-patient acceptance, exact-plan network, price and appointments are unconfirmed."},
    {"id": "dimock-adult", "name": "The Dimock Center · Adult Medicine", "kind": "Community health center",
     "url": "https://dimock.org/services/adult-medicine/",
     "address": "45 Dimock Street, Richards Building 2nd Floor, Roxbury, MA 02119", "phone": "617-442-8800 x2023", "city": "Boston", "state": "MA",
     "booking_url": "https://dimock.org/patients-visitors/book-an-appointment/",
     "services": ["primary_care", "follow_up"],
     "source_note": "Official Dimock page lists primary care for adults (19+), check-ups and chronic-condition care. New-patient acceptance, exact-plan network, price and appointments are unconfirmed."},
    {"id": "sjp-chc", "name": "Southern Jamaica Plain Community Health Center", "kind": "Community health center",
     "url": "https://www.massgeneralbrigham.org/en/locations/jamaica-plain-ma/southern-jamaica-plain-community-health-center-loc0000280788",
     "address": "640 Centre Street, Jamaica Plain, MA 02130", "phone": "617-983-4100", "city": "Boston", "state": "MA",
     "services": [],
     "source_note": "Official Mass General Brigham location page lists the center and an Adult Medicine line but does not explicitly list adult primary care. Confirm the adult service, new-patient acceptance, exact-plan network, price and appointments."},
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
     "booking_url": "https://mychart.bilh.org",
     "source_note": "Official page lists adult physicals and primary-care services. In neighboring ZIP 02446; travel distance, new-patient acceptance, exact-plan network and price remain unconfirmed."},
    {"id": "bwh-family-care-brookline", "name": "Brigham and Women's Family Care Associates (Mass General Brigham Healthcare Center Brookline)",
     "kind": "Outpatient primary care", "url": "https://www.massgeneralbrigham.org/en/locations/brookline-ma/mass-general-brigham-healthcare-center-brookline-loc0000247013",
     "address": "1285 Beacon Street, Brookline, MA 02446", "phone": "617-983-7025",
     "city": "Brookline", "state": "MA", "services": ["primary_care", "follow_up"],
     "source_note": "Official Mass General Brigham page says Family Care Associates provides comprehensive pediatric and adult primary care at this center. New-patient acceptance, exact-plan network, price and appointments are unconfirmed."},
]


# Named clinicians from official public profiles. Not exact-plan network, price or appointment proof.
CLINICIANS = [
    {"id": "dr-eric-hwang", "name": "Eric L. Hwang, MD", "practice_id": "bilh-beacon",
     "url": "https://primarycare.bilh.org/details/6789/eric-hwang-primary_care-brookline", "checked_on": "2026-11-08",
     "source_note": "Official BILH profile lists primary care at 1180 Beacon Street, says currently accepting new patients, and lists Blue Cross Blue Shield - MA. Exact plan/network, appointments and price are unconfirmed."},
    {"id": "dr-jonathan-berz", "name": "Jonathan P. Berz, MD", "practice_id": "bmc-adult-pc",
     "url": "https://www.bmc.org/about-us/directory/doctor/jonathan-p-berz-md", "checked_on": "2026-11-08",
     "source_note": "Official BMC profile lists Adult Primary Care at Crosstown Center, 801 Massachusetts Ave., 6th Floor. New-patient acceptance, exact-plan network, appointments and price are unconfirmed."},
    {"id": "dr-daniel-chen", "name": "Daniel C. Chen, MD", "practice_id": "bmc-adult-pc",
     "url": "https://www.bmc.org/about-us/directory/doctor/daniel-c-chen-md", "checked_on": "2026-11-08",
     "source_note": "Official BMC profile lists a board-certified primary care physician in Adult Primary Care at Crosstown Center, 801 Massachusetts Ave., 6th Floor. New-patient acceptance, exact-plan network, appointments and price are unconfirmed."},
]


def _norm(text):
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in text).split())


def directory_search(query, limit=10):
    """Local name/address lookup over sourced entries only. Nothing is fetched."""
    terms = [t for t in _norm(query or "").split() if t not in ("dr", "doctor", "md")]
    if not terms:
        return []
    practices = {p["id"]: p for p in REAL + BROOKLINE}
    entries = [dict(type="clinician", id=c["id"], name=c["name"], practice=practices[c["practice_id"]]["name"],
                    address=practices[c["practice_id"]]["address"], phone=practices[c["practice_id"]].get("phone", ""), booking_url=practices[c["practice_id"]].get("booking_url", ""),
                    url=c["url"], source_note=c["source_note"], checked_on=c["checked_on"]) for c in CLINICIANS]
    entries += [dict(type="practice", id=p["id"], name=p["name"], practice=p["kind"], address=p["address"], phone=p.get("phone", ""), booking_url=p.get("booking_url", ""),
                     url=p["url"], source_note=p["source_note"], checked_on=SOURCES_CHECKED) for p in REAL + BROOKLINE]
    hits = [e for e in entries if all(t in _norm(" ".join([e["name"], e["practice"], e["address"]])) for t in terms)]
    return hits[:limit]


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
