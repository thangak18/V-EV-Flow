# Đề xuất tích hợp Predictor với Kiên — C5/C7/C8

**Trạng thái: đề xuất chờ Kiên xác nhận, không phải thỏa thuận đã được duyệt.**
Model chốt và data vẫn là `simulated`; không retrain hoặc đổi contracts.
Source main kiểm tra: `3db895894458b0a04b9bb4b820e2dcde4fc63977`.

## Điều đã có và điều chưa có

- Bảo đã sửa departure window ở #79; history train không đổi.
- Predictor, artifact và 24 ca local inference đã sẵn sàng.
- Kiên đã merge C3/C4, file repositories và Goong adapter/cache.
- `api/dependencies.build_container` vẫn chỉ cho mock/fake; chọn model/file
  hiện bị StartupConfigurationError. `/recommend` là Phase 0 placeholder;
  `/pressure` và `/simulate` còn mock. UI Driver gọi `/recommend`, không gọi
  `/predict` trực tiếp. Không gọi đây là toàn luồng ML/API/UI đã nối.
- PR #80 của Tú có ca UI injected để chuẩn bị tích hợp, không thay backend wiring.

## Snapshot và scenario — đề xuất bắt buộc rõ nguồn

1. `observed_at` lấy theo mốc replay snapshot +07:00, bội 5 phút. Không thay bằng
   clock máy hoặc dùng snapshot tương lai.
2. Predictor yêu cầu `(0,15,30,60)` phút: current + exact past lags cùng station,
   scenario, capacity, metadata và phiên bản dữ liệu.
3. Bind một repository/predictor cố định cho mỗi scenario. Chọn instance theo
   `request.scenario`; không đổi mutable global scenario giữa request.
4. Dùng file repositories hiện có thì thiếu bất kỳ lag/current đều có thể ra
   DataSourceUnavailableError. Partial-window imputation chỉ áp dụng nếu adapter
   thực sự trả được partial window; không giấu lỗi bằng số 0 hoặc snapshot gần nhất.
5. Dữ liệu artifact chốt kết thúc **13/10/2026 23:55 +07:00**. Dùng ca replay
   `13/10 16:00`, không dùng clock ngày 14/10 rồi coi missing history là lỗi model.
6. Parquet chốt là background replay. Nếu runner thêm 100 xe, phải ghi rõ model
   đang dựa vào background snapshot, hoặc phối hợp Bảo cung cấp public live-history
   source. Không đọc simulator private state hay gán nhãn live cho background.

## Chính sách ETA gửi Kiên xác nhận

- Giữ `eta_actual` từ routing để báo hành trình; predictor dùng `eta_bucket`.
- Với snapshot `t`, `h = ceil((eta_actual - t) / 5 phút) * 5 phút`; chỉ dùng nếu
  `0 < h <= 60`. Đây là xấp xỉ thời điểm, không bảo đảm thận trọng về xác suất.
- Ceil có thể dự báo sau lúc xe đến gần 5 phút: nếu cổng được giải phóng trong
  khoảng đó, xác suất có thể lạc quan. Floor/nearest cũng có sai số; lấy min của
  hai bucket là một heuristic chưa được đánh giá, không còn là xác suất đã
  calibrate tại ETA thật. Không tự đổi sang heuristic đó hoặc gọi ceil là an toàn.
  Kiên cần xác nhận chính sách và UI/reasons phải hiển thị thời điểm đánh giá.
- Ví dụ t=16:00: ETA 16:30 -> bucket 16:30; 16:31:01 -> 16:35;
  16:59 -> 17:00; 17:00:01 -> 17:05 -> **unsupported**, không clip 17:00.
- 15/30/60 là horizon đã đánh giá; runtime có nhận bội 5 khác, nhưng các horizon
  trung gian chưa có bảng benchmark riêng. Ghi đây là xấp xỉ và giới hạn trong reasons.
- Khi gọi `/predict` trực tiếp, dùng ETA bucket hợp lệ; response ETA giữ đúng
  request. Đối với `/recommend`, Kiên giữ actual ETA trong Plan và nêu rõ thời
  điểm xác suất được đánh giá trong reasons; không đổi shared DTO tùy tiện.
- Candidate vượt horizon: Kiên chốt loại candidate có lý do hoặc fallback được
  duyệt/có nhãn. Không âm thầm fake probability hoặc làm cả request thất bại
  chỉ vì một candidate xa nếu còn candidate được hỗ trợ.
- Ngưỡng SOC hiệu lực của C3 và RankingConfig C4 phải đồng nhất. `p_available`
  giữ nguyên xác suất model; tải ảo chỉ tác động score, không giả làm calibration.

## Kiểm tra HTTP parity đã chuẩn bị

Tạo expected report bằng `check_inference` như [INFERENCE_CASES.md](INFERENCE_CASES.md),
rồi chạy từ root trên API Kiên đã wire:

```bash
uv run python -m app.backend.modules.prediction.check_api \
  --api-base-url http://127.0.0.1:8000/api/ \
  --expected-report app/backend/modules/prediction/artifacts/inference-cases-c721ddae.json \
  --output app/backend/modules/prediction/artifacts/http-parity.json
```

Tool gửi 9 payload hợp lệ, kiểm station/ETA, version, provenance, contract,
reasons/explanation_method và xác suất với absolute tolerance 1e-8.
Scope report ghi rõ chưa kiểm HTTP error mapping 404/422/503, thiếu history
hay startup artifact lỗi; parity xanh không thay bộ kiểm thử các lỗi này. Không thay payload hoặc dự đoán hộ API.
Exit 0: match; exit 1: mismatch/HTTP error; exit 2: setup/report không hợp lệ.
Report không được ghi đè expected file. Không commit generated outputs.

## Kết quả thật của lần chuẩn bị

- Local file repositories/loader/capability: 24 kiểm tra lịch sử đạt (19 runtime/loader, 5 capability-only); artifact không đổi.
- API local dùng composition mặc định: `/ready` báo mock/fake/fake;
  HTTP parity **0/9 match**, vì model_version/data_type/probability là fake.
  Đây là xác nhận wiring chưa có, không phải model đã train bị sai.
- Bind model thật vào container **chỉ trong TestClient tạm**: HTTP `/predict`
  **9/9 match** direct inference, cả ba scenario; không sửa API source.
- Trong test-only binding trên, horizon 65 phút ra **HTTP 500** vì ValueError
  từ model chưa được API adapter phân loại. Kiên cần mapping request sai ->422,
  source/model unavailable ->503; không map tất cả ValueError thành 422.
- Chưa chạy thành công full Data -> model -> recommend API -> UI bằng runtime
  wiring thật. Không dùng injected UI fixtures thay bằng chứng tích hợp đó.

Bằng chứng ngoài Git: assets `http-parity-current-api.json` và
`http-parity-temporary-model-binding.json` trên private draft release được dẫn
ở [ARTIFACT_RELEASE.md](ARTIFACT_RELEASE.md). Đây là report lịch sử trước thay
đổi kiểm tra reasons; chạy lại CLI trên revision hiện tại để xác nhận mới.

## Checklist chạy khi Kiên đã nối xong

- `/ready` phản ánh đúng backend file/model/route được chọn, không còn binding fake ngoài chủ ý.
- 9 ca `/predict` phải đạt parity; thêm 404/422/503, thiếu lag/current và startup artifact hỏng.
- Gọi `/recommend` với replay/scenario đã chốt, xác minh model_version là artifact,
  source đúng thực tế và trạm khả thi; không còn phase0_placeholder/fake-v1.
- Với primary/backup: đối chiếu p_available với direct Predictor tại bucket thực
  đã dùng, giữ ETA thật và giải thích xấp xỉ. Không chỉ assert HTTP 200.
- UI hiển thị đúng station, ETA +07:00, probability, version/source; no-plan/error
  có lý do và retry; dùng backend thật, không Playwright route.fulfill cho ca này.
- `/simulate`: ba chiến lược, cùng fixture/seed/100 xe; chạy với runner Bảo sau #79,
  ghi rõ availability background hay live, không lấy FakeSimulationRunner làm kết quả AI.

Kiên vui lòng xác nhận chính sách ETA/scenario và thông báo PR wiring + lệnh bật
runtime. Thắng chạy HTTP parity và UI end-to-end trên revision đó khi sẵn sàng.
