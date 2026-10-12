"""Audit ledger with hash chain"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict


def _compute_hash(payload: dict) -> str:
    h = hashlib.sha256()
    h.update(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def append(entry: dict, path: Path) -> Dict:
    """Append entry to ledger with hash chain. Returns full entry with hashes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    prev_hash = "0" * 64
    if path.exists():
        # read last line
        try:
            content = path.read_text(encoding="utf-8").rstrip()
            if content:
                lines = content.splitlines()
                if lines:
                    last = json.loads(lines[-1])
                    prev_hash = last.get("hash", "0" * 64)
        except Exception:
            prev_hash = "0" * 64
    rec = dict(entry)
    if "reason" not in rec:
        rec["reason"] = ""
    rec["prev_hash"] = prev_hash
    # compute hash from rec without hash field
    to_hash = dict(rec)
    if "hash" in to_hash:
        to_hash.pop("hash")
    rec["hash"] = _compute_hash(to_hash)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return rec


def verify(path: Path) -> bool:
    """Verify ledger file integrity."""
    if not path.exists():
        return True
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return False
    if not content.strip():
        return True
    lines = content.splitlines()
    prev_hash = "0" * 64
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            return False
        if not rec.get("reason"):
            return False
        if rec.get("prev_hash") != prev_hash:
            return False
        to_hash = dict(rec)
        h = to_hash.pop("hash", None)
        calc = _compute_hash(to_hash)
        if h != calc:
            return False
        prev_hash = calc
    return True
