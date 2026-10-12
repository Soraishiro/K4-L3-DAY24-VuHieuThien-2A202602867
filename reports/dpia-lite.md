# DPIA-lite (Data Protection Impact Assessment, phiên bản rút gọn)

## Dữ liệu
- Dữ liệu synthetic: khách hàng giả trong `data/customers.json` (KH-000999, KH-000777...), ticket trong `corpus/*.md`. Chứa PII giả (CCCD/SĐT/STK/email) phục vụ mục đích lab.
- Token giả: `lab-fake-secret.txt` tại commit `1bdd849` (synthetic, rule `lab24-synthetic-token`). Không phải credential thật.

## Mục đích xử lý
- Giáo dục: tạo bằng chứng rò rỉ, xây lớp chặn (PII gate, policy, OBO, split, ledger), chứng minh remediation.

## Phạm vi & môi trường
- Chạy cục bộ (localhost:10024), chế độ `--mock` (không gọi API ngoài). Sink ghi log cục bộ `reports/sink.log`.
- Phân biệt rõ: mock ≠ hệ thống thật; principal là fixture mô phỏng, không phải auth production.

## Rủi ro & biện pháp giảm thiểu
- Rủi ro: prompt injection → exfiltration. Giảm thiểu: trifecta split (Run B không đọc free text untrusted), policy deny restricted+egress, PII gate (redact), ledger audit, least privilege (OBO).
- Sau contain: `attack-after.log` rỗng, `tests/test_injection.py` pass cả 4 biến thể × 2 principal.

## Giới hạn của mock/system
- Ledger hash chain phát hiện sửa đổi nội dung dòng; không phát hiện xoá dòng cuối hoặc overwrite toàn bộ file nếu thiếu mốc tin cậy bên ngoài (đã ghi rõ trong doc).
- PII regex đạt recall cao nhưng precision thấp trên test set (đủ pass). Cần cải thiện cho production.
- Gitleaks tìm thấy token giả trong lịch sử (dự kiến) — là bằng chứng thực hành, không phải incident thật.
