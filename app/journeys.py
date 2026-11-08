"""Shared care-task lifecycle; a report is optional evidence, never a diagnosis."""
import time
from .navigation import text

KINDS = {'general': '一起理清下一步 / Help me get started',
         'first_visit': '我想找一位固定医生 / Find a regular doctor', 'concern': '我有新的健康困扰 / A new health concern',
         'report': '我想讨论检查结果 / Discuss test results', 'follow_up': '医生让我复诊或跟进 / My doctor recommended a next step'}


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


def preparation(case, reports):
    lines = ['我的这次目标 / My goal: ' + case.get('goal', 'Discuss my care needs')]
    if case.get('kind') == 'first_visit':
        lines += ['我希望建立 primary care 联系，并了解联系这家诊所需要准备什么。 / I would like to establish primary care and understand what to prepare when contacting a practice.']
    lines += ['想向医生确认 / Questions for my clinician:',
              '这次就诊应该讨论哪些问题？ / What should we discuss at this visit?',
              '如需后续检查或就诊，请说明原因、时间及如何安排。 / If follow-up is recommended, what is it for, when, and how should I arrange it?']
    for report in reports:
        lines += ['', '我带来的资料 / Report: ' + report['label'],
                  '以下是我核对过的报告记录，不是新增诊断。 / Reviewed source facts, not a new diagnosis.']
        for row in report['rows']:
            lines.append(f"{row['name']}: {row['result']} | Reported reference: {row['reference']} | Source flag: {row['flag'] or '-'}")
        lines += ['请结合我的情况解释这些结果，是否需要进一步行动？ / Please explain these results in my context and whether any action is needed.']
    return '\n'.join(lines)
