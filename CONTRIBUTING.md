# Làm việc chung

Đọc [harness workflow](docs/harness/workflow.md) khi nhận issue. [Policy](docs/harness/policy.json) quản lý đường dẫn, nhánh và gate; issue quản lý mục tiêu/AC/dependency; handoff quản lý checkpoint; PR/CI giữ bằng chứng trên revision cuối.

- `main` là bản tích hợp; giữ bốn nhánh owner theo policy. Chỉ mở lane sau khi reviewer độc lập chấp nhận Foundation snapshot trong [runbook](docs/runbooks/phase-0-handoff.md). Một issue và một người ghi mỗi lane; integrator điều phối các lane cùng lúc.
- A↔B review dữ liệu/nhãn/evaluation; C↔D review API/UI. Kiên là integrator dự kiến; phải xác nhận GitHub handles thực trước khi ghi approval.
- Harness bootstrap và tooling/contract dùng nhánh riêng theo policy. Shared contract changes cập nhật DTO, examples, OpenAPI/types, tests/docs và consumer impact cùng một PR; dependency updates là tooling prerequisite, không nằm trong feature PR.
- Sau squash merge, owner merge `main` để tích hợp prerequisites; không force-push hoặc tự reset thay đổi người khác.
- Dùng `make setup` để cài frozen locks, các gate Makefile để kiểm chứng. `make ci` phải chạy mới trên commit sạch trước handoff hoàn tất. Ghi `PASS`, `FAIL`, `BLOCKED`, `NOT RUN` trung thực, cùng HEAD/base/lệnh/log.
- Generate OpenAPI bằng `uv run python -m app.backend.api.generate_openapi`, types bằng `npm --prefix app/frontend run generate:api` trong contract PR. `make contract-check` kiểm tra OpenAPI bằng `--check` và drift; không dùng nó thay lệnh sinh OpenAPI.
- Commit code + checkpoint trước gate cuối, đưa kết quả gate cuối vào PR/ignored evidence; không commit log rồi giả sử bằng chứng còn đúng cho SHA mới.
- Review và merge thủ công trong pilot: CI xanh trên đúng head, base hiện tại, ít nhất một non-author approval, conversations resolved, scope/AC evidence đầy đủ. [Protection runbook](docs/runbooks/branch-protection.md) ghi rõ trạng thái cưỡng chế thực tế.
- Không commit `.env`, key, cache thật, model binary/lịch sử lớn, dữ liệu đối tác hoặc `.harness/`; fixture nhỏ cần nguồn và nhãn giả định.
- Giới hạn sửa cùng một lỗi và checkpoint theo workflow; hết quota không tự chuyển sang API trả phí. Cập nhật docs bằng hành vi và lệnh đã chạy, ghi rõ limitations.

Lịch nhóm: họp 15 phút mỗi sáng; chốt tính năng tối 14/10/2026, ý tưởng mới chuyển backlog. Lịch BTC cần nhóm xác nhận.
