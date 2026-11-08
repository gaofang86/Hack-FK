"""One answer card per entry point, shaped by the person's own situation ("Me").

RESTRUCTURE.md §2–§6. Fixed rules, sourced, no model. Text is (zh, en) pairs; `view()`
returns one card per interface language. Coverage is a shared parameter: it is read from
the saved profile only, never guessed from goal wording, and `not_sure` is never shown as
confirmed. Unknown costs are never $0.

Entry points (kind ids kept for saved-task compatibility):
  first_visit -> A. I'm new here — set me up
  concern     -> B. Something's wrong — where do I go?
  follow_up   -> C. A clinician told me to do something, or I got results (legacy 'report' too)
  insurance   -> D. Figure out my insurance
"""
import re
from datetime import date

from .catalog import REAL, BROOKLINE, SOURCES_CHECKED
from .benefits import clean_plan
from .sbc import describe
from .scenarios import SOURCES as SCENARIO_SOURCES, compare_plans
from .student_plan import NUSHP
from .expect import SOURCES as EXPECT_SOURCES

COVERAGES = ('insured', 'uninsured', 'choosing', 'not_sure')
LANGUAGES = ('English', 'Chinese', 'Spanish')
CARD_KINDS = ('first_visit', 'concern', 'follow_up', 'report', 'insurance')  # 'report' is the legacy id for C
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


# ---- B. Something's wrong — where do I go? --------------------------------------------------
# The safety check always comes first and never depends on coverage. Price appears only for
# non-emergency levels. No urgent-care location is invented: there is no sourced same-day
# directory, so the card points to the insurer's directory or health-center finder instead.

SICK_STAGES = [T('安全检查', 'Safety check'), T('去哪', 'Where to go'), T('费用和怎么去', 'Cost and getting there'), T('之后', 'Afterwards')]
_UHCS = next(p for p in REAL if p['id'] == 'nu-uhcs')
_FAIR = dict(EXPECT_SOURCES['fair_health'])
_FAD = {'title': 'BCBSMA · Find a Doctor & Estimate Costs', 'url': 'https://member.bluecrossma.com/fad', 'checked_on': NUSHP['checked_on']}
VENUE_TEXT = {
    'urgent_care': T('Urgent care：当天走进去看扭伤、伤口、感染和发烧，不处理重大急症。', 'Urgent care: walk in the same day for sprains, cuts, infections and fevers; not for major emergencies.'),
    'campus_health': T('校园诊所：学生的第一站，先查开放时间和就诊费。', 'Campus health clinic: often the first stop for students; check hours and any visit fee.'),
    'telehealth': T('视频看诊（telehealth）：适合很多常见问题，但不能近距离看眼睛或拍 X 光。', 'Video visit (telehealth): works for many common problems; can’t examine an eye up close or X-ray an injury.'),
    'er': T('急诊 ER：情况变坏或出现任何危险信号时去。', 'Emergency room: go if it gets worse or you notice any warning sign.'),
    'primary_care': T('常规医生预约：计划内的照护，通常提前几天到几周预约。', 'Primary care appointment: planned care, usually booked days or weeks ahead.'),
}
EMERGENCY_TEXT = {  # same wording as triage.decide, in both languages
    'emergency': T('这可能是急症。现在就打 911，或去最近的急诊室。', 'This could be an emergency. Call 911 or go to the nearest emergency room now.'),
    'crisis': T('请现在就联系：拨打或发短信 988。如果你可能付诸行动或有危险，打 911。', 'Please reach out right now: call or text 988. If you might act on these thoughts or are in danger, call 911.'),
    'poison': T('现在打中毒控制中心 1-800-222-1222。如果对方叫不醒、呼吸困难或抽搐，打 911。', 'Call Poison Control now at 1-800-222-1222. If the person is hard to wake, has trouble breathing, or has a seizure, call 911.'),
}


def _calls(safety):
    names = ' '.join(h['name'] for h in safety.get('hotlines') or [])
    calls = [dict(href='tel:911', label=T('打 911', 'Call 911'))]
    if '988' in names:
        calls += [dict(href='tel:988', label=T('打 988', 'Call 988')), dict(href='sms:988', label=T('短信 988', 'Text 988'))]
    if 'Poison' in names:
        calls.append(dict(href='tel:18002221222', label=T('打中毒控制中心', 'Call Poison Control')))
    return calls


def _emergency_kind(safety):
    names = ' '.join(h['name'] for h in safety.get('hotlines') or [])
    other = [r for r in safety.get('rules') or [] if not re.search(r'hurting|killing|poison|medicine', r, re.I)]
    if '988' in names and not other:
        return 'crisis'
    if 'Poison' in names and not other:
        return 'poison'
    return 'emergency'


def _sick_cost(m, profile, level):
    """Same-day: urgent care vs ER. Example fees are FAIR Health illustrations, never quotes."""
    s = ((profile.get('plan_benefits') or {}).get('services') or {}) if m['sbc'] else {}
    if level == 'same_day':
        if m['sbc']:
            return [T(f'你的 urgent care：{describe(s.get("urgent", {}))}（SBC）', f'Your urgent care: {describe(s.get("urgent", {}))} (SBC)'),
                    T(f'你的急诊 ER：{describe(s.get("er", {}))}（SBC）', f'Your ER: {describe(s.get("er", {}))} (SBC)')]
        ex = T('FAIR Health 示例费用（不是报价）：urgent care $300，ER $1,000', 'FAIR Health example fees (not a quote): urgent care $300, ER $1,000')
        if m['coverage'] == 'insured':
            return [T('你的 urgent care 和 ER 自付：未知，不按 0 计算；ER 那一行通常更高', 'Your urgent care and ER share: unknown, not $0; the ER line is usually higher'), ex]
        return [T('自费：未知，不按 0 计算，先问前台价格', 'Self-pay: unknown, not $0; ask the front desk first'), ex]
    if m['sbc']:
        return [T(f'常规/视频看诊：{describe(s.get("primary", {}))}（SBC）', f'Regular or video visit: {describe(s.get("primary", {}))} (SBC)')]
    if m['coverage'] == 'insured':
        return [T('看一次自付：未知，不按 0 计算；问保险的 telehealth 或护士热线', 'Your share: unknown, not $0; ask your plan about its telehealth or nurse line')]
    return [T('自费价格：未知，不按 0 计算，先问价格', 'Self-pay price: unknown, not $0; ask first')]


def sick(m, profile, safety):
    cov, plan, nushp = m['coverage'], m['plan'] or None, _nushp(m)
    recheck = dict(id='recheck', label=T('重新检查', 'Redo the safety check'), primary=False)
    if not safety:
        return dict(stages=SICK_STAGES, stage=0,
                    headline=T('先做 30 秒安全检查：哪里不舒服？', 'First, a 30-second safety check: what’s going on?'),
                    why=[dict(text=T('先判断紧急程度，再谈去哪和费用；紧急情况永远不比价。', 'Urgency comes before where to go or cost; emergencies are never priced.'), source=None)],
                    cost=[T('先完成安全检查', 'After the safety check')],
                    do_now=dict(text=T('勾选符合的情况，或用几句话描述。只在本机判断。', 'Tick what fits, or describe it in a few words. Checked on this device only.'), script='', gloss=None),
                    unknown=[], then=T('检查后：去哪、自己付多少', 'After the check: where to go and what it costs you'),
                    clinics=[], calls=[], safety_form=True, actions=[])
    level = safety['level']
    rules = [dict(text=(r, r), source=None) for r in safety.get('rules') or []]
    if level == 'emergency':
        kind = _emergency_kind(safety)
        return dict(stages=SICK_STAGES, stage=1, headline=EMERGENCY_TEXT[kind],
                    why=rules + [dict(text=T('急诊室必须先检查和稳定病情，不论你有没有保险或能否付款（联邦法律 EMTALA）。',
                                             'Emergency rooms must check and stabilize you whether or not you have insurance or can pay (federal law, EMTALA).'), source=None)],
                    cost=[T('急症不比价。先求助。', 'No price comparison for an emergency. Get help first.')],
                    do_now=dict(text=T('用下面的按钮打电话。打不了的话，请身边的人帮你打。', 'Use the button below. If you can’t call, ask someone near you to call.'), script='', gloss=None), unknown=[],
                    then=T('安全之后，再回来记录发生了什么', 'Once you’re safe, come back and record what happened'),
                    clinics=[], calls=_calls(safety), actions=[recheck])
    insured = cov == 'insured'
    if level == 'same_day':
        venues = ['urgent_care', 'campus_health', 'er']
        if m['sbc']:
            s = profile['plan_benefits'].get('services') or {}
            headline = T(f'今天就去 urgent care：你付 {describe(s.get("urgent", {}))}，急诊则是 {describe(s.get("er", {}))}。',
                         f'Get seen today at urgent care: you pay {describe(s.get("urgent", {}))}; the ER would be {describe(s.get("er", {}))}.')
        elif insured:
            headline = T(f'今天就去{"校园诊所 UHCS 或" if nushp else ""}网络内的 urgent care，通常比急诊便宜得多。',
                         f'Get seen today at {"UHCS on campus or " if nushp else ""}an in-network urgent care; it usually costs much less than the ER.')
        elif cov == 'uninsured':
            headline = T('今天就去 urgent care，除非情况变坏否则别去急诊：先问自费价格。', 'Get seen today at urgent care, not the ER unless it gets worse: ask the self-pay price first.')
        elif cov == 'choosing':
            headline = T('今天先自费去 urgent care：之后才买的保险通常不报今天这次。', 'Get seen today at urgent care and pay self-pay for now: a plan you buy later usually won’t cover today.')
        else:
            headline = T('今天就去 urgent care，并在前台问你的学校保险是否有效。', 'Get seen today at urgent care, and ask at the desk whether your school plan is active.')
        then = T('看完后：记录医生说了什么，有随访就转到 C', 'Afterwards: record what the clinician said; follow-ups go to C')
    elif level == 'soon':
        venues = ['campus_health', 'telehealth', 'urgent_care']
        if insured:
            headline = T(f'一两天内看医生：用{plan or "你的保险"}的视频看诊或校园诊所通常最便宜。',
                         f'See someone in the next day or two: a video visit or your campus clinic is usually cheapest under {plan or "your plan"}.')
        elif cov == 'uninsured':
            headline = T('一两天内看医生：社区健康中心或自费视频看诊，先问价格。', 'See someone in the next day or two: a community health center or a self-pay video visit; ask the price first.')
        elif cov == 'choosing':
            headline = T('一两天内看医生，先自费；选保险的事可以同时在 D 里做。', 'See someone in the next day or two and pay self-pay for now; choose a plan in D meanwhile.')
        else:
            headline = T('一两天内看医生：先查你是否有学校保险，它决定去哪最便宜。', 'See someone in the next day or two: first check whether your school plan covers you; it decides the cheapest place.')
        then = T('如果变严重：直接去 urgent care 或急诊', 'If it gets worse: go to urgent care or the ER')
    else:
        venues = ['primary_care', 'campus_health', 'telehealth']
        headline = {
            'insured': T('这可以约常规门诊：找网络内的常规医生，体检常常是 0 元。', 'This can be a regular appointment: book an in-network regular doctor; checkups are often $0.')
            if 'checkup' in (safety.get('checks') or []) else
            T('这可以约常规门诊：找网络内的常规医生或校园诊所。', 'This can be a regular appointment: book an in-network regular doctor or your campus clinic.'),
            'uninsured': T('这可以约常规门诊：社区健康中心按收入收费，先问自费价。', 'This can be a regular appointment: community health centers charge by income; ask the self-pay price.'),
            'choosing': T('这可以约常规门诊：先选好计划，它决定你能去哪。', 'This can be a regular appointment: pick a plan first; it decides where you can go.'),
        }.get(cov, T('这可以约常规门诊：先确认你有没有保险。', 'This can be a regular appointment: confirm your coverage first.'))
        then = T('转到 A：找一个常规医生', 'Go to A: find a regular doctor')
    why = rules + [dict(text=VENUE_TEXT[v], source=_FAIR if v in ('urgent_care', 'er') else None) for v in venues]
    links = [_FAD] if nushp else ([_src('hrsa')] if cov in ('uninsured', 'choosing') else [])
    if insured:
        do_text = T('打卡背面的会员电话或护士热线，问最近的网络内 urgent care。', 'Call the member or nurse line on your card and ask for the nearest in-network urgent care.') if level == 'same_day' \
            else T('打卡背面的电话，问视频看诊或网络内诊所。', 'Call the number on your card and ask about video visits or an in-network clinic.')
        script = f'Which in-network {"urgent care" if level == "same_day" else "clinic or video visit"} near me takes {plan or "my plan"}, and what will I owe?'
        gloss = T('意思：附近哪家网络内的诊所接受我的保险？我要付多少？', 'Ask for an in-network place and your share.')
    else:
        do_text = T('到前台或打电话先问自费价格。', 'Ask the front desk or call for the self-pay price before you’re seen.')
        script = 'Hi, I don’t have insurance. What is your self-pay price for this visit, and do you offer a discount or payment plan?'
        gloss = T('意思：我没有保险，这次自费多少？有没有折扣或分期？', 'Ask for the self-pay price.')
    unknown = [T('具体地点的价格和今天能不能看：营业时间不等于有号', 'The exact place’s price and whether they can see you today: open hours are not availability')]
    if insured and not m['sbc']:
        unknown.append(T('你计划的 urgent care / ER 自付：上传 SBC 后会显示', 'Your plan’s urgent care / ER share: add your SBC to see it'))
    actions = [recheck]
    if level == 'routine':
        actions.insert(0, dict(id='go-settle', label=T('找一个常规医生', 'Find a regular doctor'), primary=True))
    if cov in ('not_sure', 'choosing'):
        actions.insert(0, dict(id='go-insurance', label=T('弄懂我的保险', 'Figure out my insurance'), primary=level == 'routine'))
    return dict(stages=SICK_STAGES, stage=2, headline=headline, why=why, cost=_sick_cost(m, profile, level),
                do_now=dict(text=do_text, script=script, gloss=gloss), unknown=unknown, then=then,
                clinics=[_clinic(_UHCS)] if nushp and level in ('same_day', 'soon') else [], calls=[], links=links,
                actions=actions)


# ---- C. A clinician told me to do something, or I got results -------------------------------
# Only what the person entered and report rows they reviewed. A lab flag is quoted, never
# interpreted; questions go to the clinician. Due dates become to-dos on My health.

FOLLOW_STAGES = [T('你手里有什么', 'What you have'), T('它说了什么（只列事实）', 'What it says (facts only)'),
                 T('问谁、问什么', 'Who to ask and what'), T('记录结果', 'Record the outcome')]
FOLLOW_TYPES = ('follow_up', 'refill', 'results')


def clean_followup(raw, has_reports=False):
    kind = raw.get('type')
    if kind not in FOLLOW_TYPES:
        raise ValueError('Choose a follow-up, a refill or results')
    what = str(raw.get('what') or '').strip()[:160]
    who = str(raw.get('who') or '').strip()[:120]
    due = str(raw.get('due') or '').strip()[:10]
    if due:
        try:
            due = date.fromisoformat(due).isoformat()
        except ValueError:
            raise ValueError('Use a valid date')
    if not what and not (kind == 'results' and has_reports):
        raise ValueError({'follow_up': 'Say what the clinician asked for', 'refill': 'Add the medicine name',
                          'results': 'Say which results, or add the lab PDF'}[kind])
    return dict(type=kind, what=what, who=who, due=due)


def add_todo(profile, f):
    """A dated follow-up or refill becomes a to-do on My health (health.todos)."""
    if not f.get('due') or not f.get('what'):
        return
    if f['type'] == 'refill':
        meds = profile.setdefault('medications', [])
        if f['what'] not in meds:
            meds.append(f['what'])
        profile.setdefault('refills', {})[f['what']] = f['due']
    elif f['type'] == 'follow_up':
        ups = [u for u in profile.get('follow_ups') or [] if u.get('what') != f['what']]
        profile['follow_ups'] = ups + [{'what': f['what'], 'due': f['due']}]


def follow(m, profile, f, reports):
    cov, plan = m['coverage'], m['plan'] or None
    facts = [dict(name=r['name'], result=r['result'], reference=r['reference'], flag=r['flag'], label=rep['label'])
             for rep in reports for r in rep['rows']]
    report_ids = [rep['id'] for rep in reports]
    edit = dict(id='followup-edit', label=T('修改我手里的事', 'Edit what I have'), primary=False)
    if not f:
        return dict(stages=FOLLOW_STAGES, stage=0,
                    headline=T('医生让你做什么，或者你拿到了什么结果？', 'What did your clinician ask you to do, or what results do you have?'),
                    why=[dict(text=T('先写下原话和期限；这里不解释结果，也不安排检查。', 'Start with their words and the deadline; this page never interprets results or orders tests.'), source=None)],
                    cost=[T('写下之后再算', 'Once you tell us')],
                    do_now=dict(text=T('选一类，写一句话。有化验单可以加 PDF。', 'Pick one and write a sentence. Add the lab PDF if you have one.'), script='', gloss=None),
                    unknown=[], then=T('之后：该问谁、问什么', 'Next: who to ask and what'),
                    clinics=[], calls=[], followup_form=True, report_upload=True, facts=facts, report_ids=report_ids, actions=[])
    what, who, due = f['what'], f['who'], f['due']
    who_en, who_zh = who or 'your clinician’s office', who or '医生的诊所'
    by_en, by_zh = (f' by {due}', f'（{due} 前）') if due else ('', '')
    s = ((profile.get('plan_benefits') or {}).get('services') or {}) if m['sbc'] else {}
    flagged = [x for x in facts if x['flag']]
    if f['type'] == 'refill':
        lead = T(f'在{by_zh or "用完前"}续上 {what}', f'Refill {what}{by_en or " before it runs out"}')
        tail = {'insured': T(f'：找药房或开药医生；{"仿制药 " + describe(s.get("generic", {})) if m["sbc"] else "问你计划的药品自付"}。',
                             f': ask your pharmacy or prescriber; {"generic drugs are " + describe(s.get("generic", {})) if m["sbc"] else "ask what your plan charges for it"}.'),
                'uninsured': T('：问药房现金价，以及有没有折扣。', ': ask the pharmacy for the cash price and any discount.'),
                'choosing': T('：先按现金价续上，新计划生效前别断药。', ': pay the cash price for now so you don’t run out before a new plan starts.'),
                'not_sure': T('：先确认你的保险，它决定药价。', ': confirm your coverage first; it decides the price.')}[cov]
        script = f'Hi, I need a refill of {what}. Is a new prescription needed, and what will it cost me{" with " + plan if plan else ""}?'
        cost = [T(f'仿制药：{describe(s.get("generic", {}))}（SBC）', f'Generic drugs: {describe(s.get("generic", {}))} (SBC)')] if m['sbc'] else \
            [T('药价：未知，不按 0 计算，问药房', 'Drug price: unknown, not $0; ask the pharmacy')]
    else:
        if f['type'] == 'results':
            n = len(facts)
            lead = T(f'请 {who_zh} 解释你的结果' + (f'（已核对 {n} 项，{len(flagged)} 项有化验单标记）' if n else f'：{what}'),
                     f'Ask {who_en} what your results mean for you' + (f' ({n} reviewed, {len(flagged)} marked by the lab)' if n else f': {what}'))
        else:
            lead = T(f'你的随访「{what}」{by_zh}：联系{who_zh}', f'Your follow-up ({what}){by_en}: contact {who_en}')
        tail = {'insured': T(f'；在{plan or "你的计划"}下复诊可能需要转诊。', f'; a follow-up visit under {plan or "your plan"} may need a referral.'),
                'uninsured': T('；如需复诊，先问自费价。', '; ask the self-pay price before any follow-up visit.'),
                'choosing': T('；新计划未必赶得上复诊，也问一下自费价。', '; a new plan may not start in time for a follow-up, so ask the self-pay price.'),
                'not_sure': T('；预约复诊前先确认你的保险。', '; confirm your coverage before booking a follow-up visit.')}[cov] if f['type'] == 'results' else \
               {'insured': T(f'，问在{plan or "你的计划"}下需不需要转诊。', f' and ask whether it needs a referral under {plan or "your plan"}.'),
                'uninsured': T('，预约前先问自费价和减免。', ' and ask the self-pay price and assistance before booking.'),
                'choosing': T('；新计划未必来得及生效，也问一下自费价。', '; a new plan may not start in time, so ask the self-pay price too.'),
                'not_sure': T('；预约前先确认你的保险。', '; confirm your coverage before booking.')}[cov]
        if f['type'] == 'results':
            script = 'Could you explain my recent results in my context, and tell me whether any follow-up is needed?'
        else:
            script = f'Hi, my clinician asked me to {what}{by_en}. Can I schedule it, and do I need a referral{" under " + plan if plan else ""}?'
        cost = [T(f'随访就诊：{describe(s.get("primary", {}))}（SBC）', f'Follow-up visit: {describe(s.get("primary", {}))} (SBC)')] if m['sbc'] else \
            [T('就诊费用：未知，不按 0 计算；检查和化验可能另外收费', 'Visit cost: unknown, not $0; tests and labs may be billed separately')]
    headline = (lead[0] + tail[0], lead[1] + tail[1])
    why = [dict(text=T(f'你写的：{what}', f'You wrote: {what}'), source=None)] if what else []
    if facts:
        why.append(dict(text=T('化验单的标记是原文，不是诊断；只有医生能结合你的情况解释。', 'Lab flags are quoted from the report, not a diagnosis; only a clinician can explain them for you.'), source=None))
    unknown = []
    if f['type'] != 'refill':
        unknown.append(T('需不需要转诊或事先授权：问诊所或保险', 'Whether a referral or prior authorization is needed: ask the office or your insurer'))
    if not m['sbc']:
        unknown.append(T('你要付多少：问清楚再预约', 'What you’ll pay: ask before booking'))
    questions = [T(f'化验单把「{x["name"]}」标为 {x["flag"]}：这对我意味着什么？需要做什么吗？', f'My report marks {x["name"]} as {x["flag"]}: what does that mean for me, and is anything needed?') for x in flagged[:3]]
    actions = [edit]
    if cov in ('not_sure', 'choosing'):
        actions.insert(0, dict(id='go-insurance', label=T('弄懂我的保险', 'Figure out my insurance'), primary=False))
    actions.append(dict(id='record-visit', label=T('记录这次就诊', 'Record the visit'), primary=False))
    return dict(stages=FOLLOW_STAGES, stage=2, headline=headline, why=why, cost=cost,
                do_now=dict(text=T(f'打给{who_zh}，说这段话。', f'Call {who_en} and say this.'), script=script,
                            gloss=T('意思：说明医生的要求，问怎么预约、要不要转诊、要付多少。', 'Explain the request; ask how to book, referral, and cost.')),
                unknown=unknown, questions=questions,
                then=T('就诊后：记录医生说了什么，新的随访会进待办', 'After the visit: record what was said; new follow-ups become to-dos'),
                clinics=[], calls=[], report_upload=True, facts=facts, report_ids=report_ids,
                todo=bool(due and what and f['type'] != 'results'), actions=actions)


# ---- entry ---------------------------------------------------------------------------------

def card(kind, profile, case=None):
    if kind not in CARD_KINDS:
        return None
    m, profile = me(profile), profile or {}
    if kind == 'first_visit':
        body = settle(m, profile)
    elif kind == 'concern':
        body = sick(m, profile, (case or {}).get('safety'))
    elif kind in ('follow_up', 'report'):
        body = follow(m, profile, (case or {}).get('followup'), (case or {}).get('reports') or [])
    else:
        body = insurance(m, profile)
    return dict(body, kind=kind, coverage=m['coverage'])


def next_line(kind, profile, case=None):
    """Bilingual "zh / en" next action for saved-task lists; None for entries without a card yet."""
    c = card(kind, profile, case)
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


def view(kind, profile, case=None):
    c = card(kind, profile, case)
    return None if c is None else {'zh': _localize(c, 0), 'en': _localize(c, 1)}
