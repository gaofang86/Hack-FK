"""Local candidate intake and dated answers. These are user reports, not certifications."""
from datetime import date
import secrets

from .navigation import safe_url, text

ANSWER_KEYS = {
    'availability': 'Accepting new patients / appointment availability',
    'language': 'Language / interpreter support',
    'referral': 'Referral / prior authorization',
    'referral_action': 'Required referral / authorization obtained',
}


def checked_date(raw):
    try:
        value = date.fromisoformat(str(raw or ''))
    except ValueError:
        raise ValueError('Enter the actual date checked')
    if value > date.today():
        raise ValueError('The checked date cannot be in the future')
    return value.isoformat()


def new_candidate(raw, existing):
    name, address = text(raw.get('name'), 150), text(raw.get('address'), 300)
    url = safe_url(raw.get('url'))
    source = text(raw.get('source'), 500)
    if not name or not address or not source or not url:
        raise ValueError('Add the candidate name, exact address, public source URL and source description')
    if any(p['name'].casefold() == name.casefold() and p['address'].casefold() == address.casefold() for p in existing):
        raise ValueError('This candidate and address are already in the shortlist')
    if len(existing) >= 30:
        raise ValueError('This journey supports up to 30 candidates')
    return dict(id=secrets.token_hex(8), name=name, address=address, url=url,
                phone=text(raw.get('phone'), 50), kind='User-added candidate · needs confirmation',
                demo=False, services=[], languages=[], cash={}, coverage={}, rating=None,
                checked_on=checked_date(raw.get('checked_on')), source_note=source,
                user_entered=True, answers=[])


def save_answer(provider, person, raw):
    key = raw.get('key')
    if key not in ANSWER_KEYS:
        raise ValueError('Choose an availability, language or referral question')
    result = raw.get('result')
    if result not in ('yes', 'no', 'unknown'):
        raise ValueError('Choose yes, no or still unknown')
    source, answer = text(raw.get('source'), 500), text(raw.get('answer'), 1500)
    if not source or not answer:
        raise ValueError('Record the reply and who or what supplied it')
    entry = dict(key=key, result=result, answer=answer, source=source,
                 checked_on=checked_date(raw.get('checked_on')), service=person['service'],
                 plan=(person.get('plan') or {}).get('name', '') if key in ('referral', 'referral_action') else '',
                 language=person.get('language', '') if key == 'language' else '',
                 user_entered=True)
    if len(provider.get('answers', [])) >= 100:
        raise ValueError('This candidate has reached its answer-history limit')
    provider.setdefault('answers', []).append(entry)
    return entry


def current_answers(provider, person):
    """Only matching answers count; stale and superseded reports remain in history."""
    latest = {}
    for entry in provider.get('answers', []):
        if entry.get('service') != person['service']:
            continue
        if entry['key'] in ('referral', 'referral_action') and entry.get('plan') != (person.get('plan') or {}).get('name', ''):
            continue
        if entry['key'] == 'language' and entry.get('language') != person.get('language', ''):
            continue
        old = latest.get(entry['key'])
        if old is None or entry['checked_on'] >= old['checked_on']:
            latest[entry['key']] = entry
    return {key: dict(entry, stale=(date.today() - date.fromisoformat(entry['checked_on'])).days > 30)
            for key, entry in latest.items()}


def next_action(case, rows):
    if case.get('status') == 'attended':
        return 'Visit recorded; review follow-ups on your health profile.'
    if case.get('status') == 'booked':
        return 'Review appointment details and bring your preparation script.'
    for row in rows:
        if row.get('unavailable'):
            continue
        questions = row['confirmation']
        if questions:
            first = next((q for key in ('availability', 'service', 'insurance', 'referral_action', 'cash', 'language', 'referral') for q in questions if q['key'] == key), questions[0])
            return f"Next with {row['provider']['name']}: {first['question']}"
    return 'Review your evidence, then contact your chosen provider to book.'
