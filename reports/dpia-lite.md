# DPIA-lite — Đánh giá tác động rút gọn cho bài lab

**Tính chất:** Bài tập mô phỏng bằng dữ liệu tổng hợp. Không xác nhận đáp ứng hồ sơ pháp lý theo Luật 91/2025/QH15 hay Nghị định 356/2025/NĐ-CP.

## Dữ liệu và mục đích

- `corpus/ticket-*.md`: phiếu hỗ trợ giả, gồm văn bản thiếu tin cậy có thể chứa chỉ thị tấn công.
- `data/customers.json`: hồ sơ tổng hợp với CCCD, điện thoại, số tài khoản và email giả; phân loại `restricted`.
- `data/principals.json`: cấu hình quyền mô phỏng (`support_l1`, `billing`, `dpo`) — `--as` không xác thực danh tính thật.
- Mục đích: phát hiện rủi ro prompt injection, kiểm soát truy cập và bảo vệ dữ liệu trong bài tập giáo dục.

## Sơ đồ luồng dữ liệu

```text
corpus/*.md (untrusted)
   │ search_docs (Run A, policy)
   ├─ tên tệp ──> ticket_id ──> related_tickets ──> customer_id
   │                                         │
   │                                Run B: kiểm OBO
   │                                         │
   │                                read_customer (restricted)
   │                                         │
   │                          PEP: restricted + egress => deny
   │                                         X
   │                          http://127.0.0.1:10024/reconcile
   │
   └─ redact(text) ──> nhánh tóm tắt (không truyền hồ sơ restricted)
```

Không truyền toàn văn phiếu hỗ trợ từ Run A sang Run B; chỉ truyền ID suy ra từ tên file. Nhánh tóm tắt xử lý văn bản phiếu đã được che PII; vẫn cần coi nội dung phiếu là thiếu tin cậy. Chế độ mô hình thật ở ngoài phạm vi chấm điểm.

## Rủi ro, biện pháp và bằng chứng

| Rủi ro | Biện pháp hiện có | Bằng chứng kiểm thử | Hạn chế còn lại |
|---|---|---|---|
| Lệnh ẩn làm agent đọc và gửi hồ sơ | Tách A/B; PEP từ chối restricted + egress | `tests/test_injection.py`, `tests/test_split.py` | Chỉ 4 biến thể, mô hình giả lập |
| ID khách hàng nằm trong free text của attacker | Chỉ đọc ID suy ra từ `related_tickets` | `tests/test_split.py` với `KH-000777` | Nguồn `related_tickets` được coi là tin cậy trong lab |
| Dùng quyền người khác/agent con vượt quyền | Principal, purpose, agent scopes, parent scopes, TTL | `tests/test_obo.py`, `tests/test_security_regression.py` | Không có xác thực đăng nhập |
| Lộ PII trong văn bản đầu vào nhánh tóm tắt | `agent/pii.py:redact` | `tests/test_pii.py`, `tests/test_security_regression.py` | Regex theo tập dữ liệu lab, không bảo đảm mọi ngữ cảnh |
| Thay đổi nhật ký | Chuỗi SHA-256, reason và args_hash | `tests/test_ledger.py`, `tests/test_security_regression.py` | Không phát hiện cắt bỏ đuôi/viết lại toàn bộ nếu thiếu mốc bên ngoài |
| Lộ token trong Git | Gitleaks, hook pin, hash lock; bài tập token giả | `reports/secrets-incident.md` | Quét scanner không thu hồi credential đã lộ |

## Phạm vi và lưu trữ

- Sink chỉ nghe tại `127.0.0.1:10024`. `reports/attack-before.log` ghi dữ liệu tổng hợp bị lộ có chủ đích trước containment; `reports/attack-after.log` dự kiến rỗng sau containment.
- Ledger và log ở `reports/`, các file evidence được đưa vào Git có chủ đích theo `SUBMISSION.md`; không đưa dữ liệu thật vào đây.
- Thời hạn lưu trữ, quy trình xóa và phân công nhân sự kiểm soát dữ liệu thật: **không áp dụng trong mock / chưa triển khai**.
- Nếu dùng dữ liệu thật cần phân định bên kiểm soát/xử lý, căn cứ xử lý, thời gian lưu, quản lý khóa, quyền chủ thể dữ liệu và quy trình sự cố. Bài lab không chứng minh các yêu cầu đó.

## Kết quả và giới hạn kiểm chứng

Tập `tests/vn_pii_testset.jsonl` có 118 thực thể chuẩn; phép đối chiếu mã nhận diện đã cho precision=1.000, recall=1.000. Đây chỉ là kết quả trên tập tổng hợp có sẵn, không suy rộng ra thực tế. Trước khi nộp cần chạy lại toàn bộ kiểm thử và tạo mới minh chứng trên commit cuối.

Tham chiếu yêu cầu của Điều 19 khoản 3 NĐ 356/2025/NĐ-CP (mục đích, sơ đồ luồng dữ liệu, bảo vệ dữ liệu, rủi ro): https://vanban.chinhphu.vn/?classid=1&docid=216387&pageid=27160
