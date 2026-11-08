"""One answer card per entry point, shaped by the person's own situation ("Me").

RESTRUCTURE.md §2–§6. Fixed rules, sourced, no model. Text is (zh, en) pairs; `view()`
returns one card per interface language. Coverage is a shared parameter: it is read from
the saved profile only, never guessed from goal wording, and `not_sure` is never shown as
confirmed. Unknown costs are never $0.

Entry points (kind ids kept for saved-task compatibility):
  first_visit -> A. I'm new here — set me up
  concern     -> B. Something's wrong (P2: still the existing flow)
  follow_up   -> C. A clinician told me to… (P3: still the existing flow)
  insurance   -> D. Figure out my insurance
"""
import re

from .catalog import REAL, BROOKLINE, SOURCES_CHECKED
from .benefits import clean_plan
from .sbc import describe
from .scenarios import SOURCES as SCENARIO_SOURCES, compare_plans
from .student_plan import NUSHP

COVERAGES = ('insured', 'uninsured', 'choosing', 'not_sure')
LANGUAGES = ('English', 'Chinese', 'Spanish')
CARD_KINDS = ('first_visit', 'insurance')  # P1; concern / follow_up keep the existing task page
_NUSHP = re.compile(r'nushp|northeastern', re.I)


def T(zh, en):
    return (zh, en)


def _src(key):
    return dict(SCENARIO_SOURCES[key], checked_on='2026-11-07')


# ---- Me: the shared parameters, asked once -------------------------------------------------

def me(profile):
    profile = profile or {}
    ins = profile.get('insurance')
    if ins == 'yes':
        coverage = 'insured'
    elif ins == 'no':
        coverage = 'choosing' if profile.get('wants_insurance') else 'uninsured'
    else:
        coverage = 'not_sure'
    return dict(coverage=coverage, plan=(profile.get('plan') or {}).get('name', '') if coverage == 'insured' else '',
                zip=profile.get('zip', '') or '', language=profile.get('language') or 'English',
                sbc=bool(profile.get('plan_benefits')) and coverage == 'insured')


def apply_me(profile, raw):
    """Update only the shared parameters. Everything else in the profile is untouched."""
    coverage = raw.get('coverage')
    if coverage not in COVERAGES:
        raise ValueError('Choose insured, uninsured, choosing a plan, or not sure')
    zip_code = str(raw.get('zip') or '').strip()
    if zip_code and not re.fullmatch(r'\d{5}', zip_code):
        raise ValueError('Use a 5-digit ZIP, or leave it blank')
    language = raw.get('language') or profile.get('language') or 'English'
    if language not in LANGUAGES:
        raise ValueError('Choose a supported language')
    profile['insurance'] = {'insured': 'yes', 'uninsured': 'no', 'choosing': 'no'}.get(coverage, '')
    profile['wants_insurance'] = coverage == 'choosing'
    profile['zip'] = zip_code
    profile['language'] = language
    if coverage == 'insured':
        name = str(raw.get('plan') or '').strip()[:120]
        current = profile.get('plan') or {}
        if not name:
            profile['plan'] = None
        elif current.get('name') != name:
            profile['plan'] = clean_plan({'name': name})
        benefits = profile.get('plan_benefits')
        if benefits and benefits.get('name') != name:
            profile.pop('plan_benefits', None)
    else:
        profile['plan'] = None
        profile.pop('plan_benefits', None)
    return me(profile)


# ---- Directory picks: sourced entries only, no invented distance ---------------------------

def _clinic(p):
    return {k: p.get(k, '') for k in ('id', 'name', 'kind', 'address', 'phone', 'url', 'booking_url', 'source_note')} | {'checked_on': SOURCES_CHECKED}


def _pick(zip_code, community=False, limit=2):
    pool = [p for p in REAL + BROOKLINE if 'primary_care' in p.get('services', [])]
    if community:
        pool = [p for p in pool if p.get('kind') == 'Community health center']
    near = [p for p in pool if zip_code and p.get('address', '').endswith(zip_code)]
    rest = [p for p in pool if p not in near and p.get('city') == 'Boston']
    return [_clinic(p) for p in (near + rest)[:limit]], bool(near)


def _where(zip_code, matched):
    return T(f'在 {zip_code} 附近', f'near {zip_code}') if matched else T('在 Boston', 'in Boston')


# ---- A. I'm new here — set me up ------------------------------------------------------------

SETTLE_STAGES = [T('你的保险', 'Your coverage'), T('选一个常规医生', 'Pick a regular doctor'),
                 T('联系预约', 'Call and book'), T('第一次就诊后', 'After the first visit')]


def _nushp(m):
    return m['coverage'] == 'insured' and bool(_NUSHP.search(m['plan']))


def _primary_cost(m, profile):
    if m['sbc']:
        row = ((profile.get('plan_benefits') or {}).get('services') or {}).get('primary', {})
        return T(f'常规医生就诊：{describe(row)}（来自你的 SBC）', f'Regular-doctor visit: {describe(row)} (from your SBC)')
    if _nushp(m):
        ref = NUSHP['reference_copays']
        return T(f'参考：去年公布的网络内诊所 ${ref["default_in_network"]}（Fenway ${ref["fenway"]}），2025–26 或未注明年份，今年需确认',
                 f'Reference: last published ${ref["default_in_network"]} at in-network offices (${ref["fenway"]} at Fenway), 2025–26 or undated — confirm for this year')
    return T('未知，不按 0 计算：加上你的 SBC 或问保险公司', 'Unknown, not $0: add your plan’s SBC or ask your insurer')


def settle(m, profile):
    cov, plan = m['coverage'], m['plan'] or None
    if cov in ('not_sure', 'choosing'):
        not_sure = cov == 'not_sure'
        return dict(
            stages=SETTLE_STAGES, stage=0,
            headline=T('找医生之前，先弄清你是不是已经有保险。', 'Before picking a doctor, find out whether you’re already covered.') if not_sure
            else T('先选好保险计划：能去哪个医生取决于它的网络。', 'Pick a plan first: which regular doctor you can use depends on its network.'),
            why=[dict(text=T('很多学校会自动给学生上健康计划；有没有保险决定了你该问医生什么、付多少。',
                              'Many schools enroll students automatically. Your coverage decides what to ask a clinic and what you pay.'),
                      source=_src('neu_plan'))],
            cost=[T('未知，不按 0 计算：先确定保险', 'Unknown, not $0: settle coverage first')],
            do_now=dict(text=T('去「弄懂我的保险」，答完会自动回到这里。', 'Go to “Figure out my insurance”; your answer carries back here.'), script=''),
            unknown=[T('你是否已经被学校计划覆盖：查学生账户或计划网站', 'Whether your school plan already covers you: check your student account or the plan site')],
            then=T('确定保险后，选一个常规医生', 'Once coverage is settled: pick a regular doctor'),
            clinics=[], actions=[dict(id='go-insurance', label=T('弄懂我的保险', 'Figure out my insurance'), primary=True)])
    insured = cov == 'insured'
    clinics, matched = _pick(m['zip'], community=not insured)
    first, where = clinics[0], _where(m['zip'], matched)
    if insured:
        headline = T(f'用{plan or "你的保险"}建立常规医生：先从{where[0]}的 {first["name"]} 开始。',
                     f'Use {plan or "your plan"} to set up a regular doctor: start with {first["name"]} {where[1]}.')
        script = (f'Hi, I’m a new patient looking for a primary care doctor. Are you accepting new patients? '
                  f'Do you take {plan or "my insurance plan"}? I can give you my member ID.')
        gloss = T('意思：我是新病人，想找 primary care 医生。现在收新病人吗？接受我的保险吗？', 'Ask whether they take new patients and your exact plan.')
        cost = [_primary_cost(m, profile),
                T('每年体检在网络内常常是 0 元（预防性服务），请诊所按 preventive 开账', 'A yearly checkup is often $0 in network as preventive care; ask the office to bill it as preventive')]
        why = [dict(text=T('网络内的常规医生通常最便宜，也是之后看专科、续药的入口。',
                           'An in-network regular doctor is usually the cheapest and is your way in to specialists and refills.'), source=_src('total_costs')),
               dict(text=T('诊所来自官方页面；新病人名额、网络和价格未确认。', 'Clinics come from official pages; new-patient openings, network and price are unconfirmed.'), source=None)]
        unknown = [T('这位医生、这个地址是否在你具体计划的网络内：问卡背面的会员电话', 'Whether this clinician at this address is in your exact plan’s network: ask the member number on your card'),
                   T('现在收不收新病人：问诊所', 'Whether they take new patients now: ask the office')]
        if not m['sbc']:
            unknown.append(T('今年看一次自付多少：上传 SBC 或问保险公司', 'What a visit costs you this year: add your SBC or ask your insurer'))
    else:
        headline = T(f'先从社区健康中心开始，例如 {first["name"]}：联邦资助的健康中心按收入收费。',
                     f'Start with a community health center such as {first["name"]}: federally funded centers charge by income.')
        script = ('Hi, I don’t have insurance and I’m looking for a primary care doctor. What is your self-pay price '
                  'for a new-patient visit? Do you offer a sliding fee or financial assistance?')
        gloss = T('意思：我没有保险，想找 primary care 医生。新病人自费多少？有没有按收入减免？', 'Ask for the self-pay price and a sliding fee.')
        cost = [T('自费价格未知，不按 0 计算：请诊所报价', 'Self-pay price unknown, not $0: ask the clinic to quote it'),
                T('社区健康中心按收入分档收费，有没有保险都可以去', 'Community health centers use a sliding fee by income, with or without insurance')]
        why = [dict(text=T('联邦资助的社区健康中心按收入收费。', 'Federally funded health centers charge on a sliding scale by income.'), source=_src('hrsa')),
               dict(text=T('预约前可以要求书面的 Good Faith Estimate。', 'You can ask for a written Good Faith Estimate before a scheduled visit.'), source=_src('gfe'))]
        unknown = [T('具体自费价格和减免条件：问诊所', 'The exact self-pay price and sliding-fee rules: ask the office'),
                   T('你是否其实已经有学校保险：查学生账户', 'Whether you already have school coverage: check your student account')]
    return dict(stages=SETTLE_STAGES, stage=1, headline=headline, why=why, cost=cost,
                do_now=dict(text=T(f'打给 {first["name"]}' + (f'（{first["phone"]}）' if first['phone'] else ''),
                                   f'Call {first["name"]}' + (f' ({first["phone"]})' if first['phone'] else '')),
                            script=script, gloss=gloss),
                unknown=unknown, then=T('预约后：记录预约结果，准备第一次就诊', 'After booking: record the appointment and prepare for the first visit'),
                clinics=clinics,
                actions=[dict(id='find', label=T('看更多诊所并比较', 'See more clinics and compare'), primary=False),
                         dict(id='doctor-search', label=T('按医生或诊所名字找', 'Find by doctor or clinic name'), primary=False)])


# ---- D. Figure out my insurance -------------------------------------------------------------

def _insurance_stages(cov):
    middle = T('比较计划', 'Compare plans') if cov == 'choosing' else T('讲清楚你的情况', 'Your options in plain words')
    return [T('你的情况', 'Your situation'), middle, T('要确认的事', 'What to confirm'), T('拿去看病', 'Use it for care')]


def _ranked_plans(profile):
    saved = profile.get('plan_compare')
    if not saved:
        return None
    try:
        return compare_plans(saved)
    except ValueError:
        return None


def insurance(m, profile):
    cov, plan = m['coverage'], m['plan']
    base = dict(stages=_insurance_stages(cov), stage=0 if cov == 'not_sure' else 1, clinics=[], links=[])
    go_settle = dict(id='go-settle', label=T('用它找一个常规医生', 'Use it to find a regular doctor'), primary=False)
    if cov == 'insured' and m['sbc']:
        b = profile['plan_benefits']
        s = b.get('services') or {}
        p, u, e = (describe(s.get(k, {})) for k in ('primary', 'urgent', 'er'))
        cost = [T(f'常规医生：{p}', f'Regular doctor: {p}'), T(f'Urgent care：{u}', f'Urgent care: {u}'), T(f'急诊 ER：{e}', f'Emergency room: {e}')]
        if b.get('deductible') is not None:
            cost.append(T(f'Deductible：${b["deductible"]:,.0f}', f'Deductible: ${b["deductible"]:,.0f}'))
        if b.get('oop_max') is not None:
            cost.append(T(f'每年自付上限：${b["oop_max"]:,.0f}', f'Yearly out-of-pocket limit: ${b["oop_max"]:,.0f}'))
        src = b.get('source') or {}
        return base | dict(
            headline=T(f'{plan or "你的计划"}：常规医生 {p}，urgent care {u}，急诊 {e}。', f'{plan or "Your plan"} in plain words: regular doctor {p}, urgent care {u}, ER {e}.'),
            why=[dict(text=T(f'读自你核对过的 SBC（{src.get("file") or "SBC"}，{src.get("read_on", "")}）', f'Read from your reviewed SBC ({src.get("file") or "SBC"}, {src.get("read_on", "")})'), source=None),
                 dict(text=T('网络外通常贵得多或不报。', 'Out-of-network care can cost much more or not be covered.'), source=_src('total_costs'))],
            cost=cost,
            do_now=dict(text=T('打卡背面的会员电话，确认你想去的医生在网络内。', 'Call the member number on your card to confirm your doctor is in network.'),
                        script='Is this clinician at this address in network for my exact plan? Do I need a referral or a PCP on file?',
                        gloss=T('意思：这位医生在我计划的网络内吗？需要转诊或登记 PCP 吗？', 'Check network and referral rules.')),
            unknown=[T('具体医生是否在网络内', 'Whether a specific clinician is in network'), T('今年 deductible 还剩多少', 'How much deductible is left this year')],
            then=T('用这些数字去找医生', 'Use these numbers to pick a doctor'), actions=[go_settle])
    if cov == 'insured' and _nushp(m):
        ref = NUSHP['reference_copays']
        return base | dict(
            headline=T(f'NUSHP：今年的看病费用还没确认；去年公布的常规医生是 ${ref["default_in_network"]}。',
                       f'Your NUSHP plan: this year’s visit costs aren’t confirmed yet; last published regular-doctor copay was ${ref["default_in_network"]}.'),
            why=[dict(text=T('学校页面列出 2026–27 日期和年费，但福利 PDF 仍是 2025–26。', 'NEU lists 2026–27 dates and fee, but its benefit PDFs still open 2025–26 files.'), source=dict(NUSHP['links'][0], checked_on=NUSHP['checked_on']))],
            cost=[T(f'学生年费 ${NUSHP["annual_student_fee"]:,}（2026–27 参考，{NUSHP["period"]["start"]} 至 {NUSHP["period"]["end"]}）',
                    f'Student annual fee ${NUSHP["annual_student_fee"]:,} (2026–27 reference, {NUSHP["period"]["start"]} to {NUSHP["period"]["end"]})'),
                  T(f'常规医生：参考 ${ref["default_in_network"]}（Fenway ${ref["fenway"]}），去年/未注明年份，需确认', f'Regular doctor: reference ${ref["default_in_network"]} (${ref["fenway"]} at Fenway), prior-year/undated — confirm'),
                  T('今年的 urgent care、ER、deductible：未知，不按 0 计算', 'This year’s urgent care, ER and deductible: unknown, not $0')],
            do_now=dict(text=T(f'向 NUSHP 要 2026–27 的 SBC：{NUSHP["contact"]}', f'Ask NUSHP for the 2026–27 SBC: {NUSHP["contact"]}'),
                        script='Could you send me the 2026–27 Summary of Benefits and Coverage for my exact NUSHP product?',
                        gloss=T('意思：请发给我今年我这个具体 NUSHP 计划的 SBC。', 'Request this year’s SBC.')),
            unknown=[T('你的具体产品（PPO 或 EPO）：看会员卡或 MyBlue', 'Your exact product (PPO or EPO): check your card or MyBlue'),
                     T('今年各项自付金额：拿到 SBC 后上传', 'This year’s cost sharing: upload the SBC once you have it')],
            then=T('拿到 SBC 后上传，费用会自动算出', 'Upload the SBC when you get it; costs fill in automatically'),
            links=[dict(l, checked_on=NUSHP['checked_on']) for l in NUSHP['links']],
            actions=[dict(id='sbc', label=T('上传我的 SBC', 'Add my SBC'), primary=True), go_settle])
    if cov == 'insured':
        return base | dict(
            headline=T('上传你计划的 SBC，我们把它变成每次看病自己付多少。', 'Add your plan’s SBC and we’ll turn it into what each visit costs you.'),
            why=[dict(text=T('所有美国计划都按同一联邦模板公布 SBC；在本机读取，不联网。', 'Every US plan publishes an SBC on the same federal template; it is read on this computer.'), source=_src('total_costs'))],
            cost=[T('常规医生、urgent care、急诊：未知，不按 0 计算', 'Regular doctor, urgent care, ER: unknown, not $0')],
            do_now=dict(text=T('在保险公司会员网站下载 SBC PDF，然后上传。', 'Download the SBC PDF from your insurer’s member site, then add it here.'), script='', gloss=None),
            unknown=[T('你的计划各项自付', 'Your plan’s cost sharing')], then=T('读完后核对每个数字', 'Review each value after it is read'),
            actions=[dict(id='sbc', label=T('上传我的 SBC', 'Add my SBC'), primary=True), go_settle])
    if cov == 'uninsured':
        return base | dict(
            headline=T('先查学校是不是已经给你上了保险；如果没有，这些地方不需要保险也能看病。',
                       'First check whether your school already enrolled you; if not, here’s care you can get without insurance.'),
            why=[dict(text=T('很多学校自动给学生上计划。', 'Many schools enroll students automatically.'), source=_src('neu_plan')),
                 dict(text=T('社区健康中心按收入收费。', 'Community health centers charge by income.'), source=_src('hrsa')),
                 dict(text=T('非营利医院必须有书面的经济援助政策。', 'Nonprofit hospitals must have a written financial assistance policy.'), source=_src('fap')),
                 dict(text=T('自费可以要求书面的 Good Faith Estimate。', 'Self-pay patients can ask for a written Good Faith Estimate.'), source=_src('gfe'))],
            cost=[T('自费价格：未知，不按 0 计算，请诊所报价', 'Self-pay prices: unknown, not $0 — ask each clinic')],
            do_now=dict(text=T('打电话问诊所自费价格和减免。', 'Call a clinic and ask for its self-pay price and assistance.'),
                        script='Hi, I don’t have insurance. What is your self-pay price for this visit? Is there a sliding scale or financial assistance?',
                        gloss=T('意思：我没有保险，自费多少？有没有减免？', 'Ask for price and assistance.')),
            unknown=[T('你是否已经被学校计划覆盖', 'Whether your school plan already covers you'), T('你是否符合 MassHealth 等资格：只有官方能判断', 'Eligibility for MassHealth and similar: only official channels decide')],
            then=T('想买保险？把情况改成「在选保险」', 'Want coverage? Change your situation to “choosing a plan”'),
            links=[_src('hrsa'), _src('nafc'), _src('connector')],
            actions=[dict(id='me', label=T('我其实想买保险', 'I want to get a plan'), primary=False), go_settle])
    if cov == 'choosing':
        result = _ranked_plans(profile)
        complete = sorted([p for p in (result or {}).get('plans', []) if p['complete']], key=lambda p: p['year_total'])
        if len(complete) >= 2:
            diff = complete[1]['year_total'] - complete[0]['year_total']
            headline = T(f'按你预计的看病需求，{complete[0]["name"]} 今年大约便宜 ${diff:,.0f}。',
                         f'{complete[0]["name"]} costs about ${diff:,.0f} less this year for the care you expect.')
        elif result and result['plans']:
            blocked = next((p for p in result['plans'] if not p['complete']), result['plans'][0])
            gaps = ', '.join(blocked['unknown'] + blocked['not_covered']) or 'premium'
            headline = T(f'还不能排名：{blocked["name"]} 的 {gaps} 费用未知。', f'Can’t rank yet: {blocked["name"]} has unknown costs for {gaps}.')
        else:
            headline = T('按你一年会用到的医疗比较计划：保费加上实际看病的自付。', 'Compare plans on the care you expect this year: premium plus what you’d pay.')
        return base | dict(
            headline=headline,
            why=[dict(text=T('只看保费会误导；要看一年总花费。', 'Premium alone misleads; compare the yearly total.'), source=_src('total_costs'))],
            cost=[T('只用你输入的数字；未知或不报的项目不能排名', 'Uses only the numbers you enter; plans with unknown or uncovered care can’t be ranked')],
            do_now=dict(text=T('输入 2–3 个候选计划的保费和各项自付（看它们的 SBC）。', 'Enter 2–3 candidate plans’ premium and costs (from their SBCs).'), script='', gloss=None),
            unknown=[T('资格和补贴：只有官方渠道能判断', 'Eligibility and subsidies: only official channels decide')],
            then=T('只通过学校或 Health Connector 等官方渠道投保', 'Enroll only through your school or official channels like the Health Connector'),
            links=[_src('connector'), _src('healthcare_gov')],
            actions=[dict(id='plans', label=T('比较计划', 'Compare plans'), primary=True)])
    return base | dict(
        headline=T('先确认你有没有保险：查这两个地方。', 'Let’s find out if you’re covered: check these two places.'),
        why=[dict(text=T('很多学校自动给学生上计划，学费账单里可能已经有这笔费用。', 'Many schools enroll students automatically; the fee may already be on your tuition bill.'), source=_src('neu_plan'))],
        cost=[T('未知，不按 0 计算：先确认保险', 'Unknown, not $0: confirm coverage first')],
        do_now=dict(text=T('1. 学生账户里有没有健康计划费用或 waiver 记录；2. 学校健康计划网站上的会员查询。', '1. Your student account: look for a health plan charge or waiver. 2. Your school health plan site’s member lookup.'), script='', gloss=None),
        unknown=[T('你的保险状态', 'Your coverage status')], then=T('知道答案后，更新「我的情况」', 'Once you know, update your situation'),
        links=[_src('neu_plan')],
        actions=[dict(id='me', label=T('我知道了，更新我的情况', 'I know now — update my situation'), primary=True)])


# ---- entry ---------------------------------------------------------------------------------

def card(kind, profile):
    if kind not in CARD_KINDS:
        return None
    m = me(profile)
    body = settle(m, profile or {}) if kind == 'first_visit' else insurance(m, profile or {})
    return dict(body, kind=kind, coverage=m['coverage'])


def next_line(kind, profile):
    """Bilingual "zh / en" next action for saved-task lists; None for entries without a card yet."""
    c = card(kind, profile)
    if c is None:
        return None
    zh, en = c['do_now']['text']
    return f'{zh} / {en}'


def _localize(value, i):
    if isinstance(value, tuple) and len(value) == 2 and all(isinstance(x, str) for x in value):
        return value[i]
    if isinstance(value, dict):
        return {k: _localize(v, i) for k, v in value.items()}
    if isinstance(value, list):
        return [_localize(v, i) for v in value]
    return value


def view(kind, profile):
    c = card(kind, profile)
    return None if c is None else {'zh': _localize(c, 0), 'en': _localize(c, 1)}
