"""Shared care-task lifecycle; a report is optional evidence, never a diagnosis."""
import time
from .navigation import text

KINDS = {'general': '一起理清下一步 / Help me get started',
         'first_visit': '我刚来，先安顿好 / I’m new here — set me up', 'concern': '现在不舒服，该去哪 / Something’s wrong — where do I go?',
         'follow_up': '医生让我做件事，或拿到了结果 / A clinician told me to do something, or I got results', 'insurance': '弄懂我的保险 / Figure out my insurance',
         'report': '我想讨论检查结果 / Discuss test results'}


def create(raw, ident):
    kind = raw.get('kind', 'general')
    if kind not in KINDS:
        raise ValueError('Choose a supported starting point')
    goal = text(raw.get('goal'), 2000)
    if not goal:
        raise ValueError('Tell us what you want help with; no medical details are required')
    return dict(id=ident, kind=kind, goal=goal, description=goal, report_ids=[],
                created=time.time(), status='planning', contact={})


def next_step(case):
    if case.get('status') == 'attended':
        return '回顾医生建议，记录后续任务 / Review clinician instructions and follow-ups.'
    return '选择这次要完成的目标，再准备问题或寻找就医选项。 / Choose your goal, then prepare questions or find care.'


import re

_CHOOSING = re.compile(r"compar|choos|pick|which plan|enrol|buy (a |an )?(health )?(insurance|plan)|比较|选.*(保险|计划)|买保险", re.I)
_UNINSURED = re.compile(r"no insurance|not insured|uninsured|without insurance|(don'?t|do not|doesn'?t) have (any |health )?insurance|没有保险|没保险|自费", re.I)
_INSURED = re.compile(r"have .*insurance|my (insurance|plan)|student (health )?(insurance|plan)|nushp|bcbs|blue cross|有.*保险|学生保险|我的保险", re.I)


def coverage_situation(case, profile=None):
    """Deterministic: a task's own Find care answer wins (it priced that shortlist), then the
    saved profile, then the user's own goal wording."""
    profile = profile or {}
    person = case.get('input') or {}
    if person.get('insurance') == 'yes':
        return 'insured'
    if person.get('insurance') == 'no':
        return 'choosing' if person.get('wants_insurance') else 'uninsured'
    if profile.get('insurance') == 'yes':
        return 'insured'
    if profile.get('insurance') == 'no':
        return 'choosing' if profile.get('wants_insurance') else 'uninsured'
    # Goal wording is only a suggestion (suggested_coverage): "I think I have insurance" is not
    # a confirmed answer, so it never shows as settled (RESTRUCTURE.md §4).
    return 'unknown'


def suggested_coverage(case):
    goal = case.get('goal', '')
    if _CHOOSING.search(goal):
        return 'choosing'
    if _UNINSURED.search(goal):
        return 'uninsured'
    if _INSURED.search(goal):
        return 'insured'
    return None


def _section(title, *items):
    return {'title': title, 'items': list(items)}


def _insurance_sections(situation, profile):
    plan = ((profile or {}).get('plan') or {}).get('name')
    plan_en, plan_zh = (f' ({plan})', f'（{plan}）') if plan else ('', '')
    after = ('拿到答复后：在「寻找就医选项」的候选列表里点「记录诊所答复」或「记录报价」，比较结果会更新。',
             'After you get answers: in Find care, use “Record office reply” or “Add quote” on that clinic so the comparison updates.')
    if situation == 'insured':
        return [
            _section(('你的情况', 'Your situation'),
                     (f'你有医疗保险{plan_zh}。还没确认：具体医生是否在网络内、看一次自己要付多少。',
                      f'You have insurance{plan_en}. Not yet confirmed: whether a specific clinician is in network, and what a visit costs you.')),
            _section(('先准备好', 'Have ready'),
                     ('保险卡：Member ID、具体计划名称、卡背面的会员服务电话', 'Your insurance card: member ID, exact plan name, and the member services number on the back'),
                     ('想去的 1–2 家诊所（名称和地址）', '1–2 clinics you are considering (name and address)')),
            _section(('问保险公司（卡背面电话或会员网站）', 'Ask your insurer (number on your card or the member website)'),
                     ('这位医生、这个地址在我这个具体计划的网络内吗？', 'Is this clinician at this address in network for my exact plan?'),
                     ('看 primary care 的 copay 是多少？要先付 deductible 吗？', 'What is my copay for a primary-care visit? Does the deductible apply first?'),
                     ('需要 referral，或需要先登记 primary care 医生（PCP）吗？', 'Do I need a referral or a primary care physician (PCP) on file?')),
            _section(('问诊所', 'Ask the clinic'),
                     ('现在接收新病人吗？', 'Are you accepting new patients?'),
                     ('接受我这个具体计划吗？', 'Do you accept my exact plan?')),
            _section(('下一步', 'Next'), after)]
    if situation == 'uninsured':
        return [
            _section(('你的情况', 'Your situation'),
                     ('你目前没有保险。在诊所给出价格前，费用都是未知，不按 0 计算。', 'You do not have insurance right now. Until a clinic gives a price, costs are unknown, not $0.')),
            _section(('先确认', 'Check first'),
                     ('你是否已经有自己不知道的保障？例如学校健康计划、家人或雇主的计划。', 'Do you already have coverage you did not know about, such as a school health plan or a family or employer plan?')),
            _section(('问诊所', 'Ask the clinic'),
                     ('新病人看一次 primary care 的自费价格是多少？包含哪些项目？', 'What is your self-pay price for a new-patient primary-care visit, and what does it include?'),
                     ('有没有按收入减免（sliding fee）或经济援助？可以分期付吗？', 'Do you offer a sliding fee, financial assistance or a payment plan?')),
            _section(('如果想买保险', 'If you want coverage'),
                     ('通过官方渠道办理（马萨诸塞州：Health Connector 或 MassHealth）。这里不判断你是否符合资格。', 'Enroll only through official channels (in Massachusetts: the Health Connector or MassHealth). Eligibility is not decided here.')),
            _section(('下一步', 'Next'), after)]
    if situation == 'choosing':
        return [
            _section(('你的情况', 'Your situation'),
                     ('你在比较保险计划。要比的是一年总花费：保费，加上实际看病时自己付的钱。', 'You are comparing plans. Compare the yearly total: premium plus what you pay when you use care.')),
            _section(('先准备好', 'Have ready'),
                     ('候选计划的具体名称', 'The exact names of the plans you are considering'),
                     ('一年大概看几次医生、有没有长期用药', 'Roughly how many visits and regular prescriptions you expect in a year')),
            _section(('每个计划都查清（看它的 SBC 文件）', 'Check for each plan (in its Summary of Benefits and Coverage)'),
                     ('每月保费', 'Monthly premium'),
                     ('Deductible 和 primary care 的 copay', 'Deductible and primary-care copay'),
                     ('你想去的诊所在不在网络内', 'Whether the clinic you want is in network'),
                     ('每年自付上限（out-of-pocket maximum）', 'Yearly out-of-pocket maximum')),
            _section(('下一步', 'Next'),
                     ('在「我的健康」上传计划的 SBC，可以自动填入费用。只通过官方渠道投保。', 'Upload a plan’s SBC in My health to fill in costs. Enroll only through official channels.'))]
    return [
        _section(('先回答一个问题', 'One question first'),
                 ('你现在有医疗保险吗？点「填写或核对保险」选择，下面的问题会按你的情况调整。', 'Do you have health insurance now? Use “Add or check my plan”; the questions here will match your answer.')),
        _section(('两种情况的要点', 'In short'),
                 ('有保险：问保险公司，这位医生是否在网络内、看一次自付多少。', 'With insurance: ask your insurer whether the clinician is in network and what a visit costs you.'),
                 ('没保险：问诊所，新病人的自费价格，以及有没有减免。', 'Without insurance: ask the clinic for its new-patient self-pay price and any financial assistance.'))]


def preparation_sections(case, reports, profile=None):
    """Sections of (zh, en) pairs so the interface can show one language at a time."""
    sections = [_section(('我的这次目标', 'My goal'), (case.get('goal', ''), case.get('goal', '')))]
    if case.get('kind') == 'insurance':
        sections += _insurance_sections(coverage_situation(case, profile), profile)
    else:
        if case.get('kind') == 'first_visit':
            sections[0]['items'].append(('我希望建立 primary care 联系，并了解联系这家诊所需要准备什么。',
                                         'I would like to establish primary care and understand what to prepare when contacting a practice.'))
        sections.append(_section(('想向医生确认', 'Questions for my clinician'),
                                 ('这次就诊应该讨论哪些问题？', 'What should we discuss at this visit?'),
                                 ('如需后续检查或就诊，请说明原因、时间及如何安排。', 'If follow-up is recommended, what is it for, when, and how should I arrange it?')))
    for report in reports:
        rows = [(line, line) for line in (f"{r['name']}: {r['result']} | Reported reference: {r['reference']} | Source flag: {r['flag'] or '-'}" for r in report['rows'])]
        sections.append(_section(('我带来的资料：' + report['label'], 'Report: ' + report['label']),
                                 ('以下是我核对过的报告记录，不是新增诊断。', 'Reviewed source facts, not a new diagnosis.'), *rows,
                                 ('请结合我的情况解释这些结果，是否需要进一步行动？', 'Please explain these results in my context and whether any action is needed.')))
    return sections


def localized(sections, lang):
    i = 0 if lang == 'zh' else 1
    return [{'title': s['title'][i], 'items': [item[i] for item in s['items']]} for s in sections]


def as_text(sections):
    return '\n'.join(f"{s['title']}:\n" + '\n'.join('- ' + item for item in s['items']) for s in sections)


def preparation(case, reports, profile=None):
    """Bilingual plain text kept for the call-script note."""
    sections = preparation_sections(case, reports, profile)
    lines = []
    for s in sections:
        lines.append(f"{s['title'][0]} / {s['title'][1]}:")
        lines += [zh if zh == en else f'{zh} / {en}' for zh, en in s['items']]
    return '\n'.join(lines)
