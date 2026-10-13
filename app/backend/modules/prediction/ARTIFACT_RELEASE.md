# Artifact ML đã chốt để bàn giao Kiên

**Nguồn: `simulated`, không phải dữ liệu vận hành thật.** Bộ này dùng thay
synthetic demo 3 trạm. Đây là kiểm tra/đóng gói lại model đã train, **không refit**
model hoặc calibrator, không chọn lại model dựa trên test.

## Phiên bản cố định

| Mục | Giá trị |
| --- | --- |
| Release | `simulator-v1-lightgbm-c721ddae6c9223ad` |
| Model | `lightgbm-c721ddae6c9223ad`, LightGBM 80 estimators |
| Calibrator | IsotonicRegression, chọn bằng calibration Brier |
| Source / data type | `bao-stateful-simulator` / `simulated` |
| Data version | `station-data-0.1.0`, kèm hash cụ thể trong release pin |
| Dữ liệu Bảo | 14 trạm CCS2 × 3 scenario × 14 ngày × 288 mốc/ngày = 169.344 dòng |
| Lịch sử | 30/09/2026 00:00 đến 13/10/2026 23:55, +07:00 |
| Scenario / seed | `normal`, `holiday_30_4`, `tet` / 42 |
| Horizon đã đánh giá | 15 / 30 / 60 phút; maximum 60 phút |
| Train/calibration/test | 288.918 / 107.352 / 107.856 nhãn ETA, embargo 60 phút |
| Model SHA-256 | `c721ddae6c9223ada849865a8528e2dc643a6822c0f443a02b95a57ae00223d0` |
| Bundle SHA-256 | `4943d86428e943e047d0e529f7d0aa386123bd3308232510d069f516ff1ed1dd` |
| Bundle size | 716.239 bytes |

[Bảng release đã chốt](releases/simulator-v1.md) giữ checksum model, manifest,
stations, history, producer manifest, fixture hash, dependency versions,
training/producer revision và source đã kiểm tra. `data_version` không đủ để
nhận diện một dataset nếu config/seed thay đổi: phải đối chiếu các hash đó.
Nguồn training `d0676d0`; producer main `d6dc06d`; đã xác minh tương thích tại
main `5c7ae8c55d99c8ec62c6989b457e29c41a93cee0`.

## Nhận bundle

File local đã đóng gói, nằm **ngoài checkout Git**:

`/Volumes/Thang/V-EV-Flow-deliveries/ml/simulator-v1-lightgbm-c721ddae6c9223ad.zip`

Thắng gửi file này cho Kiên qua kênh nhóm. ZIP không phải GitHub asset và chưa
được gửi tự động. Bản gốc `artifacts/simulator-v1/` vẫn giữ nguyên để rollback.
Không commit binary, Parquet hoặc generated fixtures.

Bundle chứa:

- `model/manifest.json` và `model/model-<sha256>.joblib`: LightGBM **cùng**
  isotonic calibrator, fitted feature builder, lag imputations và metadata.
  Không tách calibrator thành file riêng hoặc sửa/đổi tên model: loader kiểm
  tra pipeline và manifest như một cặp.
- `data/stations.json`, `data/station_status.parquet`, producer manifests và
  fixture bundles/config cho cả ba scenario.
- `runtime_versions.json`, `producer_scenarios.yaml`, reports train/test và
  holdout cũ. Các reports này là kết quả của model đã đóng băng, không phải
  lần train mới hoặc bằng chứng dữ liệu thực.
- `request.json`, `prediction.json`, `verification_predictions.json`: 126
  lượt inference mới qua repositories file đã merge của Kiên, trên dữ liệu
  simulator Bảo, không dùng fake predictor.
- `release.json`, `CHECKSUMS.sha256` và tài liệu bàn giao.

## Giải nén và kiểm tra

Dùng source hiện tại của main hoặc nhánh `feat/ml-predict`, sau `make setup`.
Đối chiếu SHA bundle trước khi load joblib; chỉ dùng artifact từ nguồn tin cậy.
Ví dụ từ root repo, thay `/path/to/` bằng nơi Kiên nhận file:

```bash
ML_BUNDLE=/path/to/simulator-v1-lightgbm-c721ddae6c9223ad.zip
shasum -a 256 "$ML_BUNDLE"
ML_RELEASE=app/backend/modules/prediction/artifacts/simulator-v1-lightgbm-c721ddae6c9223ad
# Chọn thư mục mới chưa tồn tại để tránh trộn với một release khác.
mkdir "$ML_RELEASE"
unzip "$ML_BUNDLE" -d "$ML_RELEASE"
(cd "$ML_RELEASE" && shasum -a 256 -c CHECKSUMS.sha256)
```

Binary nằm trong ignored `artifacts/`; release pin Markdown trong source chỉ chứa
metadata nhỏ. Linux có thể dùng `sha256sum` và `sha256sum -c` thay `shasum`.

## Load bằng repositories Kiên đã có

Không còn cần tên adapter giả định trong ví dụ này:

```python
from pathlib import Path
from app.backend.contracts.enums import DataType, Scenario
from app.backend.contracts.prediction import PredictRequest
from app.backend.infrastructure.repositories import (
    FileStationRepository,
    ParquetStatusRepository,
)
from app.backend.modules.prediction.public import load_predictor
from datetime import datetime

release = Path("app/backend/modules/prediction/artifacts/simulator-v1-lightgbm-c721ddae6c9223ad")
stations = FileStationRepository(release / "data/stations.json")
statuses = ParquetStatusRepository(
    release / "data/station_status.parquet", stations, Scenario.NORMAL
)
predictor = load_predictor(
    release / "model",
    statuses,
    stations,
    status_data_type=DataType.SIMULATED,
)
result = predictor.predict(
    PredictRequest(
        station_id="S001",
        observed_at=datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
        eta=datetime.fromisoformat("2026-10-13T16:30:00+07:00"),
        connector_type="CCS2",
        scenario=Scenario.NORMAL,
    )
)
print(result.model_dump(mode="json"))
```

Ví dụ mới xác minh: S001/normal/30 phút trả
`p_available=0.9666233203294322`, model version như trên,
`explanation_method=rule`, `data_type=simulated`.

Mỗi scenario có repository/binding cố định tương ứng; không dùng một global
scenario rồi sửa nó giữa các request. Predictor lấy `lags=(0,15,30,60)`.
`ParquetStatusRepository` hiện yêu cầu đủ exact snapshots; model có missing-lag
imputation nhưng adapter này không tự bỏ qua thiếu lịch sử. Khi thiếu dữ liệu,
để Kiên xử lý typed data-source error, không trả xác suất bịa.

Inference nhận horizon dương theo bội 5 phút, tối đa 60. 15/30/60 là các horizon
đã đo. ETA giây lẻ/horizon >60 không được silently clip; cần chính sách bucket
công khai hoặc fallback có nhãn, xem [SIMULATOR_HANDOFF.md](SIMULATOR_HANDOFF.md).

## Kiểm tra và giới hạn

- SHA-256 binary/manifest/data và length-framed fixture digest đều khớp;
  station metadata bundle khớp fixture trên main hiện tại.
- Loader xác minh manifest, metadata và feature order; dependency versions
  khớp môi trường training ghi trong `runtime_versions.json`.
- 126 lượt inference: 14 trạm × 3 scenario × 15/30/60 phút, xác suất `[0,1]`,
  version khớp và toàn bộ provenance `simulated`.
- ZIP CRC và checksum mọi file được kiểm tra; `CHECKSUMS.sha256` có thể kiểm
  tra lại sau giải nén. Đây là kiểm tra tính toàn vẹn, không phải chữ ký nguồn.
- Fresh baseline `make ci` exit 0 trước cập nhật tài liệu; kiểm tra cuối trên
  revision bàn giao ghi trong phản hồi/tài liệu kiểm tra riêng.
- Không chứng minh HTTP API đã wire model, chiến lược AI đã hoạt động, hoặc
  accuracy ngoài thực tế. Chỉ thay artifact bằng model/version khác sau khi
  có đánh giá phù hợp và cập nhật release pin; hiện không đổi model.

## Rollback

Giữ bundle trước đó `artifacts/simulator-v1-bundle.zip` và artifact gốc.
Rollback tích hợp bằng cách trỏ lại **cả thư mục model của version trước**;
không trộn binary/calibrator/manifest từ hai release. Nếu có lỗi load, báo lỗi
startup hoặc nguồn fallback rõ ràng; không âm thầm dùng fake predictor.
