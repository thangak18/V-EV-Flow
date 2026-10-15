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

## POST /whatif — P1 đã triển khai

Request `WhatIfRequest` gồm scenario, seed không âm, vehicle_count, strategy,
contract_version="0.1.0" và `change` có discriminator `kind` bắt buộc:

```json
{"scenario":"tet","seed":42,"vehicle_count":100,"strategy":"ai_allocation","contract_version":"0.1.0","change":{"kind":"add_ports","station_id":"S001","ports":2}}
```

Hoặc `change: {"kind":"shift_departures","fraction":0.2,"target_hour":21}`.
Đơn vị là **cổng**, không phải trụ; ports nguyên 1–20. Dịch `floor(N*fraction)`
xe foreground (ít nhất 1) vào 20:00–20:55 hoặc 21:00–21:55 của ngày replay cuối.
Preset UI là 20% về 21h; không thay background arrivals, xe, compliance hoặc seed.

200 trả `WhatIfResult`: `before`/`after` là SimulationResult, `change`,
`before_config_hash`, `after_config_hash`, `shifted_vehicle_count`,
`data_type="simulated"`, `assumptions`, `contract_version`. Hai lượt phải cùng
scenario/seed/strategy/model_version/event fixture/mẫu số và khác fingerprint
cấu hình. UI tính delta từ số trả về, không hard-code cải thiện.

Chế độ file/model/stateful mới chạy được; valid request ở fake mode trả 503
FEATURE_NOT_READY. Không gửi body (hoặc null) giữ 503 của client cũ, không chạy thí nghiệm mặc định; body có nội dung sai schema trả 422; station không có trả 404. What-if là
read-only, không commit Driver allocations, không sửa dataset/artifact. Thêm cổng
chỉ đổi capacity của simulator và ranking; model giữ dữ liệu/capacity gốc, chưa
retrain dự báo cho capacity mới. Quyền truy cập Goong không đổi nhãn simulated.

### SHAP và gợi ý lệch giờ (optional extensions)

- `PredictionResult.explanation` và `Plan.explanation` tùy chọn: ModelExplanation
  (`method=tree_shap`, `space=raw_margin_log_odds`, bias/raw_score/raw_probability/
  calibrated_probability và đầy đủ features[value,contribution]). Tổng full
  contribution + bias = raw_score, sigmoid(raw_score)=raw_probability. Đây không
  phải phân rã xác suất đã calibrate hoặc quan hệ nhân quả. Không có explanation
  thì field được bỏ hẳn, giữ JSON P0 mặc định. Native method là tree_shap_raw_margin.
- RecommendationResult có `time_shift_evaluated` và `time_shift_estimate` tùy chọn.
  Probe delay 15/30 phút cho cùng primary, giữ observed_at và route duration;
  chỉ trả gợi ý nếu tăng >=5 điểm % và ETA trong capability artifact. Không có
  cải thiện thì time_shift=null; flag evaluated=true để UI không bịa gợi ý.
- Estimate ghi minutes, station_id, depart_time, eta, p_available, improvement,
  assumptions. Time_shift legacy giữ cùng số phút nếu có estimate. Kế hoạch và
  phân bổ hiện tại không bị thay bằng estimate; không tự thêm reservation.
- Chỉ bật trong explicit flags `PREDICTION_EXPLANATIONS=true` và
  `TIME_SHIFT_SUGGESTIONS=true`; demo launcher bật cả hai. Deploy frontend/backend
  cùng bộ contract: frontend cũ dùng strict parsing có thể reject các extension
  khi bật P1. Giữ flags false nếu consumer chưa được cập nhật. Artifact contract
  version vẫn 0.1.0; không đổi binary/calibrator chỉ để thêm giải thích.

Examples kiểm thử được ở `app/backend/contracts/examples/whatif.*.json`,
`predict.shap.response.json`, `recommend.shift.response.json`.

## POST /reset

Request `{}`; response `{ "reset": true }`. Xóa dict phân bổ và request cache, không xóa file/dataset/model. Chỉ phục vụ demo, chạy một worker.

## Validation/lỗi

422 cho đầu vào sai (SOC, pin, timestamp, scenario, tọa độ); 404 cho station_id không có; 409 cho request_id trùng nhưng payload khác; 503 khi model/source chưa sẵn sàng; upstream route lỗi trả thông báo/fallback có nguồn. Các lỗi nghiệp vụ có `code`, `message`; FastAPI validation 422 có thể dùng `detail` mặc định, frontend xử lý cả hai. Không đủ pin/không có trạm là kết quả kế hoạch rỗng có reasons, không treo UI.
