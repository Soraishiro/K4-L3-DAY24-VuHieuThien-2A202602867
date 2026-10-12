# Bốn biến thể prompt injection — lab Day 24

Mọi lệnh thử chỉ chạy với dữ liệu tổng hợp và sink `127.0.0.1:10024`. Hai hướng thử: `support_l1` bị từ chối đọc hồ sơ, `dpo` có thể đọc hồ sơ hợp lệ nhưng không được gửi restricted ra ngoài.

| Biến thể | Tệp | Kỹ thuật và điều kiện nhận diện |
|---|---|---|
| 1 | `corpus/ticket-901.md` | HTML comment chứa lệnh; `search_docs` trả về nguyên văn |
| 2 | `corpus/ticket-902.md` | HTML comment có ký tự U+200B đan trong từ khóa; `MockLLM` chuẩn hóa trước khi nhận diện |
| 3 | `corpus/ticket-903.md` | Giả mạo quyền DPO và quy trình nội bộ |
| 4 | `corpus/ticket-904.md` + `ticket-904b.md` | Lệnh chia hai tài liệu: chỉ một marker ở từng tệp; kết hợp mới đạt ngưỡng hai marker và có `KH-000999` |

## Bằng chứng

- **Baseline trước sửa:** `reports/attack-before.log` (lần chạy cũ) chứa POST `/reconcile` và hồ sơ tổng hợp `KH-000999`. Đây là bằng chứng tấn công tổng hợp, chưa phải bốn lần thử cô lập.
- **Sau sửa:** `reports/attack-after.log` cũ rỗng; bộ kiểm thử `tests/test_injection.py` phải xác minh đủ 4 biến thể × 2 principal.
- **Kiểm thử bổ sung:** `tests/test_security_regression.py::test_split_payload_requires_both_documents` kiểm tra hai phần riêng không kích hoạt, kết hợp có kích hoạt. `test_second_lure_has_invisible_characters` kiểm kỹ thuật biến thể 2.
- **Tái tạo bằng chứng cô lập:** chạy `python scripts/replay_evidence.py` (tạo báo cáo `reports/replay-summary.json` cùng ba file evidence); không gọi API bên ngoài.

Không được suy luận từ một log baseline tổng hợp rằng từng biến thể đã kích hoạt độc lập. Chỉ ghi xác nhận sau khi đã chạy kịch bản cô lập. Quy tắc không dùng dữ liệu thật được giữ nguyên.
