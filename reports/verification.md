# Xác minh Day 24 — trạng thái sau đợt sửa

**Phạm vi:** nhánh `main`. Kết quả từ bản cũ được phân biệt với các phép kiểm tra chưa chạy trên bản mới. Không dùng báo cáo này để thay thế đầu ra thật của `pytest` hoặc Gitleaks.

## Bằng chứng đã có từ lần chạy trước

- `reports/attack-before.log`: có POST `/reconcile` chứa hồ sơ tổng hợp KH-000999.
- `reports/attack-after.log`: rỗng theo lần chạy cũ.
- Bộ test PII trên tập 120 dòng/118 thực thể: gold=118, pred=118, tp=118; precision=1.000 và recall=1.000 theo kết quả ghi nhận trước. Không còn dùng giá trị precision=0.554 của lần thử cũ.
- Lần quét Gitleaks v8.30.1 ghi nhận trong `reports/secrets-incident.md`: token giả tại commit `1bdd849` (mã thoát 1 là dự kiến). Chưa tái chạy Gitleaks trong phiên sửa này.
- File ledger cũ có các giá trị `deadbeef` và thời gian cố định: chỉ giữ để đối chiếu lịch sử; **không** dùng làm bằng chứng cho logic ghi mới.

## Những thay đổi cần xác minh trên commit cuối

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
python scripts/replay_evidence.py
python -c "from agent.ledger import verify; from pathlib import Path; print(verify(Path('reports/ledger.jsonl')))"
gitleaks version
gitleaks git --config .gitleaks.toml --redact --verbose .
gitleaks dir --config .gitleaks.toml .
pre-commit run --all-files
git status --short
```

GitHub Actions chỉ chạy pytest và replay bằng mock; **không** được mô tả là đã chạy Gitleaks/pre-commit nếu không có log riêng. Việc chạy replay phải dùng dữ liệu tổng hợp và sink localhost; không bật `--model`.

Khi có kết quả cuối, ghi: commit SHA, số test pass/fail/skip, phiên bản Python và Gitleaks, kết quả quét lịch sử/hiện tại, kết quả pre-commit và giới hạn chưa kiểm chứng. Đối chiếu đường dẫn tệp minh chứng với commit thật; không dùng thời gian hoặc hash giả làm minh chứng mới.
