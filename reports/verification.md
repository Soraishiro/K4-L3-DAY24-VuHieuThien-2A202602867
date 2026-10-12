# Xác minh Day 24 — kết quả kiểm thử thực tế

**Phiên bản kiểm tra:** commit `f3a8518284d43481b12854d65e18438dd637a0af` trên `main`; GitHub Actions run [38263190831](https://github.com/Soraishiro/K4-L3-DAY24-VuHieuThien-2A202602867/actions/runs/38263190831), ngày 12/10/2026. Toàn bộ bước trong workflow hoàn thành thành công.

## Bằng chứng đã có từ lần chạy trước

- `reports/attack-before.log`: có POST `/reconcile` chứa hồ sơ tổng hợp KH-000999.
- `reports/attack-after.log`: rỗng theo lần chạy cũ.
- Bộ test PII trên tập 120 dòng/118 thực thể: gold=118, pred=118, tp=118; precision=1.000 và recall=1.000 theo kết quả ghi nhận trước. Không còn dùng giá trị precision=0.554 của lần thử cũ.
- Lần quét Gitleaks v8.30.1 ghi nhận trong `reports/secrets-incident.md`: token giả tại commit `1bdd849` (mã thoát 1 là dự kiến). Chưa tái chạy Gitleaks trong phiên sửa này.
- Ledger đã tái tạo có 23 mục, mọi mục có reason và SHA-256 của tham số thực; có 1 quyết định từ chối `http_post`.

## Các chức năng đã kiểm tra trên commit nêu trên

- Quyền OBO trong `agent/policy.py`: thiếu principal/tool/purpose/TTL bị từ chối, kiểm tra scope giao với parent.
- `agent/runner.py`: log thời gian UTC, args_hash tính từ tham số, ghi nhận lỗi gọi công cụ; Run A/B chỉ chuyển ticket ID và nhánh tóm tắt được che PII.
- `agent/ledger.py`: xác minh hash chain, từ chối nối tiếp file đã hỏng.
- `corpus/ticket-904.md` và `ticket-904b.md`: chỉ khi kết hợp mới kích hoạt.
- `tests/test_security_regression.py`: kiểm thử hồi quy mới.
- `scripts/replay_evidence.py`: tái tạo trước/sau và ledger, riêng từng biến thể baseline.
- `.github/workflows/lab-check.yml`: chạy pytest, kiểm lure, replay và xuất artifact trên GitHub Actions.

## Lệnh bắt buộc để kiểm tra khi chốt bài

```bash
python -m pip install --require-hashes -r requirements.lock
python -m pytest tests/ -q -s
python -m agent.check_lure corpus/ticket-90*.md
python -m scripts.replay_evidence
python -c "from agent.ledger import verify; from pathlib import Path; print(verify(Path('reports/ledger.jsonl')))"
gitleaks version
gitleaks git --config .gitleaks.toml --redact --verbose .
gitleaks dir --config .gitleaks.toml .
pre-commit run --all-files
git status --short
```

GitHub Actions chỉ chạy pytest và replay bằng mock; **không** được mô tả là đã chạy Gitleaks/pre-commit nếu không có log riêng. Việc chạy replay phải dùng dữ liệu tổng hợp và sink localhost; không bật `--model`.

Khi có kết quả cuối, ghi: commit SHA, số test pass/fail/skip, phiên bản Python và Gitleaks, kết quả quét lịch sử/hiện tại, kết quả pre-commit và giới hạn chưa kiểm chứng. Đối chiếu đường dẫn tệp minh chứng với commit thật; không dùng thời gian hoặc hash giả làm minh chứng mới.

## Kết quả CI đã xác nhận

- Python 3.11.17; cài `requirements.lock` bằng `--require-hashes` thành công.
- `python -m pytest tests/ -q -s`: **48 passed**, không có lỗi/skip trong tổng kết.
- `python -m agent.check_lure 'corpus/ticket-90*.md'`: **4/4** biến thể sẵn sàng.
- Replay mock cô lập: **4/4** biến thể làm lộ record tổng hợp trước containment; sink **rỗng** sau containment với `dpo`.
- `ledger.verify`: thành công; **23 mục**, có `http_post` deny và lý do.
- Gitleaks **v8.30.1**: bản phát hành đã kiểm SHA-256; quét thư mục hiện tại sạch; quét lịch sử phát hiện đúng **1 token giả** theo rule `lab24-synthetic-token` và commit `1bdd849`.
- `pre-commit run --all-files`: thành công.
- Tệp nguồn minh chứng: `reports/attack-before.log`, `reports/attack-after.log`, `reports/ledger.jsonl`, `reports/replay-summary.json`. Artifact CI: [Run 38263190831](https://github.com/Soraishiro/K4-L3-DAY24-VuHieuThien-2A202602867/actions/runs/38263190831).

**Giới hạn:** Đây là lab `--mock` trên dữ liệu tổng hợp. Không chứng minh xác thực production, bảo vệ mọi biến thể prompt injection hoặc tuân thủ pháp lý thực tế. Minh chứng trong commit là từ run CI đã nêu; chạy lại sẽ tạo UUID, timestamp và hash khác.
