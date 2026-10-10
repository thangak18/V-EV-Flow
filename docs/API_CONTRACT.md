# API contract v0 — mục tiêu triển khai

Phase 0 provides a running FastAPI mock for the routes below via `uv run uvicorn app.backend.api.main:create_app --factory`; verify `/api/health`. Pydantic contracts in `app/backend/contracts` generate `openapi.yaml`; examples remain mock/simulated and are not production accuracy claims. Prefix is `/api`; table paths are relative. Time is `+07:00`, probability 0–1, coordinates object `{lat,lng}`. Model/data/scenario versions must accompany results for reproducibility. The handoff runbook records the verified green CI gate.

| Method | Path | Ưu tiên | Chức năng |
| --- | --- | --- | --- |
| GET | /stations | P0 | Metadata trạm và nguồn |
| POST | /predict | P0 | Khả dụng ở ETA và lý do |
| POST | /recommend | P0 | Primary, backup, ranking, plan_p; tải ảo bên trong |
| GET | /pressure?scenario=normal&time=... | P0 | Dữ liệu lớp Áp lực sạc |
| POST | /simulate | P0 | Một strategy trên bộ 100 xe |
| POST | /whatif | P1 | Thay capacity hoặc dịch giờ |
| POST | /reset | Demo | Xóa tải ảo/request cache của Driver |

## GET /stations

Response `{ "stations": [...], "data_type": "mixed", "source_notes": [...] }`, mỗi phần tử theo metadata trong DATA_CONTRACT. Tọa độ thật và cổng giả định phải phân biệt trong source notes.

## POST /predict

Request minh họa:

```json
{
  "station_id": "S012",
  "observed_at": "2026-10-13T16:00:00+07:00",
  "eta": "2026-10-13T16:40:00+07:00",
  "connector_type": "CCS2",
  "scenario": "normal"
}
```

Response minh họa:

```json
{
  "station_id": "S012",
  "eta": "2026-10-13T16:40:00+07:00",
  "p_available": 0.85,
  "reasons": ["Mô hình dự báo có cổng tại thời điểm xe đến"],
  "explanation_method": "rule",
  "model_version": "example-v1",
  "data_type": "simulated"
}
```

Snapshot/lag lấy theo observed_at, không lấy theo thời gian đồng hồ thật khi replay. ETA không trước observed_at; horizon tối đa thuộc config model, từ chối đầu vào ngoài phạm vi.

## POST /recommend

Request minh họa:

```json
{
  "request_id": "demo-001",
  "origin": {"lat": 10.78, "lng": 106.70},
  "destination": {"lat": 10.35, "lng": 107.08},
  "observed_at": "2026-10-13T16:00:00+07:00",
  "depart_time": "2026-10-13T16:00:00+07:00",
  "scenario": "normal",
  "vehicle": {
    "soc_pct": 20,
    "battery_kwh": 60,
    "consumption_kwh_per_km": 0.18,
    "connector_type": "CCS2"
  }
}
```

Response minh họa (khoảng cách và SOC nhất quán theo công thức; không phải trạm/tuyến/kết quả thật):

```json
{
  "request_id": "demo-001",
  "primary": {
    "station_id": "S012",
    "eta": "2026-10-13T16:40:00+07:00",
    "distance_km": 15,
    "detour_km": 5,
    "arrival_soc_pct": 15.5,
    "p_available": 0.85
  },
  "backup": {
    "station_id": "S015",
    "eta": "2026-10-13T16:55:00+07:00",
    "distance_km": 25,
    "detour_km": 7.5,
    "arrival_soc_pct": 12.5,
    "p_available": 0.60
  },
  "plan_p": 0.94,
  "plan_p_assumption": "independent_stations",
  "reasons": ["Đủ pin để tới trạm chính và tiếp tục tới dự phòng nếu cần"],
  "time_shift": null,
  "model_version": "example-v1",
  "allocation_method": "ranking_penalty",
  "data_type": "simulated"
}
```

Backup distance/ETA/SOC theo nhánh origin → primary → backup nếu primary không sạc được. `primary`/`backup` có thể null; `plan_p` null khi không có kế hoạch, lý do rõ. Endpoint ghi tải cho primary đã chọn; UI chỉ gọi khi người dùng yêu cầu kế hoạch, không gọi mỗi lần render. Retry cùng request_id không tạo tải mới; reset trước khi chạy lại demo.

## GET /pressure

`scenario` theo enum, `time` URL-encode ISO 8601. Response gồm `time`, `scenario`, `stations` với `station_id`, `p_available`, `pressure_score`, `data_type`. P0 có thể dùng `pressure_score = 1 - p_available` theo một horizon cố định công khai, ví dụ 30 phút; đây là proxy rủi ro thiếu cổng, chưa phải lưu lượng đo thực tế. Công thức/legend phải thống nhất UI và backend.

## POST /simulate

```json
{
  "scenario": "tet",
  "seed": 42,
  "vehicle_count": 100,
  "strategy": "ai_allocation"
}
```

`strategy`: `nearest`, `currently_available`, `ai_allocation`. Response gồm scenario/seed/strategy/model_version, `fixture_hash` (SHA-256 của bộ fixture đầu vào), và `metrics`: success_rate, mean_detour_km, mean_wait_minutes, failed_count, vehicle_count. D gọi ba lần với cùng fixtures/config/seed để dựng bảng; C có thể gọi trực tiếp runner của A trong process cho demo nhỏ. Tách state khỏi Driver. Dữ liệu kết quả tính thật bằng runner, không hard-code số thắng baseline.

## POST /whatif — P1

```json
{
  "scenario": "tet",
  "seed": 42,
  "vehicle_count": 100,
  "strategy": "ai_allocation",
  "change": {"kind": "add_ports", "station_id": "S012", "extra_ports": 2}
}
```

Change khác: `{ "kind": "shift_departure", "fraction": 0.2, "offset_minutes": -120 }`. Trả before/after/delta và config. Thêm capacity không tự động làm model đã train trở nên đúng cho cấu hình mới; ghi giới hạn generalization, dùng simulator đánh giá và tránh gọi kết quả là cam kết thực tế.

## POST /reset

Request `{}`; response `{ "reset": true }`. Xóa dict phân bổ và request cache, không xóa file/dataset/model. Chỉ phục vụ demo, chạy một worker.

## Validation/lỗi

422 cho đầu vào sai (SOC, pin, timestamp, scenario, tọa độ); 404 cho station_id không có; 409 cho request_id trùng nhưng payload khác; 503 khi model/source chưa sẵn sàng; upstream route lỗi trả thông báo/fallback có nguồn. Các lỗi nghiệp vụ có `code`, `message`; FastAPI validation 422 có thể dùng `detail` mặc định, frontend xử lý cả hai. Không đủ pin/không có trạm là kết quả kế hoạch rỗng có reasons, không treo UI.
