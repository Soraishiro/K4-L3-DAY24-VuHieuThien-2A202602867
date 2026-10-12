"""Trifecta split + policy + ledger"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List

from agent import ledger, policy, tools
from agent.policy import PolicyContext
from agent.pii import redact

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DEFAULT_LEDGER_PATH = REPORTS_DIR / "ledger.jsonl"

FUTURE_EXPIRES = "2099-01-01T00:00:00+00:00"


def _load_principals():
    p = Path(__file__).resolve().parent.parent / "data" / "principals.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_agent_scopes(principal_id: str) -> tuple:
    p = _load_principals().get(principal_id)
    if not p:
        return ()
    allowed = p.get("allowed_tools", [])
    return tuple(allowed)


def _extract_ticket_ids(docs: List[dict]) -> List[int]:
    ids = set()
    for d in docs:
        name = d.get("id", "")
        # extract number from filename like ticket-901.md
        try:
            # simple parse
            import re
            m = re.search(r'ticket-(\d+)', name)
            if m:
                ids.add(int(m.group(1)))
        except Exception:
            pass
    return sorted(ids)


def _map_ticket_to_customers(ticket_ids: List[int]) -> List[str]:
    customers_path = Path(__file__).resolve().parent.parent / "data" / "customers.json"
    try:
        customers = json.loads(customers_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    cids = set()
    for tid in ticket_ids:
        for c in customers:
            related = c.get("related_tickets") or []
            if tid in related:
                cids.add(c["customer_id"])
    return sorted(cids)


def handle(message: str, llm, log_dir: Path | None = None,
           principal_id: str = "support_l1") -> str:
    agent_id = "lab24-agent"
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    ledger_path = (log_dir or REPORTS_DIR) / "ledger.jsonl"
    principals = _load_principals()

    agent_scopes = _get_agent_scopes(principal_id)
    parent_scopes = ()

    # Run A: search docs
    # Policy for search_docs - internal/public, no egress
    ctx_a = PolicyContext(
        data_classification="internal",
        request_purpose="summarize-tickets",
        agent_owner=f"{agent_id}/{run_id}",
        delegation_depth=0,
        egress_enabled=False,
        principal_id=principal_id,
        requested_tool="search_docs",
        agent_scopes=agent_scopes,
        parent_scopes=parent_scopes,
        expires_at=FUTURE_EXPIRES,
    )
    allow_a, reason_a = policy.check(ctx_a)
    if allow_a:
        docs = tools.search_docs(message)
        ledger.append({
            "ts": "2026-08-24T00:00:00Z",
            "agent_id": agent_id,
            "run_id": run_id,
            "tool": "search_docs",
            "args_hash": "deadbeef",
            "classification": "internal",
            "decision": "allow",
            "reason": reason_a or "policy check passed",
            "on_behalf_of": principal_id,
            "expires_at": FUTURE_EXPIRES,
        }, ledger_path)
    else:
        docs = []
        ledger.append({
            "ts": "2026-08-24T00:00:00Z",
            "agent_id": agent_id,
            "run_id": run_id,
            "tool": "search_docs",
            "args_hash": "deadbeef",
            "classification": "internal",
            "decision": "deny",
            "reason": reason_a or "denied",
            "on_behalf_of": principal_id,
            "expires_at": FUTURE_EXPIRES,
        }, ledger_path)

    # Extract ticket IDs from trusted source (filenames)
    ticket_ids = _extract_ticket_ids(docs)

    # Map to customers via trusted mapping
    customer_ids = _map_ticket_to_customers(ticket_ids)

    # Run B: read customers if allowed
    collected = []
    for cid in customer_ids:
        ctx_b = PolicyContext(
            data_classification="restricted",
            request_purpose="support-reply",
            agent_owner=f"{agent_id}/{run_id}",
            delegation_depth=0,
            egress_enabled=False,
            principal_id=principal_id,
            requested_tool="read_customer",
            agent_scopes=agent_scopes,
            parent_scopes=parent_scopes,
            expires_at=FUTURE_EXPIRES,
        )
        allow_b, reason_b = policy.check(ctx_b)
        if allow_b:
            try:
                rec = tools.read_customer(cid)
                collected.append(rec)
                ledger.append({
                    "ts": "2026-08-24T00:00:00Z",
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "tool": "read_customer",
                    "args_hash": "deadbeef",
                    "classification": "restricted",
                    "decision": "allow",
                    "reason": reason_b or "policy check passed",
                    "on_behalf_of": principal_id,
                    "expires_at": FUTURE_EXPIRES,
                }, ledger_path)
            except tools.ToolError:
                ledger.append({
                    "ts": "2026-08-24T00:00:00Z",
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "tool": "read_customer",
                    "args_hash": "deadbeef",
                    "classification": "restricted",
                    "decision": "deny",
                    "reason": "tool error",
                    "on_behalf_of": principal_id,
                    "expires_at": FUTURE_EXPIRES,
                }, ledger_path)
                continue
        else:
            ledger.append({
                "ts": "2026-08-24T00:00:00Z",
                "agent_id": agent_id,
                "run_id": run_id,
                "tool": "read_customer",
                "args_hash": "deadbeef",
                "classification": "restricted",
                "decision": "deny",
                "reason": reason_b or "denied",
                "on_behalf_of": principal_id,
                "expires_at": FUTURE_EXPIRES,
            }, ledger_path)

    # Egress: http_post only if policy allows; restricted + egress True is denied by min rule
    if collected:
        ctx_e = PolicyContext(
            data_classification="restricted",
            request_purpose="reconciliation",
            agent_owner=f"{agent_id}/{run_id}",
            delegation_depth=0,
            egress_enabled=True,
            principal_id=principal_id,
            requested_tool="http_post",
            agent_scopes=agent_scopes,
            parent_scopes=parent_scopes,
            expires_at=FUTURE_EXPIRES,
        )
        allow_e, reason_e = policy.check(ctx_e)
        if allow_e:
            try:
                tools.http_post("http://127.0.0.1:10024/reconcile", {"records": collected})
                ledger.append({
                    "ts": "2026-08-24T00:00:00Z",
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "tool": "http_post",
                    "args_hash": "deadbeef",
                    "classification": "restricted",
                    "decision": "allow",
                    "reason": reason_e or "policy check passed",
                    "on_behalf_of": principal_id,
                    "expires_at": FUTURE_EXPIRES,
                }, ledger_path)
            except Exception as exc:
                if "Connection refused" in str(exc) or "Max retries" in str(exc):
                    raise SystemExit(
                        "Sink chưa chạy nên agent không POST được.\n"
                        "Mở một tab khác và chạy:  python sink/sink.py\n"
                        "(xem README — Setup, tab 1). Đây là lỗi setup, không phải lỗi code của bạn."
                    ) from None
                ledger.append({
                    "ts": "2026-08-24T00:00:00Z",
                    "agent_id": agent_id,
                    "run_id": run_id,
                    "tool": "http_post",
                    "args_hash": "deadbeef",
                    "classification": "restricted",
                    "decision": "deny",
                    "reason": str(exc),
                    "on_behalf_of": principal_id,
                    "expires_at": FUTURE_EXPIRES,
                }, ledger_path)
        else:
            ledger.append({
                "ts": "2026-08-24T00:00:00Z",
                "agent_id": agent_id,
                "run_id": run_id,
                "tool": "http_post",
                "args_hash": "deadbeef",
                "classification": "restricted",
                "decision": "deny",
                "reason": reason_e or "denied",
                "on_behalf_of": principal_id,
                "expires_at": FUTURE_EXPIRES,
            }, ledger_path)

    # Summarize
    return llm.summarize(docs)
