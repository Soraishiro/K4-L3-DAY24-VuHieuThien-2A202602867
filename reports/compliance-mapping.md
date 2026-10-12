# Đối chiếu quản trị dữ liệu và bảo mật agent — Day 24 L3

**Phạm vi:** Dữ liệu và danh tính đều mô phỏng, sink chỉ ở `127.0.0.1:10024`. Tài liệu này đối chiếu nguyên tắc và biện pháp trong bài lab, **không phải kết luận tuân thủ pháp luật của một hệ thống thật**.

| Căn cứ, điều khoản | Nguyên tắc liên quan | Bằng chứng triển khai (file/dòng; xem commit nộp cuối) | Giới hạn |
|---|---|---|---|
| Luật 91/2025/QH15, Điều 3 khoản 2 | Xử lý đúng phạm vi, mục đích | `agent/policy.py:check` kiểm `request_purpose`, `data/principals.json` khai báo purpose | Purpose của lab mô phỏng; không có căn cứ xử lý dữ liệu thật |
| Luật 91/2025/QH15, Điều 3 khoản 4 | Biện pháp bảo vệ dữ liệu | `agent/runner.py:handle` chặn đọc trái quyền và chuyển dữ liệu restricted ra sink; `agent/pii.py:redact` | Regex không đảm bảo phát hiện mọi PII ngoài test set |
| Luật 91/2025/QH15, Điều 21 | Đánh giá tác động khi xử lý dữ liệu cá nhân | `reports/dpia-lite.md` mô tả luồng, rủi ro và giảm thiểu | Chỉ là phiên bản luyện tập, không phải hồ sơ chính thức |
| NĐ 356/2025/NĐ-CP, Điều 19 khoản 3 điểm c, đ, g | Luồng xử lý, thiết kế an toàn và rủi ro | `reports/dpia-lite.md` (luồng, rủi ro), `tests/test_split.py`, `tests/test_injection.py` | Không có thông tin về bên kiểm soát/xử lý thật; không thực hiện thủ tục quy định tại Điều 19 |
| Luật 134/2025/QH15, Điều 6 khoản 1 | Ứng dụng AI gắn với quản lý rủi ro | `agent/policy.py:check`, `tests/test_security_regression.py`, `tests/test_injection.py` | Không thay cho phân loại và đánh giá rủi ro một sản phẩm AI ngoài đời |

## Đối chiếu OWASP Top 10 for Agentic Applications (2026)

| Mã chính thức | Rủi ro | Bằng chứng trong lab |
|---|---|---|
| **ASI01 — Agent Goal Hijack** | Nội dung thiếu tin cậy làm agent đổi mục tiêu | `corpus/ticket-901.md` đến `ticket-904b.md`, `agent/llm.py:find_injection`, `tests/test_injection.py` |
| **ASI02 — Tool Misuse & Exploitation** | Lạm dụng công cụ đọc và gửi dữ liệu | `agent/tools.py:read_customer/http_post`, `agent/policy.py:check` |
| **ASI03 — Identity & Privilege Abuse** | Lạm dụng quyền người dùng và ủy quyền | `data/principals.json`, `agent/runner.py:handle`, `tests/test_obo.py`, `tests/test_security_regression.py` |
| **ASI04 — Agentic Supply Chain Vulnerabilities** | Phụ thuộc và thành phần bị thay đổi/chiếm quyền | `requirements.lock`, `.pre-commit-config.yaml`, `reports/secrets-incident.md`, `tests/test_supply_chain.py` |

Không đồng nhất ASI03 với đầu độc ngữ cảnh hoặc ASI04 với ủy quyền. Bài có luồng nội dung thiếu tin cậy nhưng **không** chứng minh bảo vệ toàn diện bộ nhớ lâu dài (ASI06).

## Nguồn chính thức đã đối chiếu

1. Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15, Cổng thông tin văn bản Chính phủ: https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160&typegroup=
2. Nghị định 356/2025/NĐ-CP, Cổng thông tin văn bản Chính phủ: https://vanban.chinhphu.vn/?classid=1&docid=216387&pageid=27160
3. Luật Trí tuệ nhân tạo 134/2025/QH15, Cổng thông tin văn bản Chính phủ: https://vanban.chinhphu.vn/?docid=216334&pageid=27160&typegroupid=3
4. OWASP, *Top 10 for Agentic Applications*, công bố 09/12/2025: https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/

Các điều khoản trên dùng để giải thích mối liên hệ, không khẳng định nghĩa vụ cụ thể áp dụng cho bộ dữ liệu tổng hợp của bài lab.
