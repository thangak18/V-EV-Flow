# Ca inference đối chiếu cho Kiên / C5

**Bộ 24 kiểm tra gồm 19 ca file-runtime/loader và 5 ca capability-only; nguồn `simulated`.** Model chốt
`lightgbm-c721ddae6c9223ad` không bị train lại hoặc sửa binary/manifest/history.
Đây là kết quả gọi public Predictor + file repositories và lỗi loader,
**không phải kết quả kiểm thử HTTP `/api/predict`**.

## Fixture cố định

- Station: S001, CCS2.
- observed_at: `2026-10-13T16:00:00+07:00`.
- Scenario: normal, holiday_30_4, tet.
- ETA hợp lệ: 16:15, 16:30, 17:00 (+07:00).
- Artifact/data/version/checksum: [ARTIFACT_RELEASE.md](ARTIFACT_RELEASE.md).
- Full request/response/error: asset `inference-cases-c721ddae.json` ở private
  draft release trong [ARTIFACT_RELEASE.md](ARTIFACT_RELEASE.md). Report lịch sử
  có 24 ca; chạy lại CLI để nhận nhãn category/runtime_accepted mới.

5 ca partial-window chỉ kiểm khả năng imputation/reject-current của Predictor,
không phải hành vi runtime file được chấp nhận. Repository file vẫn từ chối
thiếu bất kỳ lag nào. Report ghi category, runtime_accepted và hai count riêng;
passed tổng chỉ nói các kiểm tra đạt kỳ vọng, không duyệt adapter partial mới.

Report có expected outcome, actual response/error, passed flag và xác nhận
input không bị đổi. Các lỗi thiếu/hỏng được tiêm vào **fixture tạm**, không phá
artifact đã bàn giao. Unit tests dùng model synthetic nhỏ riêng, không cần
binary production trong Git hoặc CI.

## 9 ca hợp lệ: output thực tế

Các response đều phải có model_version như trên, contract_version `0.1.0`,
`data_type=simulated`, `explanation_method=rule`, đúng station_id/ETA và reasons.
So sánh probability với tolerance tuyệt đối `1e-8` khi dùng **đúng release,
request và snapshots**; không dùng các giá trị này với model/metadata khác.

| Scenario | ETA / horizon | p_available thực tế |
| --- | --- | --- |
| normal | 16:15 / 15 phút | `0.9666233203294322` |
| normal | 16:30 / 30 phút | `0.9666233203294322` |
| normal | 17:00 / 60 phút | `0.9666233203294322` |
| holiday_30_4 | 16:15 / 15 phút | `0.7898318654923937` |
| holiday_30_4 | 16:30 / 30 phút | `0.7779005524861878` |
| holiday_30_4 | 17:00 / 60 phút | `0.7480851063829788` |
| tet | 16:15 / 15 phút | `0.29273084479371303` |
| tet | 16:30 / 30 phút | `0.30238726790450926` |
| tet | 17:00 / 60 phút | `0.33018867924528306` |

Normal cho cùng xác suất ở ba horizon tại snapshot này là output thực của
LightGBM/isotonic, không phải hard-code hoặc bảo đảm còn cổng; không yêu cầu
xác suất phải giảm theo horizon. Ba request vẫn có ETA và reasons riêng.

Request mẫu (normal/30 phút):

```json
{
  "station_id": "S001",
  "observed_at": "2026-10-13T16:00:00+07:00",
  "eta": "2026-10-13T16:30:00+07:00",
  "connector_type": "CCS2",
  "scenario": "normal"
}
```

## Thiếu lag và thiếu current: phân biệt hai lớp

Mọi ca lỗi/window partial bên dưới dùng normal/S001/horizon 30 phút. Complete
window chứa exact timestamps 16:00, 15:45, 15:30, 15:00 (+07:00).

| Ca | Cách kiểm tra | Output/lỗi mong đợi đã xác minh |
| --- | --- | --- |
| `partial_window_missing_15` | predictor_with_partial_window_fixture | Dự đoán `0.9666233203294322` |
| `partial_window_missing_30` | predictor_with_partial_window_fixture | Dự đoán `0.9666233203294322` |
| `partial_window_missing_60` | predictor_with_partial_window_fixture | Dự đoán `0.9666233203294322` |
| `partial_window_missing_15_30_60` | predictor_with_partial_window_fixture | Dự đoán `0.974169741697417` |
| `partial_window_missing_0` | predictor_with_partial_window_fixture | `ValueError`: `exactly one current status` |
| `file_repository_missing_15` | strict_file_repository | `DataSourceUnavailableError`: `missing status snapshots` |
| `file_repository_missing_30` | strict_file_repository | `DataSourceUnavailableError`: `missing status snapshots` |
| `file_repository_missing_60` | strict_file_repository | `DataSourceUnavailableError`: `missing status snapshots` |
| `file_repository_missing_0` | strict_file_repository | `DataSourceUnavailableError`: `missing status snapshots` |

**Chính sách hiện tại:** repository file yêu cầu đủ `(0,15,30,60)` nên trả
`DataSourceUnavailableError` trước khi Predictor impute. Các ca partial dùng
fixture repository lọc bỏ lag sau khi đọc window đầy đủ, chứng minh khả năng
imputation của model, **không chứng minh repository production đã hỗ trợ đó**.
Nếu muốn partial history ở runtime, Kiên cần adapter được review tương ứng;
không tự che lỗi nguồn hoặc dùng snapshot tương lai. Current luôn bắt buộc.

## ETA và model không load được

| Ca | Output/lỗi mong đợi đã xác minh |
| --- | --- |
| `invalid_horizon_65` | `ValueError`: `positive five-minute multiple <= 60 minutes` |
| `invalid_horizon_32` | `ValueError`: `positive five-minute multiple <= 60 minutes` |
| `artifact_missing_manifest` | `FileNotFoundError`: `manifest.json` |
| `artifact_missing_binary` | `FileNotFoundError`: `missing model artifact` |
| `artifact_bad_checksum` | `ValueError`: `SHA-256 checksum mismatch` |
| `artifact_invalid_manifest` | `ValueError`: `invalid model manifest` |

- Horizon 65 phút vượt maximum 60; 32 phút không theo bội 5. Không clip,
  không tự bucket trong Predictor; C5/adapter phải thống nhất chính sách ETA.
- Loader mất manifest/binary: FileNotFoundError. Checksum/manifest sai:
  ValueError. Loader không trả Predictor dùng được ở các ca này.
- Các ca artifact chạy tại bước load/startup, không phải gọi predict trên một
  instance đã load. Không kết luận toàn bộ lỗi deserialize/dependency đã được
  phủ chỉ từ bốn ca này.

## Lệnh chạy lại

Từ repo có `check_inference.py`, sau `make setup`. Giải nén bundle đã chốt
vào thư mục ignored như hướng dẫn artifact:

```bash
ML_RELEASE=app/backend/modules/prediction/artifacts/simulator-v1-lightgbm-c721ddae6c9223ad
uv run python -m app.backend.modules.prediction.check_inference \
  --model-dir "$ML_RELEASE/model" \
  --stations "$ML_RELEASE/data/stations.json" \
  --status "$ML_RELEASE/data/station_status.parquet" \
  --observed-at '2026-10-13T16:00:00+07:00' \
  --station-id S001 \
  --output app/backend/modules/prediction/artifacts/inference-cases-c721ddae.json
```

Exit 0: tất cả ca đạt. Exit 1: có verdict failed. Exit 2: setup/input/output
không dùng được. CLI từ chối output ghi đè model hoặc input data. Không commit
JSON report này. Chạy các unit tests nhỏ độc lập:

```bash
uv run pytest app/backend/modules/prediction/tests/test_check_inference.py -q
```

## Khi nối API: đề xuất mapping, chưa xác minh HTTP

| Lỗi/lớp | Hành vi Kiên cần triển khai/kiểm thử |
| --- | --- |
| Request horizon/timestamp/connector sai | Validation response 422 |
| Repository thiếu lag/current | Nguồn unavailable; mapping 503 theo policy API |
| Predictor thiếu current trong partial window | Internal source error; không map chung mọi ValueError thành 422 |
| Model không load được | Fail selected backend startup hoặc explicit unavailable/503; không fake fallback không nhãn |

Sau khi wire API, dùng đúng 9 payload phía trên để assert probability, version,
source, ETA; kiểm tra lỗi tương ứng theo API contract. Không expose stack trace
hay path nội bộ. Chạy lại với repositories/binding theo scenario cố định; không
sửa global scenario giữa request. Report 24 ca là bằng chứng inference kỹ thuật,
không phải benchmark mới hoặc chất lượng dự đoán trên dữ liệu vận hành thật.
