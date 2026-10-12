# Secrets incident (synthetic)

- Commit chứa token giả: `1bdd849922156c868a5ee9293d68f5b72e242d2c`
- File: `lab-fake-secret.txt`, dòng 1
- RuleID: `lab24-synthetic-token`
- Fingerprint: `1bdd849922156c868a5ee9293d68f5b72e242d2c:lab-fake-secret.txt:lab24-synthetic-token:1`
- Kết quả quét lịch sử (gitleaks v8.30.1, config `.gitleaks.toml`, --redact): tìm thấy 1 finding ở commit trên. Exit code 1 là hành vi mong đợi đối với finding này.

Giải thích:

- Token này là dữ liệu tổng hợp (`LAB24-DEMO`) được cài sẵn trong lịch sử repo nhằm mục đích thực hành quét secrets (checkpoint 4). Nó không phải credential thật.
- Nếu đây là secret thật, cần thực hiện thu hồi/rotate và vô hiệu hoá credential, đồng thời xét đến việc phải xóa khỏi lịch sử Git (rebase/filter-repo) và thông báo các hệ thống liên quan. Tuy nhiên, chỉ xoá file khỏi HEAD (`git rm` rồi commit) **không thu hồi** credential đã từng bị công khai/lộ trong lịch sử.
- Pin dependency (requirements.lock với hashes) và pre-commit hook (gitleaks-system v8.30.1) giúp ngăn chặn lộ mới và đảm bảo môi trường tái lập, nhưng **không thay thế** bước rotate khi secret đã từng được phát tán (đã có trong lịch sử). Đây là sự phân biệt quan trọng giữa prevention (chặn commit mới) và remediation (xử lý lộ đã xảy ra).
- Quét file hiện tại sạch (không có finding mới). Hook được cấu hình với `pass_filenames: false` (gitleaks git) như yêu cầu.

Bằng chứng quét:

```bash
PATH=/tmp:$PATH gitleaks git --config .gitleaks.toml --redact --verbose .
```

(Exit code trả về 1 khi có finding — đây là kết quả dự kiến, không phải lỗi trong quá trình làm bài.)
