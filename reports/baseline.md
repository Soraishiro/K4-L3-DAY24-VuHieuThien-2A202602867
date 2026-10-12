# Baseline

## 1. Mỗi lần chạy baseline đã có agent_id/run_id và danh tính người dùng để kiểm quyền chưa? Chỉ dòng code chứng minh.

Theo `agent/loop.py` dòng 57–75 (hàm `run_once`), khi chưa có runner hoàn thiện, baseline gọi `_naive_loop(message, llm)` (dòng 74) và **không truyền** bất kỳ `agent_id/run_id/principal_id` nào vào `_naive_loop` cũng như không tạo/sử dụng chúng để kiểm quyền. `_naive_loop` (dòng 27–54) chỉ nhận `message, llm`; toàn bộ quyết định đọc customer và POST đều chỉ dựa vào kết quả `injected` từ LLM mà không có identity hay context kiểm quyền. Do đó, baseline **chưa** có agent_id/run_id/danh tính người dùng để kiểm quyền. Chứng cứ: `agent/loop.py:27-54, 57-75`.

## 2. Trước http_post, có policy nào kiểm mục đích, quyền và loại dữ liệu không? Ai thực sự quyết định gửi?

Baseline **không có policy nào** kiểm mục đích, quyền, loại dữ liệu trước khi gửi. `_naive_loop` (27–54) gọi `tools.search_docs` (dòng 31), lấy `combined_text`, gọi `llm.find_injection` (34), nếu có `injected` thì lặp `tools.read_customer` (38–42) và ngay lập tức gọi `tools.http_post(injected.target_url, {"records": collected})` (44) mà không đi qua bất kỳ lớp kiểm soát (PEP/policy/OBO/split/ledger). Quyết định gửi hoàn toàn do **mock LLM trả về `injected` từ nội dung untrusted (ticket)** — agent "tuân theo chỉ thị" tìm thấy trong corpus thay vì bị chặn bởi policy. Chứng cứ: `agent/loop.py:27-54`. (Lưu ý: `tools.http_post` chỉ có allowlist hardcoded về host/port `127.0.0.1:10024` — đó là giới hạn mạng, không phải policy kiểm quyền/mục đích/loại dữ liệu; xem `agent/tools.py:68-85`.)

## 3. Dòng nào tạo body POST, và file nào sẽ ghi lại việc sink đã nhận body đó?

Body POST được tạo tại `agent/loop.py:44` với `{"records": collected}` (mỗi phần tử là record trả về từ `tools.read_customer`). Việc sink nhận dữ liệu được ghi vào **`reports/sink.log`** (do `sink/sink.py` ghi log nhận POST). Chứng cứ: `agent/loop.py:44`, `agent/tools.py:68-85`, `sink/sink.py` (ghi log vào `reports/sink.log`).

