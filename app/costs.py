"""What a visit may cost you, from numbers you copied off your own card or plan summary.

FirstVisit ships no price data and never guesses a dollar amount. If you didn't
enter a copay for a kind of place, it tells you where to look instead.
"""


def _money(v):
    return f"${v:,.0f}" if isinstance(v, (int, float)) else None


def estimate(venue, profile):
    costs = profile.get("costs") or {}
    ded, coins, oop = profile.get("deductible"), profile.get("coinsurance_pct"), profile.get("oop_max")
    key = "er" if venue == "911" else venue
    copay = costs.get(key)
    lines = []
    if isinstance(copay, (int, float)):
        headline = f"{_money(copay)} copay" if copay else "No copay listed ($0)"
        lines.append(f"Your plan lists a {_money(copay)} copay for this kind of visit.")
    else:
        headline = "Copay not entered"
        lines.append("Look for this visit type on the front of your insurance card or in your plan's "
                     "Summary of Benefits and Coverage (SBC), then add it under My info.")
    if isinstance(ded, (int, float)) and ded:
        tail = f", then you pay {coins:g}% (coinsurance)" if isinstance(coins, (int, float)) else ""
        lines.append(f"Tests, X-rays or procedures may count toward your {_money(ded)} deductible{tail}.")
    if isinstance(oop, (int, float)) and oop:
        lines.append(f"The most you pay in a plan year for in-network care is {_money(oop)} (out-of-pocket maximum).")
    if venue in ("911",):
        lines.append("Ambulance rides are often billed separately from the ER visit.")
    if venue in ("urgent_care", "primary_care"):
        lines.append("Prices on this page assume the clinic is in your plan's network. Call to confirm before you go.")
    return {"venue": venue, "headline": headline, "copay": copay if isinstance(copay, (int, float)) else None,
            "lines": lines}
