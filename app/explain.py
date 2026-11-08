"""Rules decide, a local model explains, a check verifies.

The fact sheet is built deterministically. The local model may only rephrase it;
any number, dollar amount or forbidden claim not on the sheet rejects the output
and the deterministic template is shown instead. Health text is never sent.
"""
import re

from .journeys import coverage_situation

FORBIDDEN = re.compile(r"diagnos|you (have|probably have) (a|an) |in[- ]network (is )?confirmed|guarantee|free of charge|"
                       r"out[- ]of[- ]pocket|exceed|not covered|(will|likely|probably) (need to )?pay|you('ll| will) owe|covered in full|"
                       r"not active|inactive|no (added )?benefits|does not include|"
                       r"有效状态|plan is active|已经为您提供|基本的医疗保护|诊断|一定在网络内|保证|免费|超出|不在.*覆盖|覆盖范围|报销|需要自付|自己付|全额|未激活|没有.*福利|不包含", re.I)
UNKNOWN_WORDS = re.compile(r"unknown|not known|don.t know|do not know|not sure yet|未知|无法确定|暂时无法|还不知道|不确定|尚未确定|还没确定|不清楚", re.I)

NEXT_ZH = {'insured': '打保险卡背面的会员服务电话，问这位医生是否在网络内、看一次的 copay 是多少',
           'uninsured': '问诊所新病人看一次的自费价格，以及有没有经济援助',
           'choosing': '用每个计划的 SBC，比较一年的保费加上预计看病的费用',
           'unknown': '先回答你有没有保险'}


def coverage_facts(case, profile):
    profile = profile or {}
    plan = (profile.get('plan') or {}).get('name') or ''
    return {
        'situation': coverage_situation(case, profile),
        'plan_name': plan,
        'benefits_added': bool(profile.get('plan_benefits')),
        'visit_cost': 'known from reviewed benefits' if profile.get('plan_benefits') else 'unknown (not $0)',
        'next_step': {'insured': 'call the member services number on the insurance card and ask whether the clinician is in network and what the visit copay is',
                      'uninsured': 'ask clinics for the self-pay price of a new-patient visit and about financial assistance',
                      'choosing': 'compare plans by yearly premium plus expected visit costs, using each plan SBC',
                      'unknown': 'answer whether you have insurance first'}[coverage_situation(case, profile)],
    }


TEMPLATES = {
    'en': {'insured': 'You have insurance{plan}. {cost} Next: {step}.',
           'uninsured': 'You do not have insurance right now, so prices come from clinics. Visit cost: {cost_raw}. Next: {step}.',
           'choosing': 'You are choosing a plan. Next: {step}.',
           'unknown': 'We do not know yet whether you have insurance. Next: {step}.'},
    'zh': {'insured': '你有保险{plan}。{cost}下一步：{step}。',
           'uninsured': '你目前没有保险，价格要问诊所。看病费用：{cost_raw}。下一步：{step}。',
           'choosing': '你在选择保险计划。下一步：{step}。',
           'unknown': '还不知道你有没有保险。下一步：{step}。'},
}


def model_facts(facts):
    sit = {'insured': 'The person has health insurance.', 'uninsured': 'The person has no health insurance right now.',
           'choosing': 'The person is choosing a health plan.', 'unknown': 'We do not know yet whether the person has insurance.'}[facts['situation']]
    lines = [sit]
    if facts['plan_name']:
        lines.append(f"Plan name: {facts['plan_name']}.")
    if facts['situation'] in ('insured', 'uninsured'):
        lines.append('The visit cost is known from benefits the person reviewed.' if facts['benefits_added'] else
                     'The visit cost is not known yet, because the app has not read the plan documents. This says nothing about what the plan covers.')
    lines.append('Next step: ' + facts['next_step'] + '.')
    return '\n'.join(lines)


def template(facts, lang):
    t = TEMPLATES['zh' if lang == 'zh' else 'en'][facts['situation']]
    plan = (f'（{facts["plan_name"]}）' if lang == 'zh' else f' ({facts["plan_name"]})') if facts['plan_name'] else ''
    if lang == 'zh':
        cost = '已按你核对过的福利计算费用。' if facts['benefits_added'] else '还没有你的福利信息，看病费用暂时未知（不是 0）。'
    else:
        cost = 'Costs use the benefits you reviewed.' if facts['benefits_added'] else 'Your benefits are not added yet, so the visit cost is unknown (not $0).'
    step = NEXT_ZH[facts['situation']] if lang == 'zh' else facts['next_step']
    cost_raw = ('未知（不是 0）' if facts['visit_cost'].startswith('unknown') else '按已核对的福利') if lang == 'zh' else facts['visit_cost']
    return t.format(plan=plan, cost=cost, cost_raw=cost_raw, step=step)


def check(text, facts):
    """Reject output that adds numbers or claims that are not on the fact sheet."""
    if not text or len(text) > 900 or FORBIDDEN.search(text):
        return False
    allowed = set(re.findall(r"\d+", str(facts)))
    if not set(re.findall(r"\d+", text)) <= allowed:
        return False
    # If the sheet says the cost is unknown, the explanation must say so too.
    if facts.get('visit_cost', '').startswith('unknown') and facts.get('situation') in ('insured', 'uninsured') and not UNKNOWN_WORDS.search(text):
        return False
    return True


def explain_coverage(model, case, profile, lang):
    facts = coverage_facts(case, profile)
    fallback = template(facts, lang)
    language = 'Chinese' if lang == 'zh' else 'English'
    system = (f"You explain US health insurance to a newcomer in {language}. Use ONLY the facts given. Do not add numbers, "
              "prices, plan rules or network claims. Do not diagnose. If visit_cost is unknown, say plainly that the cost is "
              "not known yet and do NOT guess whether they will pay, owe money, or be covered. 2-3 short, warm sentences, "
              "then one concrete next step.")
    prompt = "Facts (fixed, do not change):\n" + model_facts(facts)
    status = model.status()
    if status.get('available'):
        try:
            text = model.generate(prompt, system, 220)
            if check(text, facts):
                return {'text': text, 'source': f'local model ({model.model_name}) · checked against the fact sheet', 'facts': facts}
            reason = 'model output added facts or failed the check'
        except Exception as e:  # any model failure falls back to rules
            reason = str(e)
    else:
        reason = status.get('reason') or 'local model unavailable'
    return {'text': fallback, 'source': 'rules template (local model not used)', 'fallback_reason': reason, 'facts': facts}


# ---- comparison results -------------------------------------------------
RANK_FORBIDDEN = re.compile(r"\bbest\b|cheapest|top[- ]rated|highest quality|\b(is|are) in[- ]network|accepts? your (insurance|plan)|"
                            r"accepting new patients|appointment (is )?available|you should (go|choose)|"
                            r"最好|最便宜|质量最高|在网络内|接受你的保险|有号|可以预约|你应该选|"
                            r"prioriti[sz]ed|ranked (first|higher)|listed first because|is first because|because (it|this) (was|is)|"
                            r"排在前|优先列出|排第一是因为|明确选择|选择了", re.I)
POSITIVE_CONFIRMED = re.compile(r"(?<!not )(?<!un)\bconfirmed\b|(?<![未尚没])已确认|确认提供", re.I)


def comparison_facts(rows, person, limit=3):
    out = []
    for i, row in enumerate(rows[:limit], 1):
        amount = row["cost"]["amount"]
        out.append({
            "rank": i,
            "name": row["provider"]["name"],
            "visit_cost": f"${amount:g} ({row['cost'].get('status') or 'estimate'})" if amount is not None else "unknown (not $0)",
            "comparable": bool(row["supported"]) and amount is not None and not row["unavailable"],
            "office_said_unavailable": bool(row["unavailable"]),
            "distance_miles": row["miles"],
            "why_listed": list(row["reasons"])[:4],
            "open_questions": len(row.get("confirmation") or []),
        })
    en, zh = why_first(rows, person.get("priority") or "cost")
    return {"priority": person.get("priority") or "cost", "why_first": {"en": en, "zh": zh}, "options": out}


def why_first(rows, priority):
    """Compare #1 and #2 on the same ordered inputs ranked() sorts by; say 'tied' honestly."""
    if len(rows) < 2:
        return ("Only one option so far.", "目前只有一个候选。")
    a, b = rows[0], rows[1]
    comparable = lambda r: bool(r["supported"]) and r["cost"]["amount"] is not None and not r["unavailable"]
    if a["unavailable"] != b["unavailable"]:
        return ("The second option is listed lower because the office said it is unavailable.", "第二家排在后面，因为诊所答复暂时不可约。")
    if comparable(a) != comparable(b):
        return ("The first option has supported cost evidence; the second does not yet.", "第一家有可比较的费用依据，第二家还没有。")
    if a.get("over_budget") != b.get("over_budget"):
        return ("The second option is above your visit budget.", "第二家超出了你的看病预算。")
    metric = {"cost": ("cost", "费用"), "distance": ("distance", "距离"), "rating": ("sourced rating", "有来源的评价")}.get(priority)
    va = {"cost": a["cost"]["amount"], "distance": a["miles"], "rating": (a["provider"].get("rating") or {}).get("value")}.get(priority)
    vb = {"cost": b["cost"]["amount"], "distance": b["miles"], "rating": (b["provider"].get("rating") or {}).get("value")}.get(priority)
    if metric and va is not None and vb is not None and va != vb:
        return (f"It comes first on your chosen priority: {metric[0]}.", f"按你选的优先项（{metric[1]}）它排在前面。")
    return ("These options have the same evidence so far, so they are listed by name. The order is not a recommendation.",
            "这几家目前的证据相同，所以按名称排列，排序不代表推荐。")


def comparison_model_facts(facts):
    lines = [f"Sorting priority chosen by the person: {facts['priority']}. Options without a supported price or marked unavailable are sorted after comparable ones."]
    for o in facts["options"]:
        lines.append(f"Option {o['rank']}: {o['name']}. Visit cost: {o['visit_cost']}. "
                     + ("Comparable on cost. " if o["comparable"] else "Not yet comparable on cost; needs confirmation. ")
                     + ("The office said it is unavailable; backup only. " if o["office_said_unavailable"] else "")
                     + (f"Straight-line distance: {o['distance_miles']} miles. " if o["distance_miles"] is not None else "Distance not verified. ")
                     + "Listed because: " + "; ".join(o["why_listed"]) + ". "
                     + f"Questions still to confirm with this office: {o['open_questions']}.")
    return "\n".join(lines)


def comparison_template(facts, lang):
    opts = facts["options"]
    if not opts:
        return "还没有候选诊所。" if lang == "zh" else "There are no options to compare yet."
    unknown = [o for o in opts if not o["comparable"]]
    if lang == "zh":
        head = facts["why_first"]["zh"] + f"排在第 1 的是 {opts[0]['name']}，看病费用：{'未知（不是 0）' if opts[0]['visit_cost'].startswith('unknown') else opts[0]['visit_cost']}。"
        tail = f"有 {len(unknown)} 家的费用还不能比较，需要先向诊所确认。" if unknown else "这几家都有可比较的费用依据。"
        return head + tail + "排序只基于已有证据，不代表医生好坏，也不代表在你的保险网络内。"
    head = facts["why_first"]["en"] + f" First listed: {opts[0]['name']}, visit cost {opts[0]['visit_cost']}."
    tail = f" {len(unknown)} of these cannot be compared on cost yet and need confirmation with the office." if unknown else " All of these have supported cost evidence."
    return head + tail + " The order reflects available evidence only, not clinician quality or network status."


def check_comparison(text, facts):
    if not text or len(text) > 1200 or FORBIDDEN.search(text) or RANK_FORBIDDEN.search(text) or POSITIVE_CONFIRMED.search(text):
        return False
    if not set(re.findall(r"\d+(?:\.\d+)?", text)) <= set(re.findall(r"\d+(?:\.\d+)?", str(facts))):
        return False
    if any(o["visit_cost"].startswith("unknown") for o in facts["options"]) and not UNKNOWN_WORDS.search(text):
        return False
    return True


def explain_comparison(model, rows, person, lang):
    facts = comparison_facts(rows, person)
    fallback = comparison_template(facts, lang)
    if not facts["options"]:
        return {"text": fallback, "source": "rules template", "facts": facts}
    language = "Chinese" if lang == "zh" else "English"
    system = (f"You help a newcomer read a clinic shortlist, in {language}. The reason for the order is shown separately by the app: "
              "do NOT explain or guess why any option is listed first. In 2-3 short sentences, explain in plain words what is still "
              "unknown (cost, language support, appointments) and what to ask the office. Use ONLY the facts. Never say anything is "
              "confirmed, best, cheapest, in network or available. Add no numbers. If a cost is unknown, say it is not known yet.")
    prompt = "Facts (fixed, do not change):\n" + comparison_model_facts(facts)
    status = model.status()
    if status.get("available"):
        try:
            text = model.generate(prompt, system, 260)
            if check_comparison(text, facts):
                text = facts["why_first"]["zh" if lang == "zh" else "en"] + " " + text
                return {"text": text, "source": f"local model ({model.model_name}) · checked against the fact sheet", "facts": facts}
            reason = "model output added facts or failed the check"
        except Exception as e:
            reason = str(e)
    else:
        reason = status.get("reason") or "local model unavailable"
    return {"text": fallback, "source": "rules template (local model not used)", "fallback_reason": reason, "facts": facts}
