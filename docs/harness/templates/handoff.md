# Handoff issue N

Khối JSON đầu tiên là metadata phiên bản 1; thay placeholders bằng dữ liệu thật. `head` ghi SHA tại checkpoint, không cần trùng commit chứa file. Trạng thái máy đọc: `implemented`, `verified`, `review-ready`, `blocked`; `merged` do integrator ghi nhận ở GitHub, không dùng để đạt local ready.

```json
{
  "schema_version": 1,
  "issue": 123,
  "url": "https://github.com/thangak18/V-EV-Flow/issues/123",
  "head": "<checkpoint-sha>",
  "base": "<integration-base-sha>",
  "branch": "<owner-branch>",
  "issue_hash": "<snapshot-body-hash>",
  "state": "implemented",
  "completed": [],
  "remaining": ["AC-01"],
  "decisions": [],
  "blockers": [],
  "next_step": "Hoàn thiện regression test AC-01",
  "retries": 0,
  "dirty_at_checkpoint": false
}
```

- Issue URL, snapshot updatedAt, owner/tool/surface/version:
- Foundation origin (xem policy), integration base:
- Goal/scope và dữ liệu/giới hạn:
- Staged/unstaged/untracked changes tại checkpoint:
- AC completed/remaining, quyết định và lý do:
- Checks: exact command, result, tested SHA/base, evidence path/link:
- Final gate: chờ chạy trên commit sạch; kết quả cuối ở PR/evidence ignored.
- Blockers, số vòng sửa từng failure, bước tiếp theo:
- Cách chuyển công việc: pushed checkpoint/draft PR hoặc patch rõ ràng:

Không ghi `verified` chỉ vì code xong; không ghi `merged` nếu chưa có xác nhận GitHub. Resume phải kiểm tra hiện trạng thay vì tin tuyệt đối checkpoint cũ.
