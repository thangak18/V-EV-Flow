# Smarter Mobility — benchmark lịch sử công khai

Nguồn: **real — lịch sử trạng thái tổng hợp Belib Paris**. Đây là benchmark offline riêng, không thay predictor/artifact simulated, API, simulator hay UI của demo.

## Nguồn và kiểm tra dữ liệu

- [Dataset và code của tác giả](https://gitlab.com/smarter-mobility-data-challenge/tutorials).
- [Bài báo mô tả dữ liệu, trạng thái và giấy phép ODbL](https://data.mlr.press/assets/pdf/v01-16.pdf), phần 2 và cuối phần 1.
- Upstream commit: `a431cae1c15887b1fd6ecc43157c48012faced42`; input `0. Input Data/train.csv`.
- Git blob đã kiểm tra từ bytes tải về: `8e9cd8ba72bd842325383d567086d60a777734e0`.
- SHA-256 CSV: `0c19fda8d2cb7c83b8df2ddbbc82298f6f0234f69fd387b045cfbb537e071f2a`; 171,754,453 bytes. CLI chỉ chấp nhận đúng checksum nguồn đã audit; fixtures phải được khai báo `mock` trong Python tests.
- 1,851,083 dòng, 91 trạm, 231 ngày: `2020-07-03 00:00:00` → `2021-02-18 23:45:00`. Bước gốc 15 phút, tổng bốn trạng thái luôn bằng 3 chỗ/trạm.
- Không có ô trống trong các cột CSV, không có khóa station/time trùng. Có 166,933 station/tick thiếu so với lưới đầy đủ trên toàn khoảng thời gian; chi tiết mỗi trạm nằm trong JSON kết quả.
- Loại 6,528 dòng của ngày chuyển giờ `2020-10-25`. Còn 1,844,555 snapshot dùng cho benchmark. Không nội suy snapshot hoặc outcome thiếu.
- `test.csv` upstream chỉ có lịch và metadata, không có bốn trạng thái để tính metric; không dùng làm test có nhãn. Tập test của benchmark là phần cuối của `train.csv` upstream.

| Trạng thái gốc | Cách xử lý |
| --- | --- |
| Available | Số chỗ được báo đang khả dụng; target tại ETA bằng 1 nếu >0 |
| Charging | Giữ số đang sạc |
| Passive | Giữ riêng số xe đang cắm nhưng không sạc; vẫn chiếm chỗ |
| Other | Giữ riêng; gồm reserved/offline/out-of-order, tuyệt đối không đổi thành broken |

Các cột `tod/dow/trend`, tọa độ, postcode và area được audit nhưng không ép vào schema simulated. Đặc trưng lịch được tính lại từ timestamp; không có thông tin theo connector.

## Thiết kế và tránh leakage

`smarter_data.py` tạo bảng benchmark riêng, không phải adapter runtime `StationStatus`. Timestamp CSV không có timezone; giữ **source-clock** và không gắn nhãn UTC, Europe/Paris hoặc +07:00 khi chưa có bằng chứng. Đây là ngoại lệ có chủ đích cho phân tích dữ liệu nguồn, không thay quy tắc timezone của API.

- Ba model độc lập cho ETA 15/30/60 phút; target join đúng `(Station, t+h)`, bỏ mẫu không có đúng outcome. Lag join đúng `(Station, t−15/30/60)`, không shift theo số dòng.
- Features: 4 trạng thái hiện tại, 4 trạng thái tại mỗi lag, cờ thiếu lag, sin/cos giờ, thứ, station code. LightGBM dùng missing-value handling gốc; station category mapping chỉ fit trên train.
- Cutoffs được chọn trước: train_end `2020-12-01 00:00`, calibration_end `2021-01-10 00:00`. Bỏ 60 phút observation trước mỗi cutoff cho mọi horizon; train/calibration ETA kết thúc trước observation đầu của tập sau.
- Hyperparameters cố định: 120 trees, learning_rate 0.05, 15 leaves, min_child_samples 50, lambda 1, seed 42, 2 CPU workers, deterministic histogram. Không chọn hyperparameter theo test.
- Platt và isotonic chỉ fit trên calibration, chọn theo calibration Brier (tie chọn Platt); cả ba horizon chọn isotonic. Test chỉ dùng để báo cáo.
- Persistence dùng `Available>0` tại t; hourly-rate học tỷ lệ target theo giờ ETA trên train, fallback global train rate. Các hàng so sánh dùng đúng cùng test rows của từng horizon.

| ETA | Train | Calibration | Test | Mẫu không có ETA đúng | Mẫu embargo |
| --- | ---: | ---: | ---: | ---: | ---: |
| 15 phút | 1,244,318 | 289,793 | 308,640 | 1,172 | 632 |
| 30 phút | 1,243,901 | 289,657 | 308,403 | 1,962 | 632 |
| 60 phút | 1,243,128 | 289,441 | 307,977 | 3,377 | 632 |

Test từ `2021-01-10 00:15` đến snapshot cuối có outcome tương ứng ngày `2021-02-18`. Tỷ lệ target dương khoảng 74,07%. Các horizon dùng chung nhiều snapshot nên không cộng số mẫu thành số quan sát độc lập.

## Kết quả thực thi

Brier, Log Loss và ECE càng thấp càng tốt; AUC càng cao càng tốt. Calibration dùng 10 bins cố định. Pooled theo station/time, chưa có khoảng tin cậy hoặc đánh giá trạm chưa từng thấy.

| ETA | Phương pháp | Brier | Log Loss | AUC | ECE |
| --- | --- | ---: | ---: | ---: | ---: |
| 15 phút | lightgbm_raw | 0.024152 | 0.100525 | 0.985694 | 0.007119 |
| 15 phút | lightgbm_calibrated | 0.024535 | 0.100859 | 0.985739 | 0.006550 |
| 15 phút | persistence | 0.030006 | 1.081520 | 0.960937 | 0.030006 |
| 15 phút | hourly_rate | 0.194600 | 0.579681 | 0.521797 | 0.052600 |
| 30 phút | lightgbm_raw | 0.033868 | 0.134223 | 0.978256 | 0.010789 |
| 30 phút | lightgbm_calibrated | 0.034986 | 0.135699 | 0.978265 | 0.012086 |
| 30 phút | persistence | 0.045369 | 1.635272 | 0.940903 | 0.045369 |
| 30 phút | hourly_rate | 0.194600 | 0.579677 | 0.521867 | 0.052573 |
| 60 phút | lightgbm_raw | 0.040291 | 0.158293 | 0.970531 | 0.014828 |
| 60 phút | lightgbm_calibrated | 0.041788 | 0.160202 | 0.970477 | 0.017671 |
| 60 phút | persistence | 0.055465 | 1.999168 | 0.927689 | 0.055465 |
| 60 phút | hourly_rate | 0.194585 | 0.579636 | 0.522087 | 0.052506 |

**Nhận xét:** model calibrated tốt hơn hai baseline ở cả ba horizon. Tuy nhiên Brier/Log Loss test hơi kém raw ở cả ba horizon và ECE kém raw ở 30/60 phút. Hiệu chỉnh trên calibration không bảo đảm cải thiện giai đoạn sau. Giữ nguyên lựa chọn đã chốt trên calibration; không đổi model theo test để làm đẹp kết quả.

Trong JSON bàn giao, hash được ghi kèm tiền tố thuật toán `sha256:`, `git:` hoặc `git-blob:`; manifest ignored giữ hex thuần để kiểm tra bytes. Các literal checksum nguồn công khai đã xác minh được annotate tại đúng dòng Python cho secret scanner, không nới baseline/tooling chung.

Từng bin reliability (count, xác suất trung bình, tỷ lệ outcome), calibration scores, khoảng split, thiếu dữ liệu theo trạm, feature order, versions và checksum artifact nằm trong [SMARTER_BENCHMARK_RESULTS.json](SMARTER_BENCHMARK_RESULTS.json). Hai lần train deterministic cho kết quả metric giống nhau; round-trip joblib khớp 32 prediction test mỗi horizon (atol 1e-12).

## Chạy lại và xem tập dữ liệu

Từ root worktree, sau `make setup`:

```bash
mkdir -p app/backend/modules/prediction/artifacts/smarter-source
curl --fail --location --max-time 180 \
  "https://gitlab.com/api/v4/projects/40194980/repository/blobs/8e9cd8ba72bd842325383d567086d60a777734e0/raw" \
  --output app/backend/modules/prediction/artifacts/smarter-source/train.csv
uv run python -m app.backend.modules.prediction.smarter_benchmark \
  --csv app/backend/modules/prediction/artifacts/smarter-source/train.csv \
  --output app/backend/modules/prediction/artifacts/smarter-v1-reproduction \
  --train-end '2020-12-01 00:00:00' \
  --calibration-end '2021-01-10 00:00:00'
```

Bản đã train ở `app/backend/modules/prediction/artifacts/smarter-v1-final/`:

- `model-{15,30,60}m.joblib`: model, calibrator, ordered features, train-fitted station categories và hourly baseline; `manifest.json` chứa metadata/checksum.
- `train-*.parquet`, `calibration-*.parquet`, `test-*.parquet`: khóa nguồn + observed_at + ETA + target của từng partition. Join `(Station, observed_at)` với `(Station, date)` của CSV để xem trạng thái/lag; đây là label partitions, không phải toàn bộ feature matrix.
- `predictions-*.parquet`: test labels kèm xác suất của cả bốn phương pháp. Binaries, source CSV và Parquet đều giữ ngoài Git.

Không load joblib không tin cậy. CLI từ chối ghi đè thư mục đã có manifest. Để rollback, bỏ thư mục benchmark hoặc revert commit benchmark; demo/API hiện tại không đổi.

## Giới hạn và bàn giao

- Dự báo **trạng thái Available được ghi nhận**, không xác nhận vật lý cổng còn chỗ; Other có phần offline/unknown nên không đồng nghĩa chắc chắn hết chỗ.
- Đây là các trạm Paris cùng giai đoạn 2020–2021, nhiều trạng thái kéo dài; AUC cao không chứng minh khả năng dự báo trạm mới, giao thông Việt Nam hay phiên sạc thực tế.
- Dataset đã được tác giả làm tròn timestamp tới 15 phút. Không có offset/fold hoặc thời điểm dữ liệu thực sự đến hệ thống. Loại ngày DST là cách bảo thủ; chưa chứng minh snapshot có thể nhận đúng t trên một feed realtime. Giả định có snapshot t là điều kiện của benchmark ngắn hạn này; challenge gốc dự báo nhiều tuần và không dùng cùng protocol, nên không so leaderboard.
- Chưa biết cổng khả dụng thuộc connector nào; không đưa model này vào gợi ý CCS2 hay simulator 100 xe. Không ép Other thành broken, không tự sinh công suất/connector cho Paris.
- Không tích hợp model này vào `load_predictor`, không kiểm chứng đặt chỗ vật lý, không thay artifact simulated. Cần adapter runtime/connector và validation dữ liệu triển khai trước khi cân nhắc thay.

## Xác minh

- Base: `75b8ea6a5823746fea93c8744a4da04ea66a9ef0`.
- `make setup`: exit 0; `make ci` trước sửa: exit 0.
- Focused ML suite trước lượt kiểm tra cuối: 188 passed; các test mới riêng: 6 passed. Fixtures unit test được khai báo mock.
- Kết quả fresh full CI trên revision hoàn tất được ghi trong bàn giao cuối; không coi dòng này là xác nhận CI đã chạy cho revision đó.
