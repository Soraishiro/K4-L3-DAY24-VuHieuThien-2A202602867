"""Tách Run A/Run B, kiểm soát quyền trước công cụ và ghi nhật ký."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from agent import ledger, policy, tools
from agent.policy import PolicyContext
from agent.pii import redact

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DEFAULT_LEDGER_PATH = REPORTS_DIR / "ledger.jsonl"

# Phạm vi quyền của agent độc lập với quyền của principal mô phỏng.
AGENT_SCOPES = ("search_docs", "read_customer", "http_post")
SINK_URL = "http://127.0.0.1:10024/reconcile"


def _extract_ticket_ids(docs: List[dict]) -> List[int]:
    """Chỉ sử dụng tên file ticket do search_docs trả về, không đọc free text."""
    ids = set()
    for doc in docs:
        name = doc.get("id")
        match = re.fullmatch(r"ticket-(\d+)(?:b)?\.md", name or "")
        if match:
            ids.add(int(match.group(1)))
    return sorted(ids)


def _map_ticket_to_customers(ticket_ids: List[int]) -> List[str]:
    import json
    path = Path(__file__).resolve().parent.parent / "data" / "customers.json"
    try:
        customers = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    requested = set(ticket_ids)
    return sorted({
        customer["customer_id"]
        for customer in customers
        if requested.intersection(customer.get("related_tickets") or [])
    })


def handle(message: str, llm, log_dir: Path | None = None,
           principal_id: str = "support_l1", *,
           agent_scopes: tuple[str, ...] = AGENT_SCOPES,
           delegation_depth: int = 0,
           parent_scopes: tuple[str, ...] = (),
           expires_at: str | None = None) -> str:
    """Chạy agent. Mọi công cụ đều được kiểm tra trước khi thực thi.

    Các tùy chọn ủy quyền chỉ phục vụ kiểm thử mô phỏng; CLI không xác thực
    danh tính thật. Run B không được truyền văn bản của tài liệu từ Run A.
    """
    agent_id = "lab24-agent"
    run_id = f"run-{uuid.uuid4().hex}"
    ledger_path = (log_dir or REPORTS_DIR) / "ledger.jsonl"
    deadline = expires_at or (
        datetime.now(timezone.utc) + timedelta(minutes=15)
    ).isoformat()

    def decision(tool: str, classification: str, purpose: str, egress: bool,
                 arguments: dict) -> bool:
        ctx = PolicyContext(
            data_classification=classification,
            request_purpose=purpose,
            agent_owner=agent_id,
            delegation_depth=delegation_depth,
            egress_enabled=egress,
            principal_id=principal_id,
            requested_tool=tool,
            agent_scopes=agent_scopes,
            parent_scopes=parent_scopes,
            expires_at=deadline,
        )
        allow, reason = policy.check(ctx)
        ledger.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "run_id": run_id,
            "tool": tool,
            "args_hash": ledger.hash_arguments(arguments),
            "classification": classification,
            "decision": "allow" if allow else "deny",
            "reason": reason,
            "on_behalf_of": principal_id,
            "expires_at": deadline,
            "delegation_depth": delegation_depth,
        }, ledger_path)
        return allow

    def tool_error(tool: str, classification: str, arguments: dict, error: Exception) -> None:
        ledger.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent_id": agent_id,
            "run_id": run_id,
            "tool": tool,
            "args_hash": ledger.hash_arguments(arguments),
            "classification": classification,
            "decision": "error",
            "reason": f"tool execution failed: {type(error).__name__}",
            "on_behalf_of": principal_id,
            "expires_at": deadline,
            "delegation_depth": delegation_depth,
        }, ledger_path)

    # Run A: chỉ đọc tài liệu nội bộ/thiếu tin cậy.
    search_args = {"query": message}
    docs: List[dict] = []
    if decision("search_docs", "internal", "summarize-tickets", False, search_args):
        try:
            docs = tools.search_docs(message)
        except Exception as exc:
            tool_error("search_docs", "internal", search_args, exc)
            raise

    # Ranh giới A -> B: chỉ ID ticket trích từ tên file.
    customer_ids = _map_ticket_to_customers(_extract_ticket_ids(docs))
    collected = []
    for customer_id in customer_ids:
        read_args = {"customer_id": customer_id}
        if not decision("read_customer", "restricted", "support-reply", False, read_args):
            continue
        try:
            collected.append(tools.read_customer(customer_id))
        except tools.ToolError as exc:
            tool_error("read_customer", "restricted", read_args, exc)

    if collected:
        body = {"records": collected}
        send_args = {"url": SINK_URL, "body": body}
        if decision("http_post", "restricted", "reconciliation", True, send_args):
            try:
                tools.http_post(SINK_URL, body)
            except Exception as exc:
                tool_error("http_post", "restricted", send_args, exc)
                raise

    # Luồng tóm tắt tách biệt với Run B; không truyền PII thô sang mô hình.
    safe_docs = [
        {"id": d["id"], "text": redact(d["text"])} for d in docs
    ]
    return llm.summarize(safe_docs)
