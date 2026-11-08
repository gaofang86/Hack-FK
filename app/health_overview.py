"""My health: a personal overview built only from the profile and user-reviewed reports.

Three parts, all fixed rules:
1. overview         - what FirstVisit holds about you (facts you entered or reviewed), no interpretation.
2. needs attention  - only (a) rows a report itself flagged, quoted verbatim with a question for a clinician,
                      (b) refills and follow-ups that are due or overdue, (c) the sourced age/sex screenings
                      and vaccines from health.py. No diagnosis, no inferred condition, no risk score.
3. plan direction   - expected care use this year, counted from the same facts, translated into what to
                      look for in a plan. Plan figures come only from a reviewed SBC; anything else is unknown,
                      never $0.

User-facing strings use the "中文 / English" pair convention that static/i18n.js splits.
"""
import re
from datetime import date

from .health import age, todos, better_choices
from .sbc import describe
from .scenarios import NEEDS, SOURCES as PLAN_SOURCES, CHECKED as PLAN_CHECKED

FLAG_NOTE = "标记照抄自报告，不是诊断 / Flag copied from the report, not a diagnosis"
SCOPE = ("只整理你填写或核对过的事实，不做诊断、不推断病情、不给风险评分。 / "
         "Only facts you entered or reviewed. No diagnosis, no inferred conditions, no risk scores.")
UNKNOWN = "未知，不按 0 计算 / Unknown, not $0"
# Follow-ups whose own words name a lab or test count toward expected lab use (the user's words, not inference).
LAB_WORDS = re.compile(r"\b(lab|labs|blood|bloodwork|test|tests|panel|draw)\b|抽血|化验|检验|检查", re.I)
# Which SBC row (app/sbc.py SERVICES) answers each expected need; labs and refills beyond generics are not
# in the standard SBC rows we read, so they stay unknown.
SBC_ROW = {"primary": "primary", "specialist": "specialist", "prescriptions": "generic", "mental": "mental",
           "urgent": "urgent", "er": "er"}


def _coverage(profile):
    ins = profile.get("insurance")
    if ins == "yes":
        return "insured"
    if ins == "no":
        return "choosing" if profile.get("wants_insurance") else "uninsured"
    return "not_sure"


RANGE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*[-\u2013]\s*(\d+(?:\.\d+)?)\s*$")
NUMBER = re.compile(r"^\s*[<>]?\s*(\d+(?:\.\d+)?)")


def _position(result, reference):
    """Where the reported value sits against the report's own printed range, for a visual marker only.
    The scale shows half a range beyond each end, so the range spans 25%-75%. None unless both are plain numbers."""
    rng, val = RANGE.match(reference or ""), NUMBER.match(result or "")
    if not rng or not val:
        return None
    low, high, value = float(rng[1]), float(rng[2]), float(val[1])
    if high <= low:
        return None
    pct = (value - (low - (high - low) / 2)) / (2 * (high - low)) * 100
    return {"low": rng[1], "high": rng[2], "pct": round(min(max(pct, 0), 100), 1)}


def report_digest(rows):
    """At-a-glance counts and the rows the report itself flagged. No interpretation or re-derived flags."""
    flagged = [r for r in rows if r.get("flag") in ("Low", "High")]
    return {"total": len(rows), "not_flagged": len(rows) - len(flagged),
            "low": sum(r["flag"] == "Low" for r in flagged), "high": sum(r["flag"] == "High" for r in flagged),
            "flagged": [{"name": r.get("name", ""), "result": r.get("result", ""), "reference": r.get("reference", ""),
                         "flag": r["flag"], "position": _position(r.get("result"), r.get("reference"))} for r in flagged],
            "note": FLAG_NOTE}


def _report_summary(report):
    rows = report.get("rows", [])
    digest = report_digest(rows)
    return {"id": report["id"], "label": report.get("label") or "Lab report",
            "reviewed_on": (report.get("source") or {}).get("reviewed_on", ""),
            "rows": len(rows), "flagged": len(digest["flagged"]), "digest": digest,
            "results": [{k: r.get(k, "") for k in ("name", "result", "reference", "flag")} for r in rows]}


def flagged_rows(reports):
    """Rows the report itself flagged, quoted exactly as reviewed. Never re-derived from the numbers."""
    out = []
    for rep in reports:
        for row in rep.get("rows", []):
            flag = row.get("flag")
            if flag not in ("Low", "High"):
                continue
            ref = row.get("reference") or "not given"
            out.append({"kind": "report_flag", "report_id": rep["id"], "report": rep.get("label") or "Lab report",
                        "reviewed_on": (rep.get("source") or {}).get("reviewed_on", ""),
                        "name": row.get("name", ""), "result": row.get("result", ""),
                        "reference": row.get("reference", ""), "flag": flag, "note": FLAG_NOTE,
                        "ask": (f"My report marks {row.get('name', '')} {row.get('result', '')} as “{flag}” "
                                f"(reported range: {ref}). What does this mean for me, and do I need to do anything next?")})
    return out


def attention(profile, reports, today=None):
    items = todos(profile, today)
    return {"report_flags": flagged_rows(reports),
            "due": [t for t in items if t["kind"] in ("refill", "follow_up") and not t.get("done_on")],
            "preventive": [t for t in items if t["kind"] in ("screening", "vaccine") and not t.get("done_on")],
            "done": [t for t in items if t.get("done_on")],
            "needs_birth_year": age(profile, today) is None}


def expected_use(profile, reports):
    """Count expected care this year from facts on file. Each count says what it was counted from."""
    follow = profile.get("follow_ups") or []
    lab_follow = [f["what"] for f in follow if LAB_WORDS.search(f["what"])]
    visit_follow = [f["what"] for f in follow if f["what"] not in lab_follow]
    flags = flagged_rows(reports)
    use = []
    primary_basis = ["1 次年度体检（预防性） / 1 yearly checkup (preventive)"]
    primary_basis += [f"复诊 / Follow-up: {w}" for w in visit_follow]
    if flags:
        primary_basis.append(f"带着报告标记的 {len(flags)} 项去问医生 / A visit to ask about {len(flags)} flagged report row(s)")
    use.append({"need": "primary", "label": NEEDS["primary"], "count": len(primary_basis), "basis": primary_basis})
    if lab_follow:
        use.append({"need": "labs", "label": NEEDS["labs"], "count": len(lab_follow),
                    "basis": [f"后续事项 / Follow-up: {w}" for w in lab_follow]})
    meds = profile.get("medications") or []
    if meds:
        use.append({"need": "prescriptions", "label": NEEDS["prescriptions"], "count": 12 * len(meds),
                    "basis": [f"每月续药 / Monthly refills: {m}" for m in meds]})
    conds = profile.get("conditions") or []
    if conds:
        use.append({"need": "specialist", "label": NEEDS["specialist"], "count": 2,
                    "basis": [f"你记录的长期情况 / Ongoing item you entered: {c}" for c in conds]})
    return use


def _look_for(use, coverage):
    needs = {u["need"]: u["count"] for u in use}
    tips = [{"title": "预防性服务是否在网内免费 / Is preventive care free in-network?",
             "why": "多数计划在网内免费提供年度体检、筛查和疫苗。 / Most plans cover checkups, screenings and vaccines at no cost in-network.",
             "source": dict(PLAN_SOURCES["preventive"], checked_on=PLAN_CHECKED)}]
    if needs.get("primary", 0) >= 3:
        tips.append({"title": "看初级保健的 copay，以及是否先扣 deductible / Primary-care copay, and whether the deductible applies first",
                     "why": f"你今年可能看 {needs['primary']} 次初级保健。 / You may have about {needs['primary']} primary-care visits this year."})
    if "labs" in needs:
        tips.append({"title": "化验怎么报销、哪些化验室在网内 / How lab tests are covered and which labs are in-network",
                     "why": "化验常按 coinsurance 或先扣 deductible，标准 SBC 里不一定写明。 / Labs often use coinsurance or the deductible and may not be listed on the standard SBC."})
    if "prescriptions" in needs:
        tips.append({"title": "药品目录和仿制药 copay / The drug list (formulary) and generic copay",
                     "why": f"约 {needs['prescriptions']} 次续药：确认你的药在目录里。 / About {needs['prescriptions']} refills: check your medicines are on the formulary."})
    if "specialist" in needs:
        tips.append({"title": "专科 copay，以及是否需要转诊 / Specialist copay, and whether you need a referral",
                     "why": "长期情况常需要专科随访。 / Ongoing items you entered may involve specialist visits."})
    if set(needs) == {"primary"} and needs["primary"] <= 2:
        tips.append({"title": "用得少时，先比年保费和自付上限 / If you expect little care, compare yearly premium and out-of-pocket max first",
                     "why": "按你目前的记录，今年预计就医较少。 / From what’s on file, you expect little care this year.",
                     "source": dict(PLAN_SOURCES["total_costs"], checked_on=PLAN_CHECKED)})
    tips.append({"title": "自付上限 / The out-of-pocket maximum",
                 "why": "这是一年内你最多要付的医疗费用（不含保费）。 / The most you pay for covered care in a year, not counting premiums.",
                 "source": dict(PLAN_SOURCES["total_costs"], checked_on=PLAN_CHECKED)})
    return tips


def plan_direction(profile, reports):
    use = expected_use(profile, reports)
    coverage = _coverage(profile)
    benefits = profile.get("plan_benefits") if coverage == "insured" else None
    current = []
    if benefits:
        services = benefits.get("services") or {}
        for u in use:
            row = SBC_ROW.get(u["need"])
            cost = services.get(row) if row else None
            text = describe(cost) if cost else "Not found"
            known = text != "Not found"
            current.append({"need": u["need"], "label": u["label"], "value": text if known else UNKNOWN,
                            "from": ((benefits.get("source") or {}).get("file") or "SBC") if known else ""})
    return {"coverage": coverage, "plan": (profile.get("plan") or {}).get("name", "") if coverage == "insured" else "",
            "expected_use": use, "needs": {u["need"]: u["count"] for u in use},
            "look_for": _look_for(use, coverage), "current_plan": current,
            "has_sbc": bool(benefits), "choices": better_choices(profile),
            "note": ("这些次数只来自你的记录，可在比较时修改；不是医疗建议。 / "
                     "Counts come only from what’s on file and can be changed when you compare. Not medical advice.")}


def overview(profile, reports, today=None):
    today = today or date.today()
    reports = sorted(reports, key=lambda r: (r.get("source") or {}).get("reviewed_on", ""), reverse=True)
    visits = profile.get("visits") or []
    snapshot = {"age": age(profile, today), "sex": profile.get("sex", ""), "language": profile.get("language") or "English",
                "coverage": _coverage(profile), "plan": (profile.get("plan") or {}).get("name", ""),
                "conditions": profile.get("conditions") or [], "medications": profile.get("medications") or [],
                "allergies": profile.get("allergies") or [], "follow_ups": profile.get("follow_ups") or [],
                "reports": [_report_summary(r) for r in reports],
                "last_visit": visits[0] if visits else None, "visits": len(visits),
                "visit_history": [{k: v.get(k) for k in ("date", "reason", "place", "notes", "added")} for v in visits]}
    return {"overview": snapshot, "attention": attention(profile, reports, today),
            "plan_direction": plan_direction(profile, reports), "scope": SCOPE}
