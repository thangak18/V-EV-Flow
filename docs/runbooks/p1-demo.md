# Demo P1: what-if, gợi ý lệch giờ, TreeSHAP

Bộ này xây trên PR #85 (P0 flow/reset). Cùng model/calibrator đã chốt
`lightgbm-c721ddae6c9223ad`, dữ liệu simulated 14 trạm × 3 scenario × 14 ngày;
không refit, đổi feature order hoặc chọn model lại từ kết quả demo.

## Chạy

Sau `make setup`, giải nén release tin cậy theo ARTIFACT_RELEASE.md. `.env` local
có Maptiles Key ở VITE_GOONG_MAP_KEY và **API Key/REST** ở GOONG_REST_API_KEY.
VITE_API_BASE_URL=/api dùng proxy cùng origin, không đưa REST key vào frontend.

```bash
uv run python -m app.backend.api.demo --release-dir /path/to/simulator-v1 \
  --route-backend goong --port 8000
npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173
```

Launcher chọn file/model/stateful, bật prediction_explanations và
 time_shift_suggestions. Uvicorn factory cũ giữ hai flags false nếu không set
PREDICTION_EXPLANATIONS=true / TIME_SHIFT_SUGGESTIONS=true. Offline dùng
--route-backend fake có nhãn rõ; không fallback âm thầm khi Goong lỗi.

Mốc replay là 2026-10-13T16:00:00+07:00, không dùng giờ máy hiện tại. Cấu hình
preview hiện tại có thể dùng backend :8010 và Vite :5175 proxy /api sang :8010;
chỉ đổi cổng/config local, không mở rộng CORS hay commit env/key.

## Flow Tài xế

1. Đặt lại demo, giữ pin 20%, CCS2 và hành lang mặc định; bấm tìm đúng một lần.
2. Mở **Vì sao có xác suất này? (TreeSHAP)**. Năm bar thể hiện đóng góp có dấu
   lớn nhất trên điểm raw margin/log-odds. API mang đủ 29 features + bias, tổng
   khớp raw_score; calibrated_probability vẫn là xác suất đã phục vụ trước P1.
3. Đây không phải % tác động, không phải giải thích calibrator và không phải
   quan hệ nhân quả. Dùng [LightGBM native pred_contrib](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Booster.html), không cài package SHAP hoặc refit artifact.
4. Gợi ý lệch giờ probe 15/30 phút với cùng snapshot hiện tại, không đọc tương
   lai hoặc hỏi Goong lại cho các probe. Travel time giữ cố định, không dự báo
   traffic tương lai. Chỉ gợi ý nếu primary tăng ít nhất 5 điểm % và ETA <=
   horizon model. Current plan/reservation không bị thay hay nhân đôi.
5. Nếu không có cải thiện đủ lớn, UI nói rõ chưa có giờ lệch phù hợp. Trong các
   case replay đã rà với artifact hiện tại, chưa thấy gợi ý đủ ngưỡng; không
   hạ ngưỡng hay bịa ví dụ tích cực để demo. Nhánh có gợi ý dương được test bằng
   predictor kiểm soát và fixture UI; đó không phải số đo mô hình thật.

## Flow Điều hành — what-if

Chọn Tết, seed42, 100 xe. Panel what-if đọc draft seed/count hiện tại, kể cả khi
chưa bấm compare; draft trống/thập phân/âm bị chặn. Kết quả giữ metadata request
đã chạy, không đổi nhãn thành draft mới khi input thay đổi.

- **Thêm 2 cổng S001 / AI allocation:** hai engine có cùng nền/xe/seed nhưng
  capacity khác; xếp hạng dùng working capacity mới, predictor vẫn dùng lịch sử
  và metadata capacity gốc. Không gọi đây là dự báo ML đã retrain cho trạm mới.
- **Dịch 20% xe sang 21h:** dịch đúng floor(N×fraction) ID foreground theo seed
  sang 21:00–21:55 cuối window, giữ SOC/compliance và events nền. UI ghi count
  thực (20 với 100 xe), không làm thay đổi mẫu số hoặc drop xe thất bại.
- Trước/sau phải cùng event fixture/model/strategy/scenario/seed/mẫu số; config
  hash khác nhau, state tách khỏi Driver. Chạy lại cùng request cho kết quả y hệt.
- Simulator dùng road-distance/speed giả định như P0, không dùng Goong traffic;
  AI thấy snapshot nền, currently_available thấy engine có cả foreground.

### Đã chạy trên artifact thật (simulated, một seed)

| Tết, 100 xe, seed42 / AI | Có cổng ngay khi đến | Chờ trung bình | Xe thất bại |
| --- | ---: | ---: | ---: |
| Trước thay đổi | 64% | 7,85 phút | 12 |
| Thêm 2 cổng S001 | 74% | 4,75 phút | 5 |
| Dịch 20 xe sang 21h | 63% | 7,75 phút | 15 |

Không mặc định thay đổi luôn tốt hơn: dịch giờ đã làm tỷ lệ thành công kém đi
trong case này. Đây không phải kết quả vận hành thật hay cam kết nâng capacity.

## Migration và kiểm thử

Đây là PR contract P1 riêng: POST /whatif trước chỉ trả 503 và chưa có body;
nay thí nghiệm nhận body typed với discriminator kind rõ ràng. Client cũ không
gửi body (hoặc null) vẫn nhận 503, không tự chạy mặc định; body có nội dung sai
schema trả 422, valid request ở mock trả 503, station không có trả 404. Consumer cũ strict-parse cần
cập nhật cùng backend khi bật optional explanation/shift fields. Binary giữ
contract 0.1.0; không đổi manifest/model/calibrator để bật tính năng runtime.

Canonical: make setup; focused tests; make ci. API examples đã model-validate;
OpenAPI sinh từ FastAPI, TypeScript sinh từ OpenAPI, không hand-edit generated.
Default CI dùng tiny artifact tạm cho integration và route-injected UI fixtures.
Hai live P1 tests skip nếu thiếu P1_LIVE=1; không coi skip là kiểm thử model thật.

Live Playwright config local: baseURL preview live, workers1, viewport1280×900,
testDir app/frontend/e2e, testMatch p1-live.spec.ts, không webServer. Ví dụ:

```bash
P1_LIVE=1 RECORD_DEMO=1 npm --prefix app/frontend run test:e2e -- --config /path/to/live-p1.config.mjs
```

Không intercept API responses. Tests kiểm tra actual SHAP additivity/calibrated
probability, no-improvement hoặc positive hint thật, 2 what-if ×100 xe, hash,
model version, số xe dịch và UI khớp response. Video/ảnh output local ngoài Git.

Rollback: revert PR này hoặc tắt hai prediction flags và quay về P0 frontend;
what-if có thể giữ 503 bằng mode fake. Không xóa artifact hay sửa file histories.
Chỉ hỗ trợ một worker; chưa deploy production hoặc có dữ liệu charger thật.
