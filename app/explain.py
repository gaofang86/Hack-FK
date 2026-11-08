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
                       r"有效状态|plan is active|诊断|一定在网络内|保证|免费|超出|不在.*覆盖|覆盖范围|报销|需要自付|自己付|全额|未激活|没有.*福利|不包含", re.I)
UNKNOWN_WORDS = re.compile(r"unknown|not known|don.t know|do not know|not sure yet|未知|还不知道|不确定|尚未确定|还没确定|不清楚", re.I)

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
