"""Hồi quy cho các lỗ hổng còn thiếu trong bộ test bắt buộc (không sửa test gốc)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import ledger, runner
from agent.llm import find_injection, MockLLM
from agent.policy import PolicyContext, check


ROOT = Path(__file__).resolve().parent.parent


def _context(**changes):
    data = dict(
        data_classification="internal",
        request_purpose="summarize-tickets",
        agent_owner="lab24-agent",
        delegation_depth=0,
        egress_enabled=False,
        principal_id="dpo",
        requested_tool="search_docs",
        agent_scopes=("search_docs", "read_customer"),
        parent_scopes=(),
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    )
    data.update(changes)
    return PolicyContext(**data)


@pytest.mark.parametrize("field,value", [
    ("principal_id", ""), ("requested_tool", ""), ("request_purpose", ""),
    ("agent_owner", ""), ("expires_at", ""),
    ("expires_at", "2099-01-01T00:00:00"), ("delegation_depth", -1),
])
def test_missing_or_invalid_authority_is_denied(field, value):
    allowed, reason = check(_context(**{field: value}))
    assert not allowed and reason


def test_agent_scopes_are_independent():
    allowed, reason = check(_context(
        data_classification="restricted",
        request_purpose="support-reply",
        requested_tool="read_customer",
        agent_scopes=("search_docs",),
    ))
    assert not allowed and reason


def test_delegation_rejects_missing_parent_scope():
    allowed, reason = check(_context(
        delegation_depth=1, parent_scopes=(),
        data_classification="restricted", request_purpose="support-reply",
        requested_tool="read_customer",
    ))
    assert not allowed and reason


def test_split_payload_requires_both_documents():
    a = (ROOT / "corpus/ticket-904.md").read_text(encoding="utf-8")
    b = (ROOT / "corpus/ticket-904b.md").read_text(encoding="utf-8")
    assert find_injection(a) is None
    assert find_injection(b) is None
    merged = find_injection(a + "\n\n" + b)
    assert merged is not None and "KH-000999" in merged.customer_ids


def test_second_lure_has_invisible_characters():
    text = (ROOT / "corpus/ticket-902.md").read_text(encoding="utf-8")
    assert "\u200b" in text and find_injection(text) is not None


def test_ledger_uses_real_call_hash_and_timestamp(tmp_path):
    path = tmp_path / "ledger.jsonl"
    runner.handle("ticket", MockLLM(), log_dir=tmp_path, principal_id="dpo")
    entries = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert ledger.verify(path)
    assert all(len(x["args_hash"]) == 64 for x in entries)
    assert all(x["args_hash"] != "deadbeef" for x in entries)
    assert all(datetime.fromisoformat(x["ts"]).tzinfo is not None for x in entries)
    assert len(set(x["args_hash"] for x in entries if x["tool"] == "read_customer")) > 1


def test_ledger_fail_closed_on_corruption(tmp_path):
    path = tmp_path / "ledger.jsonl"
    assert not ledger.verify(path)
    ledger.append({"reason": "first", "tool": "search_docs"}, path)
    path.write_text(path.read_text() + "not valid json\n", encoding="utf-8")
    assert not ledger.verify(path)
    with pytest.raises(ValueError, match="integrity"):
        ledger.append({"reason": "second"}, path)


def test_runner_delegated_parent_cannot_read(tmp_path, monkeypatch):
    from agent import tools
    seen = []
    monkeypatch.setattr(tools, "read_customer", lambda customer_id: seen.append(customer_id))
    runner.handle(
        "Tổng hợp các ticket còn mở tuần này", MockLLM(),
        log_dir=tmp_path, principal_id="dpo",
        delegation_depth=1, parent_scopes=("search_docs",),
    )
    assert not seen
    entries = [json.loads(x) for x in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert any(x["tool"] == "read_customer" and x["decision"] == "deny" for x in entries)


def test_summary_redacts_pii(tmp_path, monkeypatch):
    from agent import tools
    class CaptureLLM:
        def summarize(self, docs):
            assert all("0912345678" not in d["text"] for d in docs)
            assert any("[REDACTED_VN_PHONE]" in d["text"] for d in docs)
            return "ok"
    monkeypatch.setattr(tools, "search_docs",
                        lambda query: [{"id": "ticket-101.md", "text": "SĐT 0912345678"}])
    assert runner.handle("ticket", CaptureLLM(), log_dir=tmp_path) == "ok"
