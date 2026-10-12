"""Chốt kiểm soát quyền trước khi gọi công cụ (OBO, mô phỏng trong lab)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class PolicyContext:
    data_classification: str
    request_purpose: str
    agent_owner: str
    delegation_depth: int
    egress_enabled: bool
    principal_id: str = ""
    requested_tool: str = ""
    agent_scopes: tuple[str, ...] = ()
    parent_scopes: tuple[str, ...] = ()
    expires_at: str = ""


_PRINCIPALS_FILE = Path(__file__).resolve().parent.parent / "data" / "principals.json"


def _load_principal(pid: str) -> dict | None:
    try:
        data = json.loads(_PRINCIPALS_FILE.read_text(encoding="utf-8"))
        return data.get(pid)
    except (OSError, ValueError):
        return None


def _is_expired(expires_at: str) -> bool:
    if not expires_at:
        return True
    try:
        dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        # Thiếu múi giờ là không đủ bằng chứng về TTL.
        if dt.tzinfo is None:
            return True
        return dt.astimezone(timezone.utc) <= datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return True


def check(context: PolicyContext) -> Tuple[bool, str]:
    """Trả (allow, reason) và từ chối khi thiếu thông tin quyền.

    Lệnh cấm gửi dữ liệu restricted được áp dụng trước mọi kiểm tra khác.
    Đây là principal mô phỏng, không phải xác thực danh tính production.
    """
    if context.data_classification == "restricted" and context.egress_enabled:
        return False, "restricted data with egress is not permitted"
    if not context.principal_id:
        return False, "missing principal"
    if not context.requested_tool:
        return False, "missing requested tool"
    if not context.request_purpose:
        return False, "missing request purpose"
    if not context.agent_owner:
        return False, "missing agent owner"
    if context.delegation_depth < 0:
        return False, "invalid delegation depth"
    if _is_expired(context.expires_at):
        return False, "session missing expiration or expired"

    principal = _load_principal(context.principal_id)
    if principal is None:
        return False, f"unknown principal: {context.principal_id}"

    if context.request_purpose not in principal.get("purposes", []):
        return False, f"purpose not allowed for principal {context.principal_id}"

    effective = set(principal.get("allowed_tools", []))
    effective &= set(context.agent_scopes)
    if context.delegation_depth > 0:
        effective &= set(context.parent_scopes)

    if context.requested_tool not in effective:
        return False, f"tool not allowed by effective scopes for {context.principal_id}"

    return True, "policy check passed"
