"""Find real places near you with Exa and Tavily, without saying why you need them.

Queries are built from a fixed template per kind of place, your ZIP/city/state, and
(if you allow it) your insurer's name. Your symptoms, conditions, name and member ID
are never part of a query, and the egress DLP filter blocks the request if one slips in.
Results are read on this laptop: phone numbers, hours and insurer mentions are pulled
out with verbatim snippets and links so every claim can be checked.
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, urlunparse

TEXT_CHARS = 8000
TEMPLATES = {
    "urgent_care": ["urgent care clinic near {loc} hours walk-in{ins_accepts}",
                    "walk-in urgent care {loc}{ins}"],
    "er": ["hospital emergency department near {loc}"],
    "primary_care": ["primary care doctor accepting new patients near {loc}{ins}"],
    "telehealth": ["{insurer_or_generic} telehealth virtual visit for members"],
    "campus_health": ["student health center walk-in hours {loc}"],
}
VENUE_WORDS = {
    "urgent_care": ["urgent care", "walk-in"], "er": ["emergency"], "primary_care": ["primary care", "family medicine", "internal medicine"],
    "telehealth": ["telehealth", "virtual", "video visit"], "campus_health": ["student health", "university health", "campus"],
}
PHONE = re.compile(r"(?:\+?1[\s.-]?)?\(?\b(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})\b")
HOURS = re.compile(r"(open 24 hours|24/7|(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*[^.\n]{0,40}?\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?\s?(?:-|–|to)\s?\d{1,2}(?::\d{2})?\s?[ap]\.?m\.?)", re.I)


def location(profile):
    parts = [profile.get("city", "").strip(), profile.get("state", "").strip(), profile.get("zip", "").strip()]
    return " ".join(p for p in parts if p)


def plan_queries(venue, profile, providers):
    """The exact strings that will leave, shown to you before anything is sent."""
    loc = location(profile)
    if not loc and venue != "telehealth":
        raise ValueError("Add your city or ZIP under My info so FirstVisit can search near you")
    insurer = profile.get("insurer", "").strip() if profile.get("share_insurer") else ""
    fill = {"loc": loc, "ins": f" {insurer}" if insurer else "",
            "ins_accepts": f" accepts {insurer}" if insurer else "",
            "insurer_or_generic": insurer or "health insurance"}
    allowed = [v for v in (profile.get("city"), profile.get("state"), profile.get("zip"), insurer) if v]
    fields = ["city", "state", "ZIP"] + (["insurer name"] if insurer else [])
    queries = []
    provs = sorted(providers)
    if not provs:
        return []
    for i, tpl in enumerate(TEMPLATES.get(venue, [])):
        q = " ".join(tpl.format(**fill).split())
        for p in provs if len(TEMPLATES[venue]) == 1 else [provs[i % len(provs)]]:
            queries.append({"q": q, "provider": p, "allowed_values": allowed, "fields": fields})
    return queries


def canonical(url):
    p = urlparse(url)
    return urlunparse((p.scheme.lower(), p.netloc.lower().removeprefix("www."), p.path.rstrip("/") or "/", "", "", ""))


def _snippet(text, start, end, width=80):
    a, b = max(0, start - width), min(len(text), end + width)
    s = " ".join(text[a:b].split())
    return ("…" if a > 0 else "") + s + ("…" if b < len(text) else "")


def read_place(page, venue, profile):
    """Pull checkable facts out of a page, each with the verbatim text it came from."""
    text = page.get("text") or ""
    facts, score = [], 0
    m = PHONE.search(text)
    if m:
        facts.append({"kind": "phone", "value": f"({m.group(1)}) {m.group(2)}-{m.group(3)}",
                      "snippet": _snippet(text, m.start(), m.end())})
        score += 1
    h = HOURS.search(text)
    if h:
        facts.append({"kind": "hours", "value": " ".join(h.group(0).split()), "snippet": _snippet(text, h.start(), h.end())})
        score += 1
    insurer = profile.get("insurer", "").strip()
    if insurer:
        core = re.escape(insurer.split(" of ")[0])
        im = re.search(core, text, re.I)
        if im:
            facts.append({"kind": "insurance", "value": f"Page mentions {im.group(0)}",
                          "snippet": _snippet(text, im.start(), im.end())})
            score += 3
    for key, w in (("zip", 2), ("city", 1)):
        v = profile.get(key, "").strip()
        if v:
            lm = re.search(re.escape(v), text, re.I)
            if lm:
                score += w
                if key == "zip" or not any(f["kind"] == "area" for f in facts):
                    facts = [f for f in facts if f["kind"] != "area"]
                    facts.append({"kind": "area", "value": f"Mentions {lm.group(0)}",
                                  "snippet": _snippet(text, lm.start(), lm.end())})
    title = (page.get("title") or "").lower()
    if any(w in title or w in text[:600].lower() for w in VENUE_WORDS.get(venue, [])):
        score += 1
    return {"url": page["url"], "domain": urlparse(page["url"]).netloc.removeprefix("www."),
            "title": page.get("title") or page["url"], "facts": facts, "score": score,
            "sources": page.get("sources", []), "excerpt": " ".join(text[:240].split())}


class Places:
    def __init__(self, egress, config):
        self.egress, self.cfg = egress, config

    def providers(self):
        return {name for name, ok in (("exa", self.cfg.exa_key), ("tavily", self.cfg.tavily_key)) if ok}

    def exa(self, query):
        res = self.egress.http(
            "POST", f"{self.cfg.exa_base}/search", service="Exa", purpose="Find places near you",
            headers={"x-api-key": self.cfg.exa_key},
            json_body={"query": query["q"], "type": "auto", "numResults": 8,
                       "contents": {"text": {"maxCharacters": TEXT_CHARS}}},
            allowed_values=query["allowed_values"])
        return [{"url": r.get("url", ""), "title": r.get("title") or "", "text": r.get("text") or "", "source": "exa"}
                for r in res.get("results", []) if r.get("url")]

    def tavily(self, query):
        res = self.egress.http(
            "POST", f"{self.cfg.tavily_base}/search", service="Tavily", purpose="Find places near you",
            headers={"Authorization": f"Bearer {self.cfg.tavily_key}"},
            json_body={"query": query["q"], "max_results": 8, "search_depth": "advanced",
                       "include_raw_content": True},
            allowed_values=query["allowed_values"])
        return [{"url": r.get("url", ""), "title": r.get("title") or "",
                 "text": (r.get("raw_content") or r.get("content") or "")[:TEXT_CHARS], "source": "tavily"}
                for r in res.get("results", []) if r.get("url")]

    def search(self, venue, profile):
        queries = plan_queries(venue, profile, self.providers())
        if not queries:
            raise ValueError("Add EXA_API_KEY or TAVILY_API_KEY to search for places")
        started = time.time()
        errors, merged = [], {}

        def one(q):
            t = time.time()
            try:
                items = self.exa(q) if q["provider"] == "exa" else self.tavily(q)
                return q, items, None, int((time.time() - t) * 1000)
            except Exception as e:     # the guard already recorded it
                return q, [], str(e), int((time.time() - t) * 1000)

        timing = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            for q, items, err, ms in pool.map(one, queries):
                timing.append({"provider": q["provider"], "q": q["q"], "ms": ms, "results": len(items), "error": err})
                if err:
                    errors.append(err)
                for it in items:
                    key = canonical(it["url"])
                    cur = merged.get(key)
                    if not cur:
                        merged[key] = dict(it, sources=[it["source"]])
                    else:
                        if len(it["text"]) > len(cur["text"]):
                            cur["text"] = it["text"]
                        if it["source"] not in cur["sources"]:
                            cur["sources"].append(it["source"])
        if errors and not merged:
            raise ValueError(errors[0])
        places = sorted((read_place(p, venue, profile) for p in merged.values()), key=lambda r: -r["score"])
        return {"venue": venue, "queries": [{"q": q["q"], "provider": q["provider"]} for q in queries],
                "places": places[:10], "timing": timing, "errors": errors,
                "duration_ms": int((time.time() - started) * 1000), "at": time.time()}
