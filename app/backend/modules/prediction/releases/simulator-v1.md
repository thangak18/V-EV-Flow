# Release pin: simulator-v1

Bản ghi reviewable; manifest JSON máy đọc nằm trong bundle ngoài Git (`release.json` và `model/manifest.json`). Các chuỗi SHA-256 dưới đây là checksum công khai của dữ liệu mô phỏng và artifact, không phải credentials.

| Field | Pinned value |
| --- | --- |
| release_id | `simulator-v1-lightgbm-c721ddae6c9223ad` |
| model_version | `lightgbm-c721ddae6c9223ad` |
| calibration_method | `isotonic` |
| data_type | `simulated` |
| source | `bao-stateful-simulator` |
| data_version | `station-data-0.1.0` |
| model_file | `model/model-c721ddae6c9223ada849865a8528e2dc643a6822c0f443a02b95a57ae00223d0.joblib` |
| binary_sha256 | `c721ddae6c9223ada849865a8528e2dc643a6822c0f443a02b95a57ae00223d0` |
| fixture_hash | `0c1e0cccfe3016021685edd8733513bcdbdfa35921c13baf625813d47e330146` |
| history_sha256 | `61ebaad53268fa51c0bd46360092f3decc811f911f957aba0cb7e83df9d3e5c3` |
| stations_sha256 | `43412b09a7fd3fda238b32a68761b77f4b699f7500437200b05f629eab0ce7a7` |
| producer_manifest_sha256 | `d43e1eec20393d8d8d94ed9a3a691fa0221f8345d9427c6d01b85dd56dfe0088` |
| model_manifest_sha256 | `6d5b4e9ca43fda87ead1f9566694f43d913c0718579f89791194bb8f04af2fde` |
| runtime_versions_sha256 | `4f0bdf073d40897d9403333de31350a4ad0108deb70011e676096f63e39f4d57` |
| training_source_revision | `d0676d07846898be3acd08b52ab274bb86705d6f` |
| producer_main_revision | `d6dc06d03ab331c42aa6b336dddeeff8c9326a62` |
| verified_source_revision | `5c7ae8c55d99c8ec62c6989b457e29c41a93cee0` |
| uv_lock_sha256 | `b716bdb72d3c1795499ce375d7d5a614df11eeeaeca2d1b2de82a59faf61fd8b` |
| bundle_filename | `simulator-v1-lightgbm-c721ddae6c9223ad.zip` |
| bundle_sha256 | `4943d86428e943e047d0e529f7d0aa386123bd3308232510d069f516ff1ed1dd` |
| bundle_bytes | `716239` |
| station_count | `14` |
| status_rows | `169344` |
| history_start | `2026-09-30T00:00:00+07:00` |
| history_end | `2026-10-13T23:55:00+07:00` |
| history_days_per_scenario | `14` |
| step_minutes | `5` |
| seed | `42` |
| maximum_horizon_minutes | `60` |
| verified_prediction_count | `126` |

## Dataset and runtime

- Scenario: normal, holiday_30_4, tet.
- Horizon đã đánh giá: 15/30/60 phút.
- Split counts: train 288.918; calibration 107.352; test 107.856.
- Repositories đã smoke: FileStationRepository và ParquetStatusRepository.
- LightGBM và calibrator isotonic nằm chung joblib với feature builder; không tách/rename.

| Library | Training and verified runtime |
| --- | --- |
| lightgbm | `4.7.0` |
| scikit-learn | `1.9.1` |
| numpy | `2.4.6` |
| pandas | `3.0.6` |
| joblib | `1.6.0` |
| pydantic | `2.14.0` |
| pyarrow | `26.0.0` |

Python training: 3.11.17. Xem [ARTIFACT_RELEASE.md](../ARTIFACT_RELEASE.md) và SIMULATOR_REPORT.md để biết thao tác load, đánh giá và giới hạn. Không refit model/calibrator trong lần đóng gói này.
