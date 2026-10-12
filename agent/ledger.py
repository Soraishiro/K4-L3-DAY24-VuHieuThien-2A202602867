"""Nhật ký quyết định có chuỗi hash, trong phạm vi bài lab."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict


def _compute_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def hash_arguments(arguments: dict) -> str:
    """Băm tham số thật; không lưu tham số hoặc PII dưới dạng văn bản trong ledger."""
    raw = json.dumps(arguments, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def append(entry: dict, path: Path) -> Dict:
    """Ghi một mục mới. Không nối tiếp nhật ký đã hỏng."""
    path.parent.mkdir(parents=True, exist_ok=True)
    prev_hash = "0" * 64
    if path.exists() and path.stat().st_size:
        if not verify(path):
            raise ValueError("ledger integrity failed; refusing to append")
        last_line = path.read_text(encoding="utf-8").splitlines()[-1]
        prev_hash = json.loads(last_line)["hash"]

    rec = dict(entry)
    rec.setdefault("reason", "")
    rec["prev_hash"] = prev_hash
    rec.pop("hash", None)
    rec["hash"] = _compute_hash(rec)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return rec


def verify(path: Path) -> bool:
    """Kiểm tra các mục đã có; file thiếu/rỗng không chứng minh đã ghi nhật ký."""
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            return False
        prev_hash = "0" * 64
        for line in content.splitlines():
            if not line.strip():
                return False
            rec = json.loads(line)
            if not isinstance(rec, dict) or not rec.get("reason"):
                return False
            if rec.get("prev_hash") != prev_hash:
                return False
            to_hash = dict(rec)
            actual = to_hash.pop("hash", None)
            calculated = _compute_hash(to_hash)
            if actual != calculated:
                return False
            prev_hash = actual
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False
