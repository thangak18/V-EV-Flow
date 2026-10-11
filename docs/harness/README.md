# Harness dùng chung cho Codex và Claude Code

Harness lưu quy trình trong repo và dùng adapter mỏng cho hai công cụ. Con người giao issue, bắt đầu phiên và quyết định merge. API/DTO sản phẩm không đổi để phục vụ harness.

## Bắt đầu

Cần quyền clone repo private, Git, Python 3.11+, `uv`, Node 22/npm, `gh` đã đăng nhập. Không lưu credentials trong repo.

```bash
cp .env.example .env
python3 .github/scripts/harness.py doctor
make setup
python3 .github/scripts/harness.py self-check
```

Backend đọc root `.env`; frontend mặc định `/api` qua Vite proxy. Nếu cần `VITE_*`, export biến hoặc tạo `app/frontend/.env` ignored; Vite không tự đọc root `.env`.

Sau khi người giao task tạo issue đủ đầu vào và reviewer chấp nhận Foundation:

```bash
python3 .github/scripts/harness.py start --issue 123
python3 .github/scripts/harness.py scope --issue 123 --base <integration-base-sha>
python3 .github/scripts/harness.py run --issue 123 --check test --ac AC-01
python3 .github/scripts/harness.py handoff --issue 123
```

`123` và `<integration-base-sha>` là placeholders, không phải issue hoặc SHA đã nghiệm thu. Chạy từ checkout đang làm việc; hooks cũng hỗ trợ subdirectory/worktree. `start` không claim issue hay tạo nhánh. `--snapshot FILE` chỉ dùng replay/offline fixture; phải đánh dấu provenance và không thay lần đối chiếu GitHub khi review-ready.

## Nguồn chuẩn

| Thông tin | Nguồn |
| --- | --- |
| Product rules/interfaces | AGENTS, SPEC, data/API contracts |
| Owner paths, branch, Foundation origin, gates | [policy.json](policy.json) |
| Thực hiện issue | [workflow.md](workflow.md) |
| Setup/build/check commands | Root Makefile và scripts |
| Goal, scope, AC, dependency, assignee | GitHub Issue |
| Decisions và checkpoint | `handoffs/<issue>.md` |
| Execution output/revision | Ignored `.harness/`, PR và CI artifacts |
| Review/merge/completion | GitHub PR và integrator |

Đọc [compatibility](compatibility.md) trước khi dùng surface mới; [pilot](pilot.md) ghi những nghiệm thu thực tế còn cần. Handoff format tại [template](templates/handoff.md), evidence format tại [schema](schemas/evidence.schema.json). Hooks là tiện ích đọc trạng thái; tắt hooks vẫn phải dùng workflow và gate như nhau.

## Trạng thái triển khai

Bộ docs, policy, CLI, adapters và kiểm tra tự động được xây trong harness bootstrap. Kết quả test phải đọc từ bằng chứng của PR, không suy ra từ việc file tồn tại. Foundation review độc lập và pilot hai công cụ/thành viên mới vẫn là gate cần người thực hiện; xem runbook và pilot. Không coi các ví dụ P1/P2 là feature đã có.

## Nguyên lý tham khảo

Áp dụng repo làm nguồn kiến thức, instructions có định tuyến, issue AC làm feature list, bàn giao nhiều phiên, evidence theo revision và vòng sửa có giới hạn. Các ví dụ khóa học không thay frozen setup, coverage hoặc merge rules của repo.

- [Repo làm system of record](https://walkinglabs.github.io/learn-harness-engineering/vi/lectures/lecture-03-why-the-repository-must-become-the-system-of-record/)
- [Instructions có định tuyến](https://walkinglabs.github.io/learn-harness-engineering/vi/lectures/lecture-04-why-one-giant-instruction-file-fails/)
- [Liên tục giữa phiên](https://walkinglabs.github.io/learn-harness-engineering/vi/lectures/lecture-05-why-long-running-tasks-lose-continuity/)
- [Initializer](https://walkinglabs.github.io/learn-harness-engineering/vi/lectures/lecture-06-why-initialization-needs-its-own-phase/)
- [Feature list](https://walkinglabs.github.io/learn-harness-engineering/vi/lectures/lecture-08-why-feature-lists-are-harness-primitives/)
- [Done cần thực thi](https://walkinglabs.github.io/learn-harness-engineering/vi/lectures/lecture-09-why-agents-declare-victory-too-early/)
- [Runtime observability](https://walkinglabs.github.io/learn-harness-engineering/vi/projects/project-06-runtime-observability-and-debugging/)
- [Loop engineering](https://walkinglabs.github.io/learn-harness-engineering/vi/projects/project-07-loop-engineering-first-loop/)
