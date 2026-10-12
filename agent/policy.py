"""Policy enforcement point for tool calls"""
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
    except Exception:
        return None


def _is_expired(expires_at: str) -> bool:
    if not expires_at:
        return False
    try:
        dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt < datetime.now(timezone.utc)
    except Exception:
        return True


def check(context: PolicyContext) -> Tuple[bool, str]:
    # Minimum deny rule: restricted + egress
    if context.data_classification == "restricted" and context.egress_enabled:
        return False, "restricted data with egress is not permitted"

    # OBO checks if principal specified
    if context.principal_id:
        p = _load_principal(context.principal_id)
        if p is None:
            return False, f"unknown principal: {context.principal_id}"
        allowed_tools = set(p.get("allowed_tools", []))
        purposes = set(p.get("purposes", []))
        # build effective scopes
        effective = set(context.agent_scopes or [])
        effective &= allowed_tools
        if context.delegation_depth > 0:
            effective &= set(context.parent_scopes or [])
        if not effective:
            return False, "no effective scope for requested tool"
        if context.requested_tool and context.requested_tool not in effective:
            return False, f"tool not allowed for principal {context.principal_id}"
        if context.request_purpose and context.request_purpose not in purposes:
            return False, f"purpose not allowed for principal {context.principal_id}"
        if _is_expired(context.expires_at):
            return False, "principal/session expired"

    return True, "policy check passed"
