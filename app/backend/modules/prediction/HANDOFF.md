# Bàn giao Predictor cho Kiên

**Bộ artifact đã chốt:** [ARTIFACT_RELEASE.md](ARTIFACT_RELEASE.md) — version/hash cố định, ZIP ngoài Git và ví dụ load qua file repositories đã có của Kiên.

**Artifact khuyên dùng hiện tại:** [model từ simulator Bảo](SIMULATOR_HANDOFF.md),
14 trạm và 14 ngày/kịch bản. Phần demo synthetic bên dưới giữ để chạy smoke
nhỏ; không dùng nó thay model simulator khi tích hợp mới.

Module này cung cấp mô hình và shared `Predictor` port. Kiên tích hợp vào
composition root/API; tài liệu này không đổi DTO, OpenAPI hay route handlers.
Backend trên main vẫn chọn fake predictor cho đến khi Kiên thay binding.

## Model demo và cách tạo lại

Dùng source cùng phiên bản artifact trên nhánh `feat/ml-predict` của PR bàn
giao này (hoặc main sau khi PR đó merge). Main trước PR chưa có Log Loss
trong report metadata, nên không dùng loader cũ để đọc bundle mới.

Từ root repo sau `make setup`:

```bash
uv run python -m app.backend.modules.prediction.demo
```

Mặc định seed 42, 7 ngày, 3 trạm, 3 scenario, horizon train 15/30/60 phút.
Output nằm trong `app/backend/modules/prediction/artifacts/synthetic-demo/`:

- `model/manifest.json`, `model/model-<sha256>.joblib`: toàn pipeline LightGBM,
  calibrator, feature builder và metadata. Loader dùng `model/`, không dùng
  thư mục cha. Không đổi tên binary hoặc sửa manifest khi copy.
- `stations.json`, `station_status.parquet`, `fixture_config.json`: dữ liệu
  và cấu hình synthetic để thử repositories; không commit.
- `request.json`, `prediction.json`, `report.md`: ví dụ và bảng đánh giá.

Chỉ load joblib từ nguồn tin cậy. Binary/dataset được Git-ignore. Chạy lại cùng
seed/config/dependencies tạo cùng fixture/predictions; creation time của
manifest có thể khác. `DEMO_REPORT.md` là báo cáo reviewable của một lần chạy.
Để Kiên dùng được trên máy khác, copy cả output folder hoặc bundle ZIP; cũng
có thể chạy generator tại máy Kiên. Sau khi có dữ liệu Bảo, train bằng CLI
trên dữ liệu đó và thay nguyên thư mục model; không gọi demo này là model thật.

Nguồn: `synthetic-correlated-integration-demo-v1`, data_type `simulated`.
Session/repair timers của từng port được giữ qua các tick; fixture không có
hàng đợi, routing, 100 xe hay so sánh strategy. Đây không phải simulator của
Bảo hoặc dữ liệu đối tác. Không dùng scores để chứng minh độ chính xác thực tế.

## Binding Predictor

```python
from pathlib import Path
from app.backend.contracts.enums import DataType
from app.backend.contracts.ports import Predictor, StationRepository, StatusRepository
from app.backend.modules.prediction.public import load_predictor


def make_predictor(
    model_dir: Path,
    statuses: StatusRepository,
    stations: StationRepository,
) -> Predictor:
    return load_predictor(
        model_dir,
        status_repository=statuses,
        station_repository=stations,
        status_data_type=DataType.SIMULATED,
    )
```

Load một lần ở composition/startup, sau đó gọi `predictor.predict(request)`.
StatusWindow v0 không có provenance: caller phải truyền đúng status_data_type.
Training/status type khác nhau trả `mixed`. Đừng silently fallback sang fake
model khi artifact lỗi. Có thể giữ mode fake riêng, với nhãn mock rõ ràng.

`StatusRepository.window` hiện không nhận scenario argument. Bind nguồn
history với scenario của request trước khi gọi Predictor; ví dụ lưu một
Predictor cho mỗi scenario với repository bound cố định. Không dùng biến
scenario global mutable vì concurrent requests có thể lấy nhầm lịch sử.

## Input repositories và thời gian

StationRepository: `get_station(id)` và `list_stations()`. Metadata capacity,
power và encoded station type phải khớp lúc train. Demo dùng trạm S001–S003,
chỉ CCS2; metadata trạm khác không tự phù hợp với artifact này.

Predictor gọi:

```python
statuses.window(station_id, observed_at, lags=(0, 15, 30, 60))
```

Nguồn trả `StatusWindow` chứa đúng station/observed_at, cùng scenario request,
các snapshots tại t, t-15, t-30, t-60 phút. Lag 0 bắt buộc và chỉ có một row.
Thiếu lag quá khứ: dùng imputation đã fit trên train + missing indicators.
Thiếu current: từ chối. Future rows, timestamp khác, duplicate keys, capacity
sai, scenario khác: từ chối. Không dùng nearest/as-of hoặc clock hiện tại.

Giờ +07:00; observed_at align bucket 5 phút. Horizon dương, nguyên bội 5 phút,
không quá manifest split `max_horizon_minutes` (demo 60). Runtime nhận 5–60;
demo train trên 15/30/60, nên ưu tiên đúng ba horizon đó. Chưa đánh giá chất
lượng tại các horizon còn lại. Không silently round ETA nhận từ routing.
Mixed-connector aggregates không đủ để xác định cổng tương thích: chưa hỗ trợ.

## Request/response và smoke CLI

Ví dụ request dùng được với fixture mặc định:

```json
{
  "station_id": "S001",
  "observed_at": "2026-10-18T12:00:00+07:00",
  "eta": "2026-10-18T12:30:00+07:00",
  "connector_type": "CCS2",
  "scenario": "normal"
}
```

`PredictionResult` có station_id, eta, p_available trong [0,1], reasons,
explanation_method `rule`, model_version, data_type và contract_version.
Response thực, không hard-code probability, nằm trong `prediction.json` và
`DEMO_REPORT.md`. Rule reasons là context; không phải SHAP từng mẫu.

```bash
uv run python -m app.backend.modules.prediction.cli predict \
  --stations app/backend/modules/prediction/artifacts/synthetic-demo/stations.json \
  --status app/backend/modules/prediction/artifacts/synthetic-demo/station_status.parquet \
  --model-dir app/backend/modules/prediction/artifacts/synthetic-demo/model \
  --station-id S001 --observed-at '2026-10-18T12:00:00+07:00' \
  --eta '2026-10-18T12:30:00+07:00' --connector-type CCS2 \
  --scenario normal --status-data-type simulated
```

Sau khi Kiên wire API, cùng payload có thể POST `/api/predict`. CLI smoke
không chứng minh endpoint hiện tại đã dùng model; endpoint đó vẫn cần Kiên
viết integration test với artifact/repositories thực.

## Lỗi để API xử lý

| Tình huống | Module hiện tại | Mapping đề xuất cho Kiên |
| --- | --- | --- |
| Request sai timestamp/horizon/connector | Pydantic validation / ValueError | 422 |
| Station không tồn tại | Lỗi lookup của repository, thường KeyError | 404 |
| Artifact thiếu/checksum/schema/contract không khớp | FileNotFoundError / ValueError | Startup unavailable; 503 khi gọi |
| Current snapshot thiếu, history invalid, metadata đã đổi | ValueError | Source/model unavailable; 503 |
| Lag quá khứ thiếu | Predictor impute nếu repository trả partial window; ParquetStatusRepository hiện báo DataSourceUnavailableError | Tùy adapter: dự đoán hoặc source unavailable (503 theo policy) |
| Joblib không deserialize được | Lỗi serialization/dependency | Startup unavailable; 503, log internal details |

Không map mọi ValueError sang cùng status: phân biệt validation request và
nguồn/model invalid ở adapter/composition. Module không trả HTTP status.
Không trả stack trace/file paths nội bộ cho frontend. Với metadata/capacity
mới cần retrain hoặc artifact phù hợp; không sửa feature values trong model.

## Đánh giá và compatibility

Brier và Log Loss thấp hơn là tốt hơn; AUC cao hơn khi có hai lớp. Log Loss
là binary negative log likelihood (natural log); sklearn clip p=0/1 theo
float64 epsilon để penalty hữu hạn. Labels [0,1] được khai báo rõ nên vẫn tính
được khi holdout chỉ có một lớp; AUC lúc đó là null. Calibration bins và ECE
vẫn có sample counts. Không chọn model/calibrator từ test scores.

Report cũ chưa có Log Loss được giữ nguyên với `log_loss=None`/không có key;
loader vẫn đọc được metadata cũ, không tự tạo score mới từ dữ liệu không còn.
Report mới có Log Loss trong train/evaluate JSON và manifest. Shared prediction
response và contract version không đổi.

Kiên cần kiểm tra end-to-end: load model → bind đúng scenario → request →
probability/model version/provenance khớp CLI; test 404/422/503, thiếu current,
missing past lags và startup model lỗi. Không cần Goong hoặc dữ liệu Bảo để
thử binding demo. Khi dữ liệu Bảo đến, đối chiếu schema và training lại rồi
thực hiện integration proof với nguồn simulator đó.

## Ca inference đối chiếu C5

Xem [INFERENCE_CASES.md](INFERENCE_CASES.md): 9 payload hợp lệ và 15 ca partial/file history, horizon, loader failure; lệnh chạy lại và output/lỗi thực tế. Không phải proof HTTP wiring.
