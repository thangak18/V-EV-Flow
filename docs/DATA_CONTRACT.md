# Hợp đồng dữ liệu

Quy ước triển khai hiện tại thống nhất dùng `station_id`, `lat`, `lng`, `n_ports`, `ts`, `ports_free`, `ports_busy`, `ports_broken`, `p_available`. Những tên khác trong tài liệu nguồn cần adapter, không tồn tại hai schema runtime.

## Quy ước chung

- ID là chuỗi; thời gian ISO 8601 có offset `+07:00`. Bước trạng thái 5 phút, dùng `observed_at` để xác định hiện tại trong replay.
- Tọa độ dạng object `{lat, lng}`. Goong/GeoJSON có thể cần `[lng, lat]`; chuyển trong adapter, không đổi contract.
- SOC phần trăm 0–100; pin kWh; tiêu thụ kWh/km; khoảng cách km; ETA timestamp, horizon/độ dài thời gian dùng phút.
- Scenario: `normal`, `holiday_30_4`, `tet`. Scenario override cần đồng bộ cờ lễ/demand; không chỉ đổi nhãn giao diện.
- Connector là mã thống nhất, MVP demo có thể dùng một loại CCS2. Hỗn hợp connector chỉ được hỗ trợ khi có trạng thái theo loại.
- Trạm/cổng giả định phải ghi `source`, `assumptions`. Payload có `data_type`: `mock`, `simulated`, `real` hoặc `mixed` và ghi chú nguồn cụ thể.

## stations — `app/backend/modules/station_data/fixtures/stations.json`

| Field | Kiểu | Ý nghĩa |
| --- | --- | --- |
| station_id, name | string | Mã/tên trạm |
| lat, lng | float | Vị trí |
| n_ports | int >= 1 | Số cổng vật lý |
| power_kw | float > 0 | Công suất giả định/quan sát |
| connector_types | string[] | Loại cổng |
| network, station_type | string | Mạng, loại trạm |
| source | string | Nguồn và mốc thu thập |
| assumptions | string[] | Những thông số tự đặt |

## station_status — `app/backend/modules/station_data/generated/station_status.parquet`

`station_id`, `ts`, `ports_free`, `ports_busy`, `ports_broken`, `scenario`; unique theo `(scenario, station_id, ts)`. Các số không âm, tổng bằng `n_ports`. Nếu mô phỏng theo connector, bổ sung bảng riêng có `connector_type` và capacity tương ứng; không dùng cổng trống của loại khác làm nhãn.

15 trạm × 288 mốc/ngày × 180 ngày = **777.600 dòng cho một timeline**. Sinh riêng cả ba scenario sẽ khoảng 2,33 triệu dòng; nhân thêm horizon tạo nhãn có thể tăng nữa. Đây là phép tính quy mô, không phải dữ liệu đã có.

## scenarios — `app/backend/modules/station_data/fixtures/scenarios.yaml` (A sẽ tạo)

Thông số cần có: `seed`, thời gian, bước 5 phút, hệ số xe đến theo giờ/ngày/loại trạm, holiday multiplier, thời gian sạc, lỗi/sửa cổng, xác suất tuân theo gợi ý. Hệ số chưa chốt, A/B lựa chọn và ghi nguồn hoặc giả định; không dùng như số liệu Việt Nam đã đo.

## vehicles — `app/backend/modules/station_data/generated/vehicles.json`

`vehicle_id`, `origin`, `destination`, `depart_time`, `vehicle` gồm `soc_pct`, `battery_kwh`, `consumption_kwh_per_km`, `connector_type`. Tạo cố định 100 xe theo seed; lưu cùng background arrivals, sự cố và thời lượng dịch vụ để so sánh strategy công bằng.

## Runtime / artifacts

- Cửa sổ trạng thái hiện tại + lag: file nhỏ do A cung cấp cho inference replay.
- Tải ảo: dict theo trạm và bucket thời gian, giá trị tải kỳ vọng; có request_id, TTL và thời gian phiên sạc giả định.
- `app/backend/modules/prediction/artifacts/`: model, calibrator, feature order, version, training config. Không commit binary lớn.
- `app/backend/modules/simulation/results/`: kết quả simulation/metrics có seed, config và model version.
- `app/backend/infrastructure/cache/`: cache route có timestamp/TTL; không commit key hoặc toàn bộ raw response nhạy cảm.

Chỉ gộp/migrate dữ liệu Tasco sau khi validate schema, quyền dùng và chất lượng. Thiếu số cổng/thông số không tự coi là thông tin thật.
