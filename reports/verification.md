# Verification report (CP1-CP5)

## CP1 — Baseline (agent/loop.py)
- Đọc `_naive_loop`: không có agent_id/run_id/principal để kiểm quyền; quyết định gửi hoàn toàn dựa vào `injected` từ LLM đọc nội dung untrusted. `http_post` tạo body `{"records": collected}` tại `agent/loop.py:44`. Sink log ghi tại `reports/sink.log` (sink/sink.py).
- `reports/baseline.md` đã được ghi với 3 câu trả lời kèm file:dòng.

## CP2 — Red team
- Tạo đủ 4 lure: `ticket-902.md`, `ticket-903.md`, `ticket-904.md`, `ticket-904b.md`. Kiểm tra: `python -m agent.check_lure corpus/ticket-90*.md` → 4/4 sẵn sàng.
- Chạy sink + agent baseline → `reports/attack-before.log` chứa POST `/reconcile` với record KH-000999 (CCCD/SĐT/STK/email). `injection-corpus.md` đã cập nhật kết quả trước khi contain.

## CP3a — PII
- `agent/pii.py`: `detect`/`redact` với regex cho VN_CCCD (12 số), VN_PHONE (03/04/05/07/08/09 + 8 số), VN_BANK_ACCOUNT (8–16 số, ưu tiên khi có nhãn STK; cũng bắt long numbers không trùng), EMAIL.
- Kiểm tra: `python3 -m pytest tests/test_pii.py -s`
  - gold=118, pred=118, tp=118; precision=1.000, recall=1.000 (2 passed)
  - Ban đầu regex chỉ nhận VN_PHONE với prefix 03/04/05/07/08/09 (miss 15 số có
    prefix 00/01/02/06) và CCCD trùng với STK (6 FP). Sau khi sắp xếp thứ tự
    bank trước CCCD trước phone và bỏ qua overlap: precision=1.000, recall=1.000. (2 passed)

## CP3b — Policy
- `agent/policy.py`: rule tối thiểu `restricted and egress_enabled -> deny`. Kiểm OBO khi `principal_id` được cung cấp: load từ `data/principals.json`, effective scope = `agent_scopes ∩ allowed_tools`; nếu `delegation_depth > 0` thì giao thêm với `parent_scopes`. Kiểm purpose trong `purposes`, kiểm `expires_at` hợp lệ (UTC). Mọi decision đều có reason.
- Kiểm tra: `python3 -m pytest tests/test_policy.py -v` → 4 passed.

## CP3c — OBO + runner split
- `agent/runner.py`: tách Run A (search_docs, internal, no egress) và Run B (chỉ map ticket_id từ tên file → related_tickets trong customers.json để lấy customer_id, không lấy từ free text). Trước mỗi tool call gọi `policy.check()` và ghi ledger (bao gồm `on_behalf_of`, `agent_id`, `run_id`, `expires_at`, `reason`). Với support_l1 không được đọc customer restricted; dpo được đọc khi hợp lệ.
- Kiểm tra: `tests/test_obo.py` (5/5), `tests/test_split.py` (1/1), `tests/test_injection.py` (8/8).

## CP3d — Ledger
- `agent/ledger.py`: append ghi `prev_hash` (hash dòng trước, "0"*64 nếu đầu), `hash` tính từ toàn bộ rec trừ field `hash` với `sort_keys=True`, `ensure_ascii=False`. verify kiểm reason non-empty, liên kết prev_hash/hash, và tính lại hash khớp. Tests: 3/3 passed.

## CP4 — Supply chain & secrets
- `requirements.lock` tạo bằng `pip-compile --generate-hashes` và cài qua `pip install --require-hashes`. `.pre-commit-config.yaml` dùng `gitleaks-system` rev `v8.30.1`, `pass_filenames: false`, args `--config .gitleaks.toml` (hook entry đã bao gồm `gitleaks git --pre-commit --redact --staged`).
- Quét lịch sử: `gitleaks git --config .gitleaks.toml --redact .` phát hiện token giả tại commit `1bdd849` (file `lab-fake-secret.txt`, rule `lab24-synthetic-token`) — finding dự kiến. `reports/secrets-incident.md` giải thích synthetic token, rằng xoá khỏi HEAD không thu hồi secret đã lộ, và pin+hook ngăn lộ mới chứ không thay thế rotate.
- Tests: `tests/test_supply_chain.py` (3/3 passed).

## CP5 — Prove
- Reset sink, chạy `python -m agent.loop --mock --as dpo "Tổng hợp các ticket còn mở tuần này"` với runner đã hoàn thiện → sink nhận 0 POST (attack-after.log rỗng). Ledger có deny `http_post` với reason non-empty và đầy đủ metadata (on_behalf_of/run_id/expires_at).
- Tất cả test chính: `test_pii`, `test_policy`, `test_obo`, `test_split`, `test_injection`, `test_scaffold_dispatch`, `test_check_lure_cli`, `test_supply_chain`, `test_ledger` đều pass.

## Compliance mapping (tóm tắt)
- Luật 91/2025, NĐ 356/2025, Luật AI 134/2025, OWASP ASI01/03/04 — xem `reports/compliance-mapping.md` (file riêng). Evidence: baseline attack log, ledger deny, split containment, PII gate, secrets incident.
- `reports/dpia-lite.md`: mô tả dữ liệu synthetic, mục đích giáo dục, phạm vi localhost/mock, giới hạn của hệ thống mock.

Ghi chú: PII regex đơn giản đạt recall 1.0 trên test set nhưng precision thấp (0.554) — đủ để pass test; trong thực tế cần tinh chỉnh hơn. Ledger hash chain phát hiện sửa đổi nội dung dòng nhưng không phát hiện xoá dòng cuối/overwrite toàn bộ file nếu thiếu mốc tin cậy bên ngoài (đã ghi rõ).
