"""Public NUSHP reference facts, separated from member-confirmed cost inputs.

Reviewed 2026-11-07. Current-year dates/annual fee are supported, while linked
benefit PDFs are still 2025–26. No provider network or member enrollment is inferred.
"""
from copy import deepcopy

NUSHP = {
    'checked_on': '2026-11-07',
    'title': 'Northeastern student plan · 2026–27 reference',
    'period': {'start': '2026-09-01', 'end': '2027-08-31'},
    'annual_student_fee': 3049,
    'carrier': 'Blue Cross Blue Shield of Massachusetts',
    'network_guidance': 'NEU links to the insurer directory and says to select PPO or EPO. Confirm your exact product using your current ID card or MyBlue account.',
    'benefit_status': 'Current-year cost sharing not verified: the official page lists 2026–27 dates, but its Summary of Benefits and SBC links still open 2025–26 documents. They are not used for current estimates.',
    'published_highlights': 'The undated NEU highlights page lists $20 for a Fenway medical office visit versus $25 at other in-network providers. Treat these as leads to confirm for 2026–27, not a quote or verified current-year copay.',
    'member_status': 'Your enrollment, exact coverage dates, remaining balances and clinician-level network still require confirmation.',
    'network_status': 'Neither Brookline candidate has been confirmed in-network. Check the exact clinician, address and service with both the insurer and the office.',
    'steps': [
        'Open MyBlue or use your current ID card to confirm your exact NUSHP product and active coverage.',
        'In the insurer directory, search primary care around 02445; use the network shown in your account (NEU public guidance: PPO or EPO).',
        'Search the selected clinician at 1 Brookline Place, Suite 225, or 1180 Beacon Street, 8th floor. A practice name alone is insufficient.',
        'Ask the insurer and office to confirm the service, network, current-year visit benefit and separate facility/lab charges. Save the dated answer in Add quote / confirmation.',
    ],
    'links': [
        {'title': 'NEU · 2026–27 dates and annual fees', 'url': 'https://studenthealthplan.northeastern.edu/effective-dates-costs/'},
        {'title': 'NEU · published benefits (year needs checking)', 'url': 'https://studenthealthplan.northeastern.edu/highlighted-benefits/'},
        {'title': 'BCBSMA · Find a Doctor & Estimate Costs', 'url': 'https://member.bluecrossma.com/fad'},
        {'title': 'NEU · insurance information', 'url': 'https://studenthealthplan.northeastern.edu/your-insurance-information/'},
    ],
    'contact': 'NUSHP office: 617-373-8007 · NUSHP@northeastern.edu. Request the 2026–27 SBC/benefit description; use the Member Service number on your current ID card for personal coverage questions.',
    'external_handoff': 'These links open external websites outside the gateway ledger. The links themselves contain no patient details; anything you enter there follows that website’s privacy practices.',
}


def reference(person):
    return deepcopy(NUSHP) if person.get('scenario') == 'neu_student' else None
