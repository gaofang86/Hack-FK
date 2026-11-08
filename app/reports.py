"""Local text-PDF lab import. No OCR, interpretation, inferred dates or diagnoses."""
import base64
import hashlib
import re
from datetime import date
from .sbc import pdf_text
from .navigation import text


def parse_upload(raw):
    encoded = raw.get('pdf_base64', '')
    if not isinstance(encoded, str) or len(encoded) > 8_000_000:
        raise ValueError('Choose a text PDF under 6 MB')
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise ValueError('Invalid PDF upload')
    if not content.startswith(b'%PDF-') or len(content) > 6_000_000:
        raise ValueError('Choose a PDF under 6 MB')
    try:
        extracted = pdf_text(content)
    except Exception:
        raise ValueError('Could not read this PDF. This importer supports text PDFs, not scanned images.') from None
    if len(extracted) > 200_000:
        raise ValueError('Report text is too large')
    rows = []
    # Supported original lab portal text export: name/value followed by reported range.
    for match in re.finditer(r'(?m)^([^\n]{1,100}?) ([<>]?\d+(?:\.\d+)?(?: [^\n]+?)?) \d{2}\nNormal: ([^\n]+)\nFinal', extracted):
        name, result, reference = match.groups()
        flag = 'Low' if reference.endswith(' Low') else 'High' if reference.endswith(' High') else ''
        if flag:
            reference = reference[:-(len(flag) + 1)]
        rows.append(dict(name=name, result=result, reference=reference, flag=flag, evidence=match.group(0)))
    # FirstVisit demo copy: text table with one extracted field per line.
    if not rows and 'Source-based demo copy' in extracted:
        for match in re.finditer(r'(?m)^([A-Za-z][^\n]{0,100})\n([<>]?\d+(?:\.\d+)?[^\n]*)\n([^\n]+)\n(Low|High|-)\n', extracted):
            name, result, reference, flag = match.groups()
            rows.append(dict(name=name, result=result, reference=reference, flag='' if flag == '-' else flag, evidence=match.group(0)))
    if not rows:
        raise ValueError('No supported lab rows found. Keep the report and add your goal manually; report import is optional.')
    if len(rows) > 200:
        raise ValueError('This report has too many rows')
    return dict(label=text(raw.get('file_name') or 'Lab report', 160), rows=rows,
                source=dict(sha256=hashlib.sha256(content).hexdigest(), reviewed_on='', imported_on=date.today().isoformat()),
                scope='Reported facts only; review each value. No medical interpretation. Original PDF is not retained.')


def reviewed(preview, raw, ident):
    if raw.get('confirmed') is not True:
        raise ValueError('Review the report and explicitly confirm it')
    values = raw.get('rows')
    if not isinstance(values, list) or len(values) != len(preview['rows']):
        raise ValueError('Review every extracted row')
    rows = []
    for original, value in zip(preview['rows'], values):
        if not isinstance(value, dict):
            raise ValueError('Invalid report row')
        if value.get('omit') is True:
            continue
        row = {key: text(value.get(key), 160) for key in ('name', 'result', 'reference', 'flag')}
        if not row['name'] or not row['result'] or row['flag'] not in ('', 'Low', 'High'):
            raise ValueError('Review the test name, result and source flag')
        rows.append(dict(row, evidence=original['evidence'], original={k: original[k] for k in row}, user_reviewed=True))
    if not rows:
        raise ValueError('Keep at least one report row')
    return dict(id=ident, label=text(raw.get('label') or preview['label'], 160), rows=rows,
                source=dict(preview['source'], reviewed_on=date.today().isoformat()))
