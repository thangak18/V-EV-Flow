# Flow demo P0 đã kiểm tra

Hai màn hình dùng cùng backend file/model/stateful. Dữ liệu trạm/trạng thái và
model là **simulated**; Goong chỉ cung cấp bản đồ/đường đi, không cung cấp trạng
thái cổng trực tiếp. What-if, lệch giờ và SHAP vẫn là P1 theo `docs/SCOPE.md`.

## Chuẩn bị

1. Cài frozen dependencies bằng `make setup`; nhận release theo
   `app/backend/modules/prediction/ARTIFACT_RELEASE.md` và kiểm tra checksum.
2. `.env` local có `VITE_GOONG_MAP_KEY` loại Maptiles và `GOONG_REST_API_KEY`
   loại API Key/REST. Hai loại không thay thế nhau. Không đưa REST key vào VITE_*.
3. Dùng `VITE_API_BASE_URL=/api` để frontend đi qua proxy cùng origin; tránh
   trỏ thẳng sang :8000 rồi gặp CORS khi đổi cổng preview.
4. Khởi động backend theo `docs/runbooks/runtime-integration.md`, thêm
   `--route-backend goong`. Khởi động frontend bằng npm dev. Trên UI phải thấy
   “Chỉ đường tài xế: Goong · Mô hình đã huấn luyện”. Dòng này cho biết cấu hình,
   không phải kiểm tra kết nối live; request thực mới xác nhận được dịch vụ.
5. Chọn mốc replay `2026-10-13T16:00:00+07:00`, không dùng giờ máy hiện tại.

Nếu dùng offline, chọn `--route-backend fake` một cách tường minh. UI hiện rõ
khoảng cách/ETA giả định; không tự fallback rồi giữ nhãn Goong khi provider lỗi.
Maptiles key sai/không có mạng vẫn có danh sách điểm để tiếp tục demo.

## Flow Tài xế (khoảng 1 phút)

1. Bấm **Đặt lại demo**. Màn hình trở về “Chưa tìm trạm sạc”, không tự phân bổ.
2. Giữ TP.HCM → Vũng Tàu, ngày thường, CCS2, pin **20%**. Phần Thông số xe cho
   xem pin 60 kWh, tiêu hao và thời điểm replay đang dùng.
3. Bấm **Tìm kế hoạch sạc** đúng một lần. Chờ kết quả route/inference; lần đầu
   Goong/cache lạnh chậm hơn các lượt sau. UI khóa submit khi đang xử lý.
4. Chỉ ra trạm chính, xác suất **tại ETA**, pin khi đến và trạm dự phòng. Các
   lý do tiếng Việt cho biết pin/khả thi, bucket ETA và giả định độc lập của hai
   trạm; xác suất là ước lượng, không phải bảo đảm đặt được cổng.
5. Bấm **Xem trạm trên bản đồ** để tới vùng bản đồ và danh sách điểm. Mở Chi tiết
   kỹ thuật nếu cần đối chiếu `lightgbm-c721ddae6c9223ad` và phương pháp phân bổ.
6. Nhập pin **0%**, bấm tìm lại: UI phải bỏ kế hoạch/marker cũ và hiện lý do
   không đủ pin. Đổi về 20%, tìm lại phải phục hồi được.
7. Bấm Đặt lại demo để luyện lại cùng điều kiện. Một ý định mới có request ID
   mới; retry của cùng request giữ ID. Reset lỗi không được xóa kết quả đang xem.

Đã kiểm tra live Directions V2 bằng API Key đúng loại: HTTP 200. Lượt cold
`/recommend` đầu tiên khoảng 7,1 giây, primary S001 cách 1,062 km, backup S003,
model `lightgbm-c721ddae6c9223ad`. Không hard-code các trạm/số này vào UI: load
ảo và tuyến khác có thể đổi lựa chọn. Không ghi key vào report hoặc video.

## Flow Điều hành (khoảng 1 phút)

1. Mở **Điều hành**, chọn **Tết**, giữ giờ replay rồi bấm **Áp dụng kịch bản**.
   Bản đồ hiện 14 trạm và rủi ro thiếu cổng theo model. Pressure = 1 − p tại
   horizon 30 phút; đây không phải số xe chờ hay occupancy trực tiếp.
2. Giữ **seed 42 / 100 xe**, bấm **So sánh 3 chiến lược**. Cả ba dùng cùng
   fixture hash nhưng engine và allocation riêng, tách khỏi flow Tài xế.
3. Đọc tỷ lệ có cổng ngay khi đến, thời gian chờ, đường vòng và số thất bại.
   Bản chạy simulated đã kiểm tra: nearest 44%, currently_available 58%, AI64%.
   AI đổi thêm đường vòng để giảm chờ; không tuyên bố AI luôn thắng.
4. Mở **Chi tiết mô phỏng**: AI mang version LightGBM; baseline có version
   simulated-baseline-v1; cả ba fixture hash phải giống nhau.
5. Giải thích nhãn nguồn: AI đọc snapshot nền; currently_available đọc engine
   có cả 100 xe. Không trình bày đây là kết quả đo ngoài thực tế.

## Video dự phòng và kiểm thử

`e2e/demo-flow.spec.ts` chạy hai hành trình trên, thêm kiểm tra reset không gọi
recommend ngầm, no-plan xóa kết quả và các con số UI khớp response simulator.
Mặc định các test dùng server do Playwright quản lý, không cần key/video:

```bash
npm --prefix app/frontend run test:e2e -- e2e/demo-flow.spec.ts
make ci
```

Để ghi backup với Goong/model thật, khởi động live demo trước rồi chạy test này
với một Playwright config local chọn live baseURL, `testMatch: demo-flow.spec.ts`,
`workers:1`, viewport 1280×900, không khai báo webServer, và RECORD_DEMO=1.
Test sẽ giữ mỗi màn hình vài giây để dễ xem lại. Không intercept API responses
hoặc thay model/metric; video/browser chỉ chứa dữ liệu demo, không có key.
Đường dẫn screenshot dùng testInfo.outputPath, video ở outputDir của test.
Bản ghi local có cả WebM và MP4; giữ ngoài Git cùng artifact demo.

Lệnh tối thiểu với config local đã chuẩn bị:

```bash
RECORD_DEMO=1 npm --prefix app/frontend run test:e2e -- --config /path/to/live-demo.config.mjs
```

Cấu hình phải import defineConfig từ package Playwright đã cài trong repo và trỏ
testDir vào `app/frontend/e2e`. Không cài thêm package hoặc commit config có key.
Full CI và source branch vẫn cần review trước khi merge.
