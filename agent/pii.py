"""PII detection and redaction for Vietnamese PII"""
from __future__ import annotations

import re
from typing import List, Dict


def detect(text: str) -> List[Dict]:
    """Detect VN PII entities."""
    entities = []
    bank_spans = []

    # VN_BANK_ACCOUNT: 8-16 digits after context keywords (highest priority)
    for m in re.finditer(r'(?:STK|stk|số tài khoản|so tai khoan|tài khoản|tai khoan)\s*(\d{8,16})\b', text, re.I):
        s, e = m.start(1), m.end(1)
        bank_spans.append((s, e))
        entities.append({"type": "VN_BANK_ACCOUNT", "start": s, "end": e})

    # VN_BANK_ACCOUNT: standalone 13-16 digit numbers (not overlapping with keyword matches)
    for m in re.finditer(r'(\d{13,16})\b', text):
        s, e = m.start(1), m.end(1)
        if any(s < bs[1] and bs[0] < e for bs in bank_spans):
            continue
        dup = any(o['start'] == s and o['end'] == e and o['type'] == "VN_BANK_ACCOUNT" for o in entities)
        if not dup:
            entities.append({"type": "VN_BANK_ACCOUNT", "start": s, "end": e})
            bank_spans.append((s, e))

    # VN_CCCD: 12 consecutive digits (not overlapping with bank accounts)
    for m in re.finditer(r'\b(\d{12})\b', text):
        s, e = m.start(1), m.end(1)
        if any(s < bs[1] and bs[0] < e for bs in bank_spans):
            continue
        entities.append({"type": "VN_CCCD", "start": s, "end": e})

    # VN_PHONE: 10-digit number starting with 0 (not overlapping with bank/CCCD)
    cccd_spans = [(e['start'], e['end']) for e in entities if e['type'] == 'VN_CCCD']
    occupied = bank_spans + cccd_spans
    for m in re.finditer(r'(?:[^\d]|^)(0\d{9})\b', text):
        s, e = m.start(1), m.end(1)
        if any(s < os[1] and os[0] < e for os in occupied):
            continue
        entities.append({"type": "VN_PHONE", "start": s, "end": e})

    # EMAIL
    for m in re.finditer(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b', text):
        entities.append({"type": "EMAIL", "start": m.start(1), "end": m.end(1)})

    entities = sorted(entities, key=lambda x: (x['start'], x['end'], x['type']))
    out = []
    for ent in entities:
        if not any(o['start']==ent['start'] and o['end']==ent['end'] and o['type']==ent['type'] for o in out):
            out.append(ent)
    return out


def redact(text: str) -> str:
    """Redact detected PII by replacing with [REDACTED_<TYPE>] from end to start."""
    ents = detect(text)
    result = text
    for ent in sorted(ents, key=lambda x: x['start'], reverse=True):
        t = ent['type']
        result = result[:ent['start']] + f'[REDACTED_{t}]' + result[ent['end']:]
    return result
