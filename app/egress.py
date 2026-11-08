"""The single door out of this machine.

Every outbound request in FirstVisit goes through Egress. It enforces, in order:
  1. Offline switch   - when on, nothing leaves (the local model still works).
  2. Host allowlist   - only the configured search services.
  3. DLP filter       - the whole payload, URLs included, is scanned for vault values:
                        your name, date of birth, member and group numbers, conditions,
                        medications, allergies, every symptom you described, and numbers
                        from bills you pasted. Each call declares which values it means to
                        send (ZIP, city, insurer name); anything else blocks the request.
  4. No redirects     - a request goes to the host that was checked, or nowhere.
  5. Leak Ledger      - the exact payload (secrets redacted) of every sent, blocked and
                        failed request. Failed requests may still have reached the host,
                        so the privacy proof counts them as transmitted.

scripts/audit_egress.py verifies no other module imports networking libraries.
"""
import ipaddress
import json
import re
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import unquote_plus, urlencode, urlparse

from . import textutil as tu

SECRET_KEYS = {"api_key", "apikey", "password", "token", "auth", "authorization", "secret", "x-api-key"}
_CHUNK = re.compile(r"[,.;:!?\n]+|\band\b|\bwith\b|\bbut\b", re.I)
_LONG_NUM = re.compile(r"\b[A-Z0-9-]{6,}\b", re.I)


class EgressBlocked(Exception):
    """Refused before anything left the machine."""


class EgressError(Exception):
    """The request was sent (or attempted) but failed."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


# ---------- DLP ----------

class Protected:
    """One vault value and how to recognise it in text."""

    def __init__(self, field, value, matcher):
        self.field, self.value, self._m = field, value, matcher

    def found_in(self, text):
        return self._m(text)


def _pattern_matcher(pattern):
    return (lambda t: bool(pattern.search(t))) if pattern else None


def _alnum(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _id_matcher(value):
    key = _alnum(value)
    if len(key) < 4:
        return None
    return lambda t: key in _alnum(t)


def _dob_matcher(dob):
    m = re.fullmatch(r"\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*", dob or "")
    if not m:
        return _pattern_matcher(tu.phrase_pattern(dob)) if dob else None
    y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
    forms = {f"{y}-{mo:02d}-{d:02d}", f"{mo:02d}/{d:02d}/{y}", f"{mo}/{d}/{y}",
             f"{mo:02d}-{d:02d}-{y}", f"{mo:02d}{d:02d}{y}", f"{y}{mo:02d}{d:02d}"}
    return lambda t: any(f in t for f in forms)


def symptom_phrases(text):
    """The pieces of a free-text description that would reveal it: the whole thing and each clause."""
    text = " ".join((text or "").split())
    out = [text] if len(text) >= 4 else []
    for part in _CHUNK.split(text):
        part = part.strip(" -'\"()")
        if len(part) >= 4 and part.lower() not in {"have", "been", "feel", "since", "days", "today"}:
            out.append(part)
    return out


def protected_values(data):
    """Every value in the vault that must not leave unless a request declares it."""
    if not data:
        return []
    profile = data.get("profile", {})
    out = []

    def add(field, value, matcher):
        if value and matcher:
            out.append(Protected(field, value, matcher))

    add("name", profile.get("full_name"), _pattern_matcher(tu.name_pattern(profile.get("full_name", ""))))
    add("date_of_birth", profile.get("date_of_birth"), _dob_matcher(profile.get("date_of_birth")))
    add("member_id", profile.get("member_id"), _id_matcher(profile.get("member_id")))
    add("group_number", profile.get("group_number"), _id_matcher(profile.get("group_number")))
    for field in ("conditions", "medications", "allergies"):
        for v in profile.get(field, []) or []:
            add(field, v, _pattern_matcher(tu.phrase_pattern(v)))
    for f in profile.get("follow_ups", []) or []:
        add("follow_ups", f.get("what"), _pattern_matcher(tu.phrase_pattern(f.get("what", ""))))
    for case in data.get("cases", {}).values():
        for phrase in symptom_phrases(case.get("description", "")):
            add("symptoms", phrase, _pattern_matcher(tu.phrase_pattern(phrase)))
        for label in case.get("symptom_terms", []):
            add("symptoms", label, _pattern_matcher(tu.phrase_pattern(label)))
    for bill in data.get("bills", {}).values():
        for num in bill.get("identifiers", []):
            add("bill_numbers", num, _id_matcher(num))
    return out


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)
    elif isinstance(obj, (int, float)):
        yield str(obj)


def payload_text(payload):
    """All strings in a payload, plus URL-decoded copies so '%20' or '+' can't hide a value."""
    raw = "\n".join(_strings(payload))
    decoded = raw
    copies = [raw]
    for _ in range(4):
        decoded = unquote_plus(decoded)
        copies.append(decoded)
    return "\n".join(copies)


def dlp_violations(payload, data, allowed_values=()):
    """Vault values present in payload that the caller did not declare. URLs are not exempt."""
    text = payload_text(payload)
    hits = []
    for pv in protected_values(data):
        if pv.found_in(text):
            hits.append(pv.field)
    return sorted(set(hits))


def redact(obj):
    if isinstance(obj, dict):
        return {k: ("[redacted]" if k.lower() in SECRET_KEYS else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


def _is_loopback(host):
    host = host or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, f"Redirect to {newurl} refused", headers, fp)


_OPENER = urllib.request.build_opener(_NoRedirect)
_LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


# ---------- the guard ----------

class Egress:
    def __init__(self, store, config):
        self.store = store
        self.config = config
        self.offline = False

    def _data(self):
        return self.store.data if self.store.unlocked else {}

    def _record(self, **entry):
        entry.setdefault("id", uuid.uuid4().hex[:12])
        entry.setdefault("ts", time.time())
        self.store.add_ledger(entry)
        return entry

    def _preflight(self, service, destination, purpose, payload, allowed_values, method, path):
        base = dict(service=service, destination=destination, method=method, path=path,
                    purpose=purpose, payload=redact(payload),
                    declared=[v for v in allowed_values if v],
                    bytes=len(json.dumps(payload, ensure_ascii=False).encode()))
        if self.offline:
            self._record(**base, status="blocked", reason="Offline mode is on")
            raise EgressBlocked("Offline mode is on")
        if destination not in self.config.allowed_hosts():
            self._record(**base, status="blocked", reason="Host is not on the allowlist")
            raise EgressBlocked(f"{destination} is not on the allowlist")
        leaks = dlp_violations(payload, self._data(), allowed_values)
        if leaks:
            self._record(**base, status="blocked", reason="DLP: would have sent " + ", ".join(leaks))
            raise EgressBlocked("Blocked before sending: the request contained your " + ", ".join(leaks))
        return base

    def http(self, method, url, *, service, purpose, headers=None, json_body=None,
             allowed_values=(), timeout=25):
        """Send an outbound JSON request through every check. Returns parsed JSON."""
        parsed = urlparse(url)
        if parsed.username or parsed.password or parsed.scheme not in ("http", "https") or (parsed.scheme != "https" and not _is_loopback(parsed.hostname)):
            raise EgressBlocked("External requests require HTTPS without URL credentials")
        payload = {"url": url, "body": json_body or {}, "headers": headers or {}}
        base = self._preflight(service, parsed.netloc.lower(), purpose, payload,
                               allowed_values, method, parsed.path)
        headers = dict(headers or {})
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode()
            headers.setdefault("Content-Type", "application/json")
        headers.setdefault("User-Agent", "FirstVisit/1.0")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        started = time.time()
        try:
            with _OPENER.open(req, timeout=timeout) as resp:
                body = resp.read(2000001)
                if len(body) > 2000000:
                    raise OSError("Search response exceeded the size limit")
                status = resp.status
        except urllib.error.HTTPError as e:
            detail = (e.read()[:300].decode(errors="replace") if e.fp else str(e.reason))
            self._record(**base, status="error", http_status=e.code, reason=detail,
                         latency_ms=int((time.time() - started) * 1000))
            raise EgressError(f"{service} returned HTTP {e.code}: {detail}", e.code)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            self._record(**base, status="error", reason=f"Network unavailable: {e}",
                         latency_ms=int((time.time() - started) * 1000))
            raise EgressError(f"Network unavailable: {e}")
        self._record(**base, status="sent", http_status=status,
                     latency_ms=int((time.time() - started) * 1000))
        return json.loads(body or b"{}")

    def local(self, method, url, *, json_body=None, timeout=120):
        """Calls to the on-device model. Loopback only; allowed while offline; not outbound."""
        parsed = urlparse(url)
        if parsed.username or parsed.password or parsed.scheme not in ("http", "https") or not _is_loopback(parsed.hostname):
            raise EgressBlocked("The model endpoint must be on this machine (localhost)")
        data = json.dumps(json_body).encode() if json_body is not None else None
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with _LOCAL_OPENER.open(req, timeout=timeout) as resp:
                body = resp.read(1000001)
                if len(body) > 1000000:
                    raise OSError("Local model response exceeded the size limit")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise EgressError(f"Local model unavailable: {e}")
        self.store.count_local_call()
        return json.loads(body or b"{}")
