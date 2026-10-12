# Làm việc chung

Đọc README, AGENTS áp dụng, SPEC của module và plan được giao. Dùng Makefile để setup và kiểm chứng, ghi kết quả thực thi trong PR; review và merge do con người quyết định.

| Người | Nhánh | Phạm vi |
| --- | --- | --- |
| Bảo | `feat/data-simulator` | `app/backend/modules/station_data/`, `app/backend/modules/simulation/` và tests/docs của chúng |
| Thắng | `feat/ml-predict` | `app/backend/modules/prediction/` và tests/docs của module |
| Kiên | `feat/recommend-api` | Recommendation, infrastructure, API composition/routes và tests/docs tương ứng |
| Tú | `feat/web-map` | Frontend source, component/service tests, E2E và module docs |

- `main` là bản tích hợp. Nhánh owner bắt đầu từ Foundation snapshot trong [runbook](docs/runbooks/phase-0-handoff.md), rồi merge prerequisites từ `main`. Một người ghi mỗi nhánh; Kiên điều phối integration.
- A↔B review dữ liệu/nhãn/evaluation; C↔D review API/UI. Người review không phải tác giả.
- Contracts, generated OpenAPI/types, dependency manifests/locks, CI và root tooling dùng PR riêng trên nhánh `codex/`. Contract PR cập nhật models, examples, generation, consumer tests và docs cùng nhau.
- Không tự sửa module của người khác để chữa lỗi integration. Không force-push hoặc reset công việc của người khác.
- `make setup` cài frozen dependencies. Chạy focused tests khi phát triển; trước handoff hoàn tất, chạy fresh `make ci` trên commit sạch.
- PR ghi owner/scope, mục tiêu và acceptance criteria, contract impact, data origin, exact commands/results, tested SHA, CI links, limitations, rollback và ảnh/trace khi UI thay đổi. Chưa chạy thì ghi NOT RUN; thiếu prerequisite thì ghi BLOCKED.
- Generate OpenAPI bằng `uv run python -m app.backend.api.generate_openapi`, types bằng `npm --prefix app/frontend run generate:api` trong contract PR. `make contract-check` dùng `--check` để phát hiện drift, không thay lệnh sinh artifact.
- Merge sau CI xanh trên revision cuối, non-author approval và conversations resolved; dùng [merge checklist](docs/runbooks/branch-protection.md). Commit mới hoặc base thay đổi cần kiểm chứng và review lại.
- Không commit `.env`, keys, cache thật, model binaries, history lớn, dữ liệu đối tác hoặc test logs. Fixture nhỏ có nguồn và nhãn mock/simulated/assumed rõ ràng.

Lịch nhóm: họp 15 phút mỗi sáng; chốt tính năng tối 14/10/2026, ý tưởng mới chuyển backlog. Lịch BTC cần nhóm xác nhận.
