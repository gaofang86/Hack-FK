"""Normalization helpers shared by the egress DLP filter and the local matcher.

Keeping one implementation means "what we refuse to send" and "what we look for
on a page" are judged the same way.
"""
import re

_WS = re.compile(r"\s+")
_DIGIT_RUN = re.compile(r"\+?\d[\d\s().\-]{5,}\d")

STREET_SUFFIXES = {
    "street": "st", "st": "st", "avenue": "ave", "ave": "ave", "av": "ave",
    "road": "rd", "rd": "rd", "drive": "dr", "dr": "dr", "lane": "ln", "ln": "ln",
    "boulevard": "blvd", "blvd": "blvd", "court": "ct", "ct": "ct", "place": "pl",
    "pl": "pl", "terrace": "ter", "ter": "ter", "way": "way", "circle": "cir", "cir": "cir",
}


def norm(text):
    return _WS.sub(" ", (text or "")).strip().lower()


def digits(text):
    return re.sub(r"\D", "", text or "")


def phone_key(phone):
    """Last 10 digits: the comparable core of a US number."""
    d = digits(phone)
    return d[-10:] if len(d) >= 10 else ""


def phone_keys_in(text):
    """Every phone-like number in the text, reduced to its last 10 digits."""
    keys = set()
    for m in _DIGIT_RUN.finditer(text or ""):
        k = phone_key(m.group(0))
        if k:
            keys.add(k)
    return keys


def phone_span(text, key):
    """(start, end) of the first phone-like run matching key, else None."""
    for m in _DIGIT_RUN.finditer(text or ""):
        if phone_key(m.group(0)) == key:
            return m.start(), m.end()
    return None


def address_pattern(address):
    """Regex for '<number> <street name>' with suffix variants, e.g. '12 Elm St' ~ '12 elm street'.

    Only the house number and the first street word are required, which is what
    makes an address identifying. Returns None when the address has no number.
    """
    tokens = norm(address).replace(",", " ").split()
    if len(tokens) < 2 or not re.fullmatch(r"\d+[a-z]?", tokens[0]):
        return None
    number, street = tokens[0], re.escape(tokens[1])
    suffixes = "|".join(sorted(STREET_SUFFIXES, key=len, reverse=True))
    return re.compile(rf"\b{re.escape(number)}\s+{street}\b(?:\s+(?:{suffixes})\b\.?)?", re.I)


def name_pattern(full_name):
    """Matches 'First Last', 'First M Last', 'First M. Last', 'First Middle Last', 'Last, First'."""
    parts = [p for p in re.split(r"\s+", (full_name or "").strip()) if p]
    if len(parts) < 2:
        return None
    first, last = re.escape(parts[0]), re.escape(parts[-1])
    alts = [r"[a-z]\.?"] + [re.escape(p) for p in parts[1:-1]]
    mid = rf"(?:(?:{'|'.join(alts)})\s+)?"
    return re.compile(rf"\b{first}\s+{mid}{last}\b|\b{last},\s*{first}\b", re.I)


def phrase_pattern(phrase):
    p = norm(phrase)
    if len(p) < 3:
        return None
    escaped = re.escape(p).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![\w@]){escaped}(?![\w@])", re.I)


def snippet(text, start, end, width=90):
    """Verbatim window around a match, whitespace collapsed."""
    a, b = max(0, start - width), min(len(text), end + width)
    # snap to whitespace so no value (a phone, an address) is ever cut in half
    for _ in range(30):
        if a <= 0 or text[a - 1].isspace():
            break
        a -= 1
    for _ in range(30):
        if b >= len(text) or text[b].isspace():
            break
        b += 1
    s = _WS.sub(" ", text[a:b]).strip()
    return ("…" if a > 0 else "") + s + ("…" if b < len(text) else "")
