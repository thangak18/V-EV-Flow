# V-EV Flow

Dự báo và điều phối nhu cầu sạc xe điện trên hành lang cao tốc. Dự án hackathon của nhóm 4 người, hướng đến một lớp ứng dụng thông minh có thể tích hợp vào VETC Trạm sạc / Vmap sau giai đoạn demo.

**Trạng thái: repo sơ khai gồm tài liệu và bộ specification cho modular monolith. Chưa có backend, model, simulator hoặc giao diện chạy được.** Các API, màn hình và lệnh trong tài liệu là mục tiêu triển khai; số ví dụ không phải kết quả đo.

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

`app/` hiện chỉ chứa `SPEC.md`, chưa phải code đã triển khai. Phase 0 sẽ tạo Pydantic contracts, OpenAPI, dependency injection, mock vertical slice và CI trước khi bốn nhánh bắt đầu. Xem [master design](docs/superpowers/specs/2026-10-11-parallel-development-design.md) và [Phase 0 spec](docs/superpowers/specs/2026-10-11-phase-0-foundation-spec.md).

## Bắt đầu cùng nhóm

```bash
git clone https://github.com/thangak18/V-EV-Flow.git
cd V-EV-Flow
cp .env.example .env
```

Repo private nên thành viên cần được cấp quyền trước khi clone. Chưa có bước chạy ứng dụng. Một foundation agent phải triển khai và merge Phase 0 trước; sau đó Bảo/Thắng/Kiên/Tú tạo nhánh từ cùng merge commit. Khi thêm code, owner cập nhật hướng dẫn cài và chạy thực tế trong tài liệu module.

Proposal và kế hoạch mới do nhóm có sẵn được giữ nguyên ở root. Kế hoạch 7 ngày ban đầu được lưu tại [docs/reference](docs/reference/README.md). Khi có khác biệt, dùng bộ tài liệu triển khai hiện tại ở README này; lịch BTC và dữ liệu đối tác vẫn cần nhóm xác nhận.
