# V-EV Flow

Bản demo tích hợp hiện có model/calibrator, simulator ba chiến lược và hai UI;
phần P1 bổ sung what-if, gợi ý lệch giờ có điều kiện và native TreeSHAP. Chạy
`python -m app.backend.api.demo` với release tin cậy theo
[runbook P1](docs/runbooks/p1-demo.md). Dữ liệu luôn ghi **simulated**; các ghi
chú Phase 0 phía dưới là lịch sử foundation, không phải mô tả đầy đủ bản demo.

Dự báo và điều phối nhu cầu sạc xe điện trên hành lang cao tốc. Dự án hackathon của nhóm 4 người, hướng đến một lớp ứng dụng thông minh có thể tích hợp vào VETC Trạm sạc / Vmap sau giai đoạn demo.

**Trạng thái: Phase 0 foundation đã có backend/frontend mock vertical slice, contracts, OpenAPI sinh tự động và CI gates.** Các model, simulator, dữ liệu đối tác và màn hình bản demo đầy đủ vẫn là phạm vi các nhánh owner sau handoff; số ví dụ không phải kết quả đo.

## Quyết định đã chốt

- Một web app React + Vite, hai màn hình: Người lái theo khung điện thoại trên laptop và Điều phối theo màn hình desktop. Responsive khi mở trên điện thoại thật.
- Python 3.11+ cho simulator, ML và FastAPI; NumPy/pandas, LightGBM/scikit-learn/Pydantic.
- Lưu bằng Parquet, JSON/CSV, YAML và joblib. Không cần database server.
- Một hành lang, 10–20 trạm; mặc định TP.HCM–Vũng Tàu, điều chỉnh nếu dữ liệu từ Tasco yêu cầu.
- Nhắm demo tối **15/10/2026**; triển khai **11–15/10**, chốt tính năng tối **14/10**. Ngày 16/10 chỉ là dự phòng nếu BTC cho phép.
- Trạng thái cổng mô phỏng phải được ghi rõ. Kết quả trên simulator chưa chứng minh độ chính xác ngoài thực tế.

## Đọc theo thứ tự

| Tài liệu | Nội dung |
| --- | --- |
| [Proposal gốc](V-EV%20Flow%20%E2%80%93%20Proposal.md) | Bài toán, giải pháp, giá trị và hướng mở rộng |
| [Phân công và lịch 5 ngày](TEAM_WORK_PLAN.md) | A/B/C/D, sản phẩm bàn giao, dependency và nghiệm thu |
| [Phạm vi MVP](docs/SCOPE.md) | P0, P1, tính năng hoãn |
| [Kiến trúc và công nghệ](docs/ARCHITECTURE.md) | Luồng xử lý, công nghệ, cache và chạy demo |
| [Dữ liệu](docs/DATA_CONTRACT.md) | Schema thống nhất, thời gian, loại cổng, nguồn và giả định |
| [API](docs/API_CONTRACT.md) | Bảy endpoint dự kiến, request/response và quy tắc lỗi |
| [ML và phân bổ](docs/ML_AND_ALLOCATION.md) | Nhãn, feature, hiệu chỉnh, ranking và đánh giá |
| [Hai giao diện](docs/UI_SPEC.md) | Driver/Operator, bố cục và thứ tự dựng |
| [Demo và checklist](docs/DEMO.md) | Demo 20% pin, 100 xe, dự phòng và việc hỏi mentor |
| [Làm việc chung](CONTRIBUTING.md) | Nhánh, PR, integration và quy tắc repo |
| [Phase 0 handoff](docs/runbooks/phase-0-handoff.md) | Đọc theo thứ tự, gates, OpenAPI và tạo nhánh owner |

## Cấu trúc

```text
V-EV-Flow/
├── README.md
├── TEAM_WORK_PLAN.md
├── CONTRIBUTING.md
├── .env.example
├── .github/     # Specification cho CI/CD và chính sách PR
├── app/
│   ├── backend/
│   │   ├── contracts/       # DTO, ports và OpenAPI dùng chung
│   │   ├── modules/         # Station data, simulation, prediction, recommendation
│   │   ├── infrastructure/  # Adapter mock/file/real và routing
│   │   └── api/             # FastAPI và composition root
│   └── frontend/            # React + Vite Driver/Operator
├── deploy/      # Specification đóng gói demo
└── docs/        # Kiến trúc, contract, specs và kế hoạch
```

`app/` chứa foundation code và specs. Phase 0 đã tạo Pydantic contracts, OpenAPI, dependency injection, mock vertical slice và CI trước khi bốn nhánh bắt đầu. Xem [master design](docs/superpowers/specs/2026-10-11-parallel-development-design.md), [Phase 0 spec](docs/superpowers/specs/2026-10-11-phase-0-foundation-spec.md) và [handoff runbook](docs/runbooks/phase-0-handoff.md).

## Bắt đầu cùng nhóm

```bash
git clone https://github.com/thangak18/V-EV-Flow.git
cd V-EV-Flow
cp .env.example .env
```

Repo private nên thành viên cần được cấp quyền trước khi clone. Foundation snapshot đã được review độc lập theo [handoff runbook](docs/runbooks/phase-0-handoff.md). Bảo/Thắng/Kiên/Tú làm trên nhánh owner và tích hợp prerequisites từ `main` bằng merge. Khi thêm code, owner cập nhật hướng dẫn cài và chạy thực tế trong tài liệu module.

## Lệnh canonical và trạng thái xác minh

Chạy từ root repo sau khi đã cài `uv` và Node/npm. `make setup` đồng bộ lockfile; các gate còn lại là lệnh canonical dùng trong PR và CI:

```bash
make setup
make lint
make test
make build
make contract-check
make smoke
make ci
```

Foundation acceptance và CI lịch sử được ghi trong [record](docs/runbooks/phase-0-handoff.md). Mỗi PR mới ghi lệnh, kết quả, tested SHA và CI link của chính revision đó. Hoàn tất handoff sau fresh `make ci` exit 0 trên working tree sạch; reviewer và integrator quyết định merge.

Mock backend và frontend có thể chạy độc lập để kiểm tra vertical slice:

```bash
uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000
npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173
```

Backend health check là `http://127.0.0.1:8000/api/health`; frontend mở `http://127.0.0.1:5173/`. Các gate canonical được định nghĩa trong Makefile; ghi kết quả kiểm tra và bàn giao trong PR.

Proposal và kế hoạch mới do nhóm có sẵn được giữ nguyên ở root. Kế hoạch 7 ngày ban đầu được lưu tại [docs/reference](docs/reference/README.md). Khi có khác biệt, dùng bộ tài liệu triển khai hiện tại ở README này; lịch BTC và dữ liệu đối tác vẫn cần nhóm xác nhận.
