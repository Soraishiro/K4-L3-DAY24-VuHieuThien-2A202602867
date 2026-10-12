# Compliance mapping (evidence tham khảo)

## Luật 91/2025 (Luật Bảo vệ dữ liệu cá nhân)
- Nguyên tắc cần thiết, hợp lý, mục đích rõ ràng: lab chỉ dùng dữ liệu tổng hợp (synthetic), giới hạn mục đích giáo dục/lab.
- Evidence: `data/customers.json` (synthetic), `reports/attack-before.log` (bằng chứng rò rỉ trước contain), `reports/attack-after.log` (rỗng sau contain), `agent/pii.py` (PII gate), `agent/policy.py` (PEP).
- Ghi chú: phân biệt rõ mock với hệ thống thật; không dùng dữ liệu cá nhân thật.

## NĐ 356/2025 (Nghị định hướng dẫn)
- Kiểm soát truy cập, phân quyền (OBO): principal từ `data/principals.json`, policy enforce trước tool call, ledger audit.
- Evidence: `tests/test_obo.py` pass, `reports/ledger.jsonl` (on_behalf_of, reason, decision).
- Phân biệt mock (giả lập) vs auth production.

## Luật AI 134/2025 (Luật Công nghệ AI)
- An toàn, đáng tin cậy, giảm rủi ro: containment (trifecta split) ngăn agent đọc dữ liệu từ chỉ thị untrusted; egress bị chặn khi restricted.
- Evidence: `tests/test_split.py`, `tests/test_injection.py` (PII không ra sink sau contain).
- Mock LLM, reproducible, không gọi model thật để chấm.

## OWASP ASI01/03/04 (Agentic Security)
- ASI01 (Tool use & function calling): enforce policy trước tool, least privilege.
- ASI03 (Memory/Context poisoning / indirect prompt injection): split A/B, không truyền free text untrusted sang Run B (map qua ticket_id → related_tickets).
- ASI04 (Identity & delegation/OBO): `principal_id`, `agent_scopes`, `parent_scopes`, `delegation_depth`, `expires_at` kiểm tra và ghi ledger.
- Evidence: runner split, policy checks, ledger với đầy đủ metadata.
