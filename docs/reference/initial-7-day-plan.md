# Kế hoạch triển khai V-EV Flow — nhóm 4 người

Tài liệu căn cứ: `V-EV Flow – Proposal.md`. Mục tiêu là có **demo chạy thông suốt**, có so sánh với baseline và trình bày rõ giới hạn của dữ liệu mô phỏng. Tên Người 1–4 là chỗ trống để nhóm tự gán.

## 1. Chia người theo sản phẩm bàn giao

| Phụ trách | Vai trò | Công việc chính | Đầu ra phải bàn giao |
| --- | --- | --- | --- |
| **Người 1** | Data Engineering & Simulation | Chọn **một** hành lang, tổng hợp 10–20 trạm (tọa độ, số cổng, loại cổng, công suất); làm simulator tạo trạng thái trạm theo thời gian, số xe đến, thời gian sạc, ngày lễ và sự cố; xây dữ liệu huấn luyện, kiểm tra | `stations.json`, dữ liệu lịch sử (`history.parquet/csv`), `simulator.py`, `generate_data.py`, mô tả schema và các giả định |
| **Người 2** | AI/ML & Evaluation | Tạo nhãn *còn ít nhất một cổng phù hợp ở thời điểm ETA*; xây baseline và mô hình LightGBM/XGBoost, hiệu chỉnh xác suất; đánh giá tách theo thời gian; cung cấp hàm suy luận dự báo cho backend | Pipeline train/infer, model đã lưu, `predict_availability(station_id, arrival_time, current_state, ...)`, các chỉ số AUC/Brier và biểu đồ calibration |
| **Người 3** | Algorithm & Backend | Dùng xác suất từ Người 2 kết hợp ETA, SOC và cổng phù hợp để lọc/xếp hạng trạm; chọn trạm dự phòng, gợi ý lệch giờ; cập nhật tải ảo khi nhiều xe nhận gợi ý; so sánh baseline trong mô phỏng 100 xe; viết FastAPI | `POST /recommend`, `POST /simulate`, `POST /what-if` (sau MVP), kết quả JSON ổn định và ví dụ request/response |
| **Người 4** | Frontend/Map & Demo Integration | Làm web map (React/Next.js + Goong), nhập điểm đến/SOC, hiện trạm chính/dự phòng và xác suất tại ETA, lớp áp lực sạc, giao diện so sánh kịch bản; tích hợp API; dựng demo và slide | Giao diện web chạy được trên dữ liệu thật về vị trí trạm + dữ liệu mô phỏng về trạng thái; một kịch bản demo mạch lạc, slide/screenshot |

**Trách nhiệm chung:** Mỗi người viết 1 trang ngắn về phần mình làm và cung cấp ảnh/kết quả cho Người 4 tổng hợp. Người 3 chịu trách nhiệm chốt API contract; Người 1 và Người 2 phối hợp chốt schema/nhãn dữ liệu ngay ngày đầu. **Một người được chỉ định làm integrator** (đề xuất Người 3) để kiểm soát nhánh chính và xử lý lỗi giữa các mô-đun; không đẩy toàn bộ phần tích hợp cho Người 4.

## 2. MVP nên chốt

**Bắt buộc (P0 — có đủ để chấm demo):**

1. Một hành lang với 10–20 trạm trên bản đồ; trạng thái cổng **mô phỏng, ghi nhãn rõ**.
2. Dự báo xác suất có cổng **tại ETA**; so sánh với baseline gần nhất và đang trống.
3. Nhập SOC; hiển thị trạm đề xuất, trạm dự phòng, pin dự kiến khi đến.
4. Mô phỏng nhiều xe (ví dụ 100 xe) và so sánh ba chiến lược trên cùng kịch bản: gần nhất, đang trống, dự báo + phân bổ. Hiển thị tỷ lệ sạc thành công và km đi vòng.

**Làm sau khi P0 chạy ổn (P1):** gợi ý lệch giờ; lớp áp lực sạc với slider ngày thường/ngày lễ; giải thích lý do bằng các đặc trưng đơn giản; bảng *what-if* (thêm 2 cổng / chuyển 20% lượt sạc sang giờ khác).

**Để cuối (P2):** gợi ý mức sạc tối ưu theo đường cong sạc chi tiết; SHAP hoàn chỉnh; báo cáo cộng đồng; giao diện riêng cho đơn vị vận hành. Những mục này có trong proposal nhưng dễ gây quá tải lịch hackathon.

## 3. Hợp đồng tích hợp phải thống nhất trước khi code

**Dữ liệu trạm tối thiểu:** `station_id`, `name`, `lat`, `lon`, `connector_types`, `total_ports`, `working_ports`, `free_ports`, `power_kw` (và `timestamp`). Dữ liệu trạng thái tại thời gian t phải tách biệt với nhãn tương lai t+ETA.

**API chính (Người 3 tạo mock response từ ngày đầu để Người 4 làm song song):**

`POST /recommend`

```json
{
  "origin": {"lat": 10.8, "lon": 106.7},
  "destination": {"lat": 10.4, "lon": 107.1},
  "departure_time": "2026-10-10T09:00:00+07:00",
  "soc_pct": 20,
  "battery_kwh": 55,
  "consumption_kwh_per_100km": 16,
  "connector_type": "CCS2"
}
```

Response (ví dụ minh họa, không phải kết quả thật):

```json
{
  "recommended_station_id": "S02",
  "backup_station_id": "S03",
  "stations": [
    {
      "station_id": "S02",
      "eta_minutes": 35,
      "distance_km": 30,
      "arrival_soc_pct": 11.3,
      "availability_probability": 0.82,
      "recommended": true
    }
  ],
  "data_type": "simulated"
}
```

`POST /simulate` nhận `scenario`, `seed`, `vehicle_count`, `strategies`; trả kết quả từng chiến lược, gồm `success_rate`, `mean_detour_km`, `mean_wait_minutes`. Tái sử dụng **cùng kịch bản và seed** giữa các chiến lược để so sánh công bằng. `GET /stations` phục vụ bản đồ; `POST /what-if` triển khai ở P1.

**Lưu ý chất lượng khoa học:** Dự báo có nhãn t+ETA nhưng đặc trưng chỉ dùng thông tin có tại thời điểm t. Không dùng trạng thái tương lai để tạo feature. Chia train/test theo thời gian và nếu được, chạy thêm test trên tham số mô phỏng khác với tham số huấn luyện. Xác suất kết hợp của trạm chính + dự phòng trong proposal giả định hai trạm độc lập, nên khi demo cần nói rõ đây là ước lượng.

## 4. Lịch 7 ngày triển khai mẫu

| Thời điểm | Người 1: Dữ liệu | Người 2: ML | Người 3: Backend | Người 4: Frontend | Mốc kiểm tra chung |
| --- | --- | --- | --- | --- | --- |
| **Ngày 1** | Chốt hành lang, schema trạm và simulator | Chốt nhãn, baseline, schema feature | Chốt API contract, mock endpoint | Vẽ UI flow, tích hợp mock API | Chạy được frontend gọi mock backend |
| **Ngày 2–3** | Có 10–20 trạm, mô phỏng lịch sử và test scenario | Train baseline/model đầu tiên, xuất hàm predict | Viết SOC filter, ranking, trạm dự phòng | Hiện map, marker, thẻ kết quả | Luồng nhập SOC → nhận trạm trên mock/thật |
| **Ngày 4** | Hoàn thiện dữ liệu với giờ cao điểm/ngày lễ, fix seed | Tích hợp model vào backend, báo Brier/AUC | API `/recommend` chạy end-to-end | Hiển thị xác suất tại ETA, tuyến | **Đóng P0 phần khuyến nghị** |
| **Ngày 5** | Sinh 100 xe và event stream cùng seed | Phân tích sai số, kiểm tra calibration | Viết `/simulate`, baseline và phân bổ tải ảo | Màn hình so sánh 3 chiến lược | **Đóng P0 mô phỏng 100 xe** |
| **Ngày 6** | Hỗ trợ kịch bản lễ và what-if | Hỗ trợ giải thích kết quả | Thêm time-shift/what-if nếu kịp | Slider thời gian, pressure layer, slide | Chỉ nhận P1 nếu P0 đã chạy ổn |
| **Ngày 7** | Kiểm tra tính lặp lại dữ liệu | Chốt đồ thị, giới hạn | Smoke test API, chạy demo nhiều lần | Quay demo, hoàn thiện pitch | Demo 3–5 phút + kết quả có nguồn/giả định |

## 5. Tiêu chí nghiệm thu chung

- Từ đầu vào điểm đi, điểm đến và SOC, frontend gọi được backend, nhận và hiển thị trạm chính + trạm dự phòng, kèm ETA, xác suất và SOC dự kiến.
- Thay đổi tình huống (ngày thường/ngày lễ hoặc cổng hỏng) làm kết quả thay đổi có lý do; không hard-code cùng một trạm cho mọi đầu vào.
- Mô phỏng 100 xe tái lập được bằng `seed`; bảng so sánh dùng cùng tập tình huống và trình bày đầy đủ cả trường hợp thuật toán mới **không** thắng baseline.
- Mọi số liệu kết quả AI được gắn nhãn **đánh giá trên dữ liệu mô phỏng**; số liệu minh họa/giả định được phân biệt với dữ liệu trạm và ETA thực tế.
- Một lệnh chạy backend, một lệnh chạy frontend; repo có README, `.env.example`, dữ liệu mẫu và hướng dẫn demo để người khác tự chạy.

## 6. Họp và quản lý tiến độ

- Mỗi task có **owner, đầu ra, tiêu chí hoàn thành**. Thư mục hiện tại chưa được khởi tạo Git; khi nhóm tạo repo, dùng PR riêng và branch dạng `feat/data-simulator`, `feat/ml-predict`, `feat/recommend-api`, `feat/web-map`.
- Daily 10–15 phút: hôm qua giao gì, hôm nay giao gì, vướng dependency nào. Các quyết định schema/API cập nhật trong repo; không thay tên field tùy ý.
- Code review chéo: Người 1 ↔ Người 2 về dữ liệu/nhãn; Người 3 ↔ Người 4 về API/UI. Khi có xung đột, integrator chốt theo API contract.
- Cuối mỗi ngày luôn chạy demo chung. Một feature chỉ được xem là **Done** khi chạy được trên nhánh chính và có thể trình diễn, không chỉ khi code trong máy cá nhân đã xong.
