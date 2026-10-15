# Runtime tích hợp: simulator → calibrated model → API → UI

Nguồn **simulated**, không phải dữ liệu vận hành thật. Base tích hợp `83295ec`
(main sau #78/#80/#81/#82). Không thay model/calibrator đã bàn giao, không refit
hoặc chọn tham số theo bảng test. Model pin: `lightgbm-c721ddae6c9223ad`,
isotonic, data version `station-data-0.1.0`; checksum và nguồn nhận nằm trong
[ARTIFACT_RELEASE](../../app/backend/modules/prediction/ARTIFACT_RELEASE.md).

## Chạy trên laptop

Sau `make setup`, nhận và kiểm tra SHA của ZIP từ private release, rồi giải nén.
Thư mục release chứa `model/`, `data/`, `producer_scenarios.yaml`. Binary và
Parquet nằm ngoài Git. Ví dụ từ root repository, terminal backend:

```bash
uv run python -m app.backend.api.demo \
  --release-dir /absolute/path/to/simulator-v1 --port 8000
```

Launcher dùng file/model/stateful và một worker, tạo bản sao dữ liệu simulated
trong thư mục tạm riêng cho tiến trình; release gốc giữ nguyên. Dừng bằng Ctrl+C.
Mặc định route là giả định hình học (`fake`), không phải chỉ đường thực tế.
Nếu muốn Goong và đã cấu hình key backend ngoài Git, thêm `--route-backend goong`.
Goong maptiles key frontend vẫn cần cấu hình riêng trong `.env`.

Terminal frontend:

```bash
npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173
```

Mở `http://127.0.0.1:5173`. Chọn giờ replay `2026-10-13T16:00:00+07:00`;
chưa tự chuyển sang giờ máy. FE gửi `/api` qua Vite proxy tới backend 8000.
Chọn scenario, bấm tìm kế hoạch hoặc áp dụng áp lực, rồi so sánh seed 42 / 100 xe.
Driver hiển thị version model trong Chi tiết kỹ thuật; Operator có nhãn simulated
và model/fixture trong Chi tiết mô phỏng. Header chỉ ghi Bản demo; nguồn ở từng
kết quả lấy theo API, tránh nhãn mock cố định che nguồn simulated.

## Cấu hình trực tiếp bằng uvicorn

Defaults vẫn mock/fake để CI và offline smoke không cần binary. Muốn chọn chế
độ đầy đủ bằng factory hiện có:

```bash
DATA_BACKEND=file DATA_DIR=/path/to/data-root \
PREDICTOR_BACKEND=model MODEL_DIR=/path/to/release/model \
SIMULATION_BACKEND=stateful \
SIMULATION_SCENARIOS_PATH=/path/to/release/producer_scenarios.yaml \
ROUTE_BACKEND=fake \
uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

`DATA_DIR/generated/` phải chứa stations, history và producer manifest; release
ban đầu đặt chúng ở `data/`. Launcher phía trên tự xử lý khác biệt này. Model
phải hỗ trợ đủ ba scenario; horizon từ manifest phải hỗ trợ pressure 30 phút.
Không dùng `FAKE_PREDICTION_HORIZON_MINUTES` để kéo dài khả năng của model.
Chọn model với mock data, hoặc stateful với fake prediction sẽ bị từ chối.
Artifact thiếu/hỏng sai checksum làm startup fail, không fallback âm thầm.

## Ngữ nghĩa và công bằng so sánh

- Driver có repository và Predictor cố định riêng cho từng scenario. Load model
  bao gồm fitted features/lag medians, LightGBM và calibrator trong cùng joblib.
  API kiểm tra horizon thực tế của artifact, không extrapolate hoặc clip >60.
- Driver file repository yêu cầu đủ exact current + lags. Thiếu snapshot trả
  typed 503, không lấy scenario khác hoặc đọc snapshot tương lai.
- Simulator tạo fixture từ public producer, đúng full scenario YAML, window từ
  producer manifest, seed và vehicle count request. Cùng bộ tham số cho cả ba
  strategy tạo cùng fixture hash; đổi seed/count sẽ tạo cả nền tương ứng.
- Mỗi lượt có engine, selection và expected-load riêng. Không chia sẻ state
  Driver; retry mô phỏng tái tạo cùng kết quả, reset Driver không đổi simulation.
- `nearest` và `currently_available` là baseline thực; baseline có version
  `simulated-baseline-v1`. AI dùng `RecommendationAllocationStrategy` với duration
  thực theo giả định runner, working capacity hiện tại (cổng không hỏng) và tải
  dự kiến từ các lựa chọn trước trong chính lượt chạy. Không dùng FakeAllocation.
- Để cùng phạm vi model, cả ba loại bỏ candidate có travel horizon >60 trước
  inference; xe không còn candidate được tính thất bại trong mẫu số. Candidate
  horizon hợp lệ được ceil tới bucket 5 phút (zero-distance tối thiểu 5 phút);
  runner vẫn giữ ETA vật lý khi tính đến trạm/chờ. 5/10/20… được model chấp nhận
  nhưng chỉ 15/30/60 đã có đánh giá riêng trong release.
- Model đọc **background replay** từ chính fixture seed/count của lượt chạy,
  không có 100 xe được thêm vào engine. `currently_available` đọc live engine.
  Hai nguồn có khác biệt này; UI nêu rõ, không coi đây là thử nghiệm ngoài đời.
- AI dự báo snapshot nền có thể dùng missing-lag imputation; current bắt buộc.
  Khi bắt đầu replay hoặc lag thiếu, adapter chỉ đưa các snapshot quá khứ có sẵn.
- Giữ giả định runner: 1.3 × khoảng cách thẳng, 50 km/h, SOC reserve theo cấu
  hình ranking, compliance trong scenario, chờ tối đa 30 phút, không rẽ backup.
  Driver fake routes dùng giả định riêng, không phải đường Goong đã xác minh.
- Success là có cổng ngay khi đến; xe sạc sau khi chờ không là success nhưng
  cũng không nhất thiết failed. Không cộng success và failed rồi bắt buộc bằng 100.

## Kiểm thử lặp lại

```bash
uv run pytest app/backend/tests/integration/test_runtime_pipeline.py -q
make ci
```

Integration tests tự train model nhỏ **simulated** trong thư mục tạm để kiểm tra
9 ca inference qua API, parity với public Predictor, version/source, HTTP
404/422/503, idempotency/reset, chiến lược thật/hash/replay/seed và state isolation.
Không commit model test. Default E2E giữ fake mode và bỏ qua hai opt-in tests.

Để chạy Chromium với artifact thật, tạo data-root với layout `generated/` như
trên (có thể copy `release/data`), dừng server trên 8000/4173 do chính mình mở:

```bash
DATA_BACKEND=file DATA_DIR=/path/to/data-root \
PREDICTOR_BACKEND=model MODEL_DIR=/path/to/release/model \
SIMULATION_BACKEND=stateful \
SIMULATION_SCENARIOS_PATH=/path/to/release/producer_scenarios.yaml \
ROUTE_BACKEND=fake \
npm --prefix app/frontend run test:e2e -- e2e/runtime-integration.spec.ts
```

Playwright tự chạy API + build/preview, **không intercept API responses**.
Driver kiểm tra xác suất render theo response thật và đúng version/source;
Operator chạy cả ba scenario × ba strategy × 100 xe, kiểm tra fixture hash,
seed/count/version và pressure có khác theo scenario. Maps CDN bị chặn có chủ
đích để kiểm tra fallback danh sách; đây không phải kiểm thử Goong live.
Screenshots lưu ignored `app/frontend/test-results/runtime-*.png`.

Bảng chạy thực tế seed42/100 xe ở [stateful-runtime.json](../results/stateful-runtime.json):

| Scenario | Nearest | Currently available | AI allocation |
| --- | ---: | ---: | ---: |
| normal | 90% | 93% | 97% |
| holiday_30_4 | 58% | 75% | 82% |
| tet | 44% | 58% | 64% |

Đây là kết quả mô phỏng của một seed với các giả định trên, không phải bằng
chứng AI luôn tốt hơn. AI đổi thêm đường vòng để giảm chờ; giữ đủ metrics trong
JSON và UI. Không chỉnh thuật toán để cố đạt các tỷ lệ này.

## Giới hạn và rollback

What-if, time-shift, charge-to guidance vẫn P1; chưa làm trong đợt nối này.
Không deploy production hoặc bảo đảm accuracy ngoài đời. Goong network/key
thật chưa được kiểm thử trong đợt này. Simulator có lock riêng để serialize lượt
chạy và cache nền giới hạn 4 bộ fixture/8192 prediction mỗi bộ; dùng một worker.

Rollback bằng revert PR tích hợp hoặc chọn lại `PREDICTOR_BACKEND=fake` và
`SIMULATION_BACKEND=fake` cùng mode dữ liệu phù hợp. UI nhận mock phải hiện nhãn
mock. Không đổi artifact pin hoặc trộn model/calibrator/manifest giữa các bản.
