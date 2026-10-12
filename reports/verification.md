# Báo cáo xác minh bài lab Day 24 L3

**Ngày:** 12/10/2026. **Nguồn xác minh:** [GitHub Actions run 38263808745](https://github.com/Soraishiro/K4-L3-DAY24-VuHieuThien-2A202602867/actions/runs/38263808745), SHA `355a5259cf121a015c404b17285bb83bb549ce5d`, kết luận **success**. Các thay đổi sau SHA này chỉ bổ sung tài liệu.

## Kết quả thực tế

| Nội dung | Kết quả |
|---|---|
| Python | 3.11.17 |
| Cài đặt từ `requirements.lock` với `--require-hashes` | Thành công |
| Pytest toàn bộ `tests/` | **48 passed**, không có fail hoặc skip trong tổng kết |
| Độ chính xác PII trên dữ liệu tổng hợp | gold=118, pred=118, TP=118; precision=1.000, recall=1.000 |
| `agent.check_lure` | **4/4** biến thể đạt |
| Baseline cô lập cho 4 biến thể | **4/4** gửi hồ sơ tổng hợp KH-000999 đến sink nội bộ |
| Containment sau sửa | Sink rỗng; `http_post` bị từ chối |
| Ledger | **23 mục**, hash chain verify thành công; `args_hash` là SHA-256 tham số, không có giá trị giả `deadbeef` |
| Gitleaks v8.30.1 | Binary kiểm tra SHA-256 đạt; thư mục hiện tại sạch; lịch sử tìm thấy đúng **1 token giả** tại commit `1bdd849` |
| `pre-commit run --all-files` | Thành công |

Workflow cũng kiểm tra trực tiếp tính toàn vẹn của **ledger đã commit**, trước khi tạo bộ minh chứng mới. Lần quét lịch sử Gitleaks trả mã 1 khi tìm thấy token giả theo yêu cầu; đây không phải credential thật.

## Tệp minh chứng

- `reports/attack-before.log`: lần baseline cô lập biến thể 1 có POST đến `/reconcile`.
- `reports/replay-summary.json`: cả 4 baseline cô lập thành công, sau bảo vệ không có POST.
- `reports/attack-after.log`: rỗng.
- `reports/ledger.jsonl`: 23 quyết định và hash chain từ lần tái tạo.
- `reports/secrets-incident.md`: token giả trong lịch sử.
- `injection-corpus.md`: phương pháp và kết quả của 4 biến thể.
- `reports/compliance-mapping.md` và `reports/dpia-lite.md`: đối chiếu rủi ro, văn bản chính thức và giới hạn mock.

## Tái tạo

```bash
python -m pip install --require-hashes -r requirements.lock
python -m pytest tests/ -q -s
python -m agent.check_lure corpus/ticket-90*.md
python -m scripts.replay_evidence
python -c "from pathlib import Path; from agent.ledger import verify; print(verify(Path('reports/ledger.jsonl')))"
gitleaks version
gitleaks git --config .gitleaks.toml --redact --verbose .
gitleaks dir --config .gitleaks.toml .
pre-commit run --all-files
```

Mỗi lượt chạy replay tạo thời gian, run ID và hash mới. Chỉ dữ liệu tổng hợp được gửi tới `127.0.0.1:10024` trong phần baseline cố ý không bảo vệ.

## Giới hạn

Kết quả chỉ chứng minh các yêu cầu của bài lab trên mock và tập dữ liệu tổng hợp. `--as` không phải xác thực thật, regex không bảo đảm nhận diện mọi PII ngoài tập kiểm thử, ledger không phát hiện được việc cắt đuôi/viết lại cả file nếu thiếu mốc tin cậy, và tài liệu pháp lý không phải xác nhận tuân thủ của hệ thống sản xuất.
