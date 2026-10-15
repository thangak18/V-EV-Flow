# Bàn giao model từ simulator Bảo cho Kiên

**Bộ artifact đã chốt:** [ARTIFACT_RELEASE.md](ARTIFACT_RELEASE.md) — version/hash cố định, ZIP ngoài Git và ví dụ load qua file repositories đã có của Kiên.

**Dùng artifact này thay demo `synthetic-correlated-integration-demo-v1`.**
Nguồn mới là `bao-stateful-simulator`, data version `station-data-0.1.0`,
14 trạm CCS2, 3 kịch bản, seed 42 và 14 ngày lịch sử. Đây vẫn là **simulated**:
không có dữ liệu vận hành/đối tác hay độ chính xác ngoài đường thực tế.
Điểm số, split, calibration và giới hạn: [SIMULATOR_REPORT.md](SIMULATOR_REPORT.md).

## Nhận và load

Bundle `simulator-v1-bundle.zip` nằm ngoài Git trong
`app/backend/modules/prediction/artifacts/`. Giải nén vào
`app/backend/modules/prediction/artifacts/simulator-v1/` hoặc thư mục riêng.
Bundle có model joblib, manifest, metadata 14 trạm, producer fixtures/config,
Parquet, validation/test/holdout reports và public-port inference proof.
Không rename binary hoặc chỉnh manifest. Không commit các file này.

Dùng source ML cùng phiên bản trên nhánh `feat/ml-predict` (PR #65), hoặc
main sau khi PR đó merge. Main trước PR chưa có Log Loss trong metadata và
loader cũ không đảm bảo đọc được bundle mới. Bản model:
`lightgbm-c721ddae6c9223ad`; calibrator isotonic; contract 0.1.0.

```python
from pathlib import Path
from app.backend.contracts.enums import DataType
from app.backend.modules.prediction.public import load_predictor

predictor = load_predictor(
    Path("app/backend/modules/prediction/artifacts/simulator-v1/model"),
    status_repository=status_repo_bound_to_request_scenario,
    station_repository=station_repo_for_bundle_stations,
    status_data_type=DataType.SIMULATED,
)
```

`status_repo_bound_to_request_scenario` và `station_repo_for_bundle_stations`
là adapters do Kiên cung cấp, không phải tên class đã có. Port signature,
provenance và HTTP error mapping nằm trong [HANDOFF.md](HANDOFF.md).
Giữ một binding riêng/cố định cho mỗi scenario; không đổi global scenario.
Model đã fit metadata 14 trạm của Bảo; không dùng metadata 3 trạm demo cũ.

Đã chạy 126 lượt qua `simulation.public.build_status_window` → shared
StatusRepository → Predictor trên 14 trạm × 3 scenario × 15/30/60 phút.
Tất cả bounded [0,1] và data_type simulated. Đây là smoke file/history;
chưa chứng minh API hoặc `ai_allocation` runner đã wire đúng.

## Trạng thái và ETA của runner

- Repository phải trả current và exact lag 15/30/60 phút theo observed_at:
  Predictor yêu cầu `lags=(0,15,30,60)`. Nếu dùng public helper của Bảo,
  translate `lags` thành `lag_minutes`, truyền scenario rõ ràng.
- `build_status_window` của Bảo hiện raise ValueError khi bất kỳ lag nào thiếu.
  Model có thể impute missing past lags, nhưng adapter muốn tận dụng điều đó
  cần trả phần lag có sẵn; current vẫn bắt buộc. History đầy đủ đủ lag sau
  60 phút đầu, nên smoke hiện không gặp trường hợp đó.
- Model train horizons 15/30/60; runtime chấp nhận bội dương của 5 phút, tối đa
  60 phút. Ưu tiên đúng ba horizon đã đánh giá. Không extrapolate >60 phút.
- Runner tính ETA từ distance/speed và có thể có phút/giây lẻ. Không nối trực
  tiếp mọi ETA đó vào Predictor: sẽ bị ValueError. Kiên cần chốt chính sách
  bucket ETA rõ ràng ở adapter, ví dụ ceil lên mốc 5 phút relative to observed_at,
  giữ ETA chuyến đi thực riêng và ghi đây là xấp xỉ. Nếu bucket vượt 60 phút,
  cần model horizon dài hơn hoặc fallback có nhãn rõ; không silently clip.
- `availability(station_id, observed_at, eta)` cần bind scenario và snapshot
  source. Parquet hiện là background replay. Nếu runner thêm 100 xe/AI làm
  đổi queues/ports, dùng live history source hoặc ghi rõ model dựa trên
  background snapshot; đừng đọc runner private state hay future snapshots.
- Không gọi results ở đây là so sánh nearest/currently_available/AI. Kiên còn
  cần wire strategy và availability vào runner, rồi chạy fair comparison với
  cùng fixture hash; data/model manifests không tự tạo strategy đó.

## Reproduce training

Chạy từ root sau `make setup`, bằng đúng source/config của lần bàn giao.
Model dùng cấu hình LightGBM mặc định hiện tại; không tuning theo test.

```bash
ML_SIM_DIR=app/backend/modules/prediction/artifacts/simulator-v1
uv run python -m app.backend.modules.station_data.cli generate \
  --scenario all --seed 42 --history-days 14 \
  --history-end '2026-10-13T23:55:00+07:00' --output "$ML_SIM_DIR/data"
uv run python -m app.backend.modules.simulation.cli history --input "$ML_SIM_DIR/data"
uv run python -m app.backend.modules.prediction.cli train \
  --stations "$ML_SIM_DIR/data/stations.json" \
  --status "$ML_SIM_DIR/data/station_status.parquet" \
  --artifact-dir "$ML_SIM_DIR/model" --horizons 15,30,60 \
  --train-end '2026-10-08T00:00:00+07:00' \
  --calibration-end '2026-10-11T00:00:00+07:00' \
  --source bao-stateful-simulator --data-type simulated \
  --data-version station-data-0.1.0 --seed 42 > "$ML_SIM_DIR/train_report.json"
```

Nếu generation config/source/dependencies đổi thì phải ghi data/model version
mới; không giả định cùng seed luôn cho cùng kết quả giữa các phiên bản code.
Manifest publication time thay đổi khi chạy lại. Không chọn calibrator bằng
bảng test; isotonic được chọn theo calibration Brier, không theo test.

## Later-seed holdout (frozen model)

```bash
uv run python -m app.backend.modules.station_data.cli generate \
  --scenario all --seed 91 --history-days 7 \
  --history-end '2026-10-27T23:55:00+07:00' --output "$ML_SIM_DIR/holdout"
uv run python -m app.backend.modules.simulation.cli history --input "$ML_SIM_DIR/holdout"
uv run python -m app.backend.modules.prediction.cli evaluate \
  --stations "$ML_SIM_DIR/holdout/stations.json" \
  --status "$ML_SIM_DIR/holdout/station_status.parquet" \
  --model-dir "$ML_SIM_DIR/model" --horizons 15,30,60 \
  --source bao-stateful-simulator-later-seed91 --data-type simulated --seed 91 \
  > "$ML_SIM_DIR/holdout_report.json"
```

Same simulator parameters, later timeline/new events; không phải stress test
với peak/outage mới hoặc real-world validation. Không refit model/calibrator
hay hourly baseline trên holdout này.

## Request mẫu / CLI smoke

```json
{
  "station_id": "S001",
  "observed_at": "2026-10-13T16:00:00+07:00",
  "eta": "2026-10-13T16:30:00+07:00",
  "connector_type": "CCS2",
  "scenario": "normal"
}
```

```bash
uv run python -m app.backend.modules.prediction.cli predict \
  --stations "$ML_SIM_DIR/data/stations.json" \
  --status "$ML_SIM_DIR/data/station_status.parquet" --model-dir "$ML_SIM_DIR/model" \
  --station-id S001 --observed-at '2026-10-13T16:00:00+07:00' \
  --eta '2026-10-13T16:30:00+07:00' --connector-type CCS2 \
  --scenario normal --status-data-type simulated
```

Response thật của bundle: p_available 0.9666233203294322, model_version
lightgbm-c721ddae6c9223ad, explanation_method rule, data_type simulated.
Đây là xác suất model, không phải bảo đảm có cổng; file `prediction.json` giữ
response đầy đủ. API integration test cần assert version/provenance/payload
match CLI và các lỗi 404/422/503, không chỉ assert HTTP 200 từ fake predictor.
