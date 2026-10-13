# Báo cáo tổng hợp: Vai A (Data & Simulator) — 12/10/2026

Người phụ trách: Bảo. Nhánh: `feat/data-simulator`. Phạm vi: `app/backend/modules/station_data` và `app/backend/modules/simulation`.

## 1. Tóm tắt

Trong ngày 12/10, ba PR của lane A đã được tạo, cùng hai PR tiền đề nhỏ để gỡ các test dùng chung. Luồng Data → ML → API → UI không còn bị chặn ở khâu dữ liệu và mô phỏng.

| PR | Nội dung | Gỡ chặn cho | Trạng thái |
| --- | --- | --- | --- |
| [#66](https://github.com/thangak18/V-EV-Flow/pull/66) | Nới test số trạm trong `test_station_contracts.py` | Lane A | Đã merge |
| [#67](https://github.com/thangak18/V-EV-Flow/pull/67) | Cố định fixture của `test_split.py` ở 2 trạm | Lane A, Thắng | Đã merge |
| [#68](https://github.com/thangak18/V-EV-Flow/pull/68) (PR-A1) | 14 trạm, loader, generator, manifest | Kiên, Tú, Thắng | Đã merge |
| [#69](https://github.com/thangak18/V-EV-Flow/pull/69) (PR-A2) | Engine, lịch sử Parquet, lệnh sinh dữ liệu | Thắng | Đã merge |
| [#70](https://github.com/thangak18/V-EV-Flow/pull/70) (PR-A3) | Baseline, runner 100 xe, lệnh `compare` | Kiên, Tú | Đã merge |

Tất cả PR của lane A đều có `make ci` exit 0 trên cây sạch tại HEAD được ghi trong PR body. Bản cuối (PR-A3, HEAD `d7c4759`): 282 test backend pass, coverage 95% (ngưỡng bắt buộc là 75%).

## 2. Bước chuẩn bị và hai PR tiền đề

Môi trường thiếu thư viện OpenMP nên LightGBM không tải được, làm 4 file test của `prediction` lỗi khi thu thập. Đã cài `libomp` bằng Homebrew; sau đó baseline đầy đủ là 206 test pass.

Mở rộng `stations.json` từ 2 lên 14 trạm làm vỡ hai test nằm ngoài lane A. Theo `AGENTS.md`, thay đổi dùng chung phải đi qua nhánh `codex/` và PR riêng có review, nên đã tách thành:

- **#66:** `test_station_contracts.py` kiểm tra "2–20 trạm, ID duy nhất, có S001 và S002" thay vì đúng 2 trạm.
- **#67:** `prediction/tests/test_split.py` lấy 2 trạm đầu (`[:2]`) vì test này assert số dòng cố định cho 2 trạm.

## 3. PR-A1: dữ liệu v0 (#68)

- **Trạm:** 14 trạm `S001…S014` trên hành lang TP.HCM–Vũng Tàu, chuẩn CCS2, ID `S001`/`S002` giữ nguyên. Mỗi trạm có `source` và `assumptions`; vị trí, số cổng và công suất là giả định, không phải dữ liệu quan sát.
- **Loader (`loaders.py`):** `load_stations`, `load_scenarios`, `load_scenario_specs`. `ScenarioSpec` nội bộ chứa các tham số mà contract `ScenarioConfig` không có (thời lượng sạc, xác suất lỗi và sửa, hệ số theo giờ, ngày, loại trạm), kiểm tra hợp lệ rồi ánh xạ sang contract: `arrival_multiplier` → `demand_multiplier`, `suggestion_compliance` → `compliance_rate`.
- **Generator (`generator.py`):** một `np.random.default_rng(seed)` sinh theo thứ tự cố định: xe, lượt đến, thời lượng sạc, lỗi và sửa cổng. Kết quả là `FixtureBundle` bất biến dùng chung cho mọi chiến lược.
- **Manifest (`manifests.py`):** SHA-256 của bundle, `data_type="simulated"`, số lượng, thời điểm sinh. Đọc bundle sẽ kiểm tra hash.
- **Test:** 25 test (ID duy nhất, giá trị sai bị từ chối, cùng seed ra giống hệt, khác seed ra khác, hash ổn định, phát hiện file bị sửa).

## 4. PR-A2: engine và lịch sử Parquet (#69)

- **Engine (`engine.py`, `domain.py`):** bước 5 phút, thứ tự sự kiện cố định (sửa, lỗi, hoàn thành, đến, nhận từ hàng đợi, snapshot), hàng đợi FIFO, bất biến `free + busy + broken == n_ports` ở mọi bước. Cổng lỗi giữ hỏng đến khi sửa. Nếu cổng hỏng khi mọi cổng tốt đang bận, xe còn nhiều thời gian nhất bị ngắt và quay về đầu hàng đợi với thời gian còn lại, không mất xe.
- **Lịch sử (`history.py`):** `generate_status_history`, `snapshots_to_frame`, `write_status_history`, `build_status_window`. Cột khớp `STATUS_COLUMNS` của prediction; khóa duy nhất `(scenario, station_id, ts)`; múi giờ +07:00.
- **Lệnh sinh dữ liệu:** hai lệnh nối bằng `&&` (`station_data.cli generate`, sau đó `simulation.cli history`). Phải tách đôi vì test kiến trúc cấm hai module import lẫn nhau; chúng trao đổi qua file được kiểm bằng contract.
- **Kết quả:** 169.344 dòng, SHA-256 của Parquet giống hệt qua hai lần chạy.
- **Tự kiểm cho Thắng:** `validate_status_frame` của prediction chấp nhận file; `prediction.cli train` chạy được. Trên tập test, LightGBM đạt AUC 0,95 và Brier 0,076, trong khi baseline persistence đạt AUC 0,845 và Brier 0,118.

Hai quyết định cần lưu ý:

1. **Cửa sổ lịch sử chung.** Ngưỡng `train-end` và `calibration-end` của prediction áp dụng toàn cục. Nếu giữ ngày thật của từng kịch bản (30/4, Tết), mỗi kịch bản sẽ nằm trọn trong một phần train, calibration hoặc test. Vì vậy cả ba kịch bản dùng chung một cửa sổ 14 ngày kết thúc 13/10/2026 (Thắng cần tối thiểu 3 ngày). Hệ quả: kịch bản holiday và tet dùng ngày giả, hệ số theo kịch bản vẫn giữ nguyên.
2. **Cân chỉnh tải.** Hệ số lượt đến cơ sở là 0,5 lượt mỗi cổng mỗi giờ, không nhân thêm `holiday_multiplier` (hiệu ứng ngày lễ đã nằm trong `arrival_multiplier` và hệ số theo ngày). Tỷ lệ bước có trạm đầy: normal khoảng 1%, holiday khoảng 16%, tet khoảng 46%.

## 5. PR-A3: baseline, runner và so sánh (#70)

- **Baseline:** `NearestStrategy` và `CurrentlyAvailableStrategy`, dùng chung bộ lọc SOC, hòa thì chọn theo `station_id`, có ghi lý do khi phải quay về trạm gần nhất.
- **Metric (`metrics.py`):** `success_rate` là tỷ lệ xe có cổng trống ngay khi đến trên toàn bộ `vehicle_count`; xe chờ rồi mới được phục vụ không tính là thành công. `failed_count` gồm xe không có trạm khả thi, xe chờ quá 30 phút, xe không kịp đến trong cửa sổ. Xe thất bại luôn nằm trong mẫu số.
- **Runner (`runner.py`):** `DefaultSimulationRunner(fixture_loader, stations, configs, availability=None, …)` với `run`, `compare`, `compare_strategies`. Mỗi chiến lược chạy độc lập với engine mới từ cùng bundle bất biến, nên mọi kết quả có cùng `fixture_hash`.
- **Chuyến xe (`trips.py`):** `Vehicle` của contract không có id, vị trí hay giờ khởi hành, nên các thông tin này được sinh từ `bundle.seed` bên trong module simulation. Không cần đổi contract.
- **CLI `compare`:** đọc output của `station_data.cli generate`, ghi `compare_results.json`, in bảng và hash. Chiến lược `ai_allocation` chỉ chạy khi truyền `--ai-strategy package.module:attribute`.
- **Test:** 34 test mới, gồm strategy giả để chứng minh strategy được gọi cho từng xe mà không import `recommendation`.

Kết quả với seed 42 và 100 xe (hai baseline), sau khi sửa cửa sổ xuất phát:

| Kịch bản | Chiến lược | Success | Detour (km) | Wait (phút) | Failed |
| --- | --- | --- | --- | --- | --- |
| normal | nearest | 0,90 | 6,66 | 1,15 | 0 |
| normal | currently_available | 0,93 | 7,48 | 0,85 | 0 |
| holiday_30_4 | nearest | 0,58 | 6,66 | 6,15 | 6 |
| holiday_30_4 | currently_available | 0,75 | 9,40 | 3,20 | 1 |
| tet | nearest | 0,44 | 6,66 | 13,70 | 29 |
| tet | currently_available | 0,59 | 9,29 | 8,90 | 14 |

Đã sửa lỗi ở `trips.py`: trước đó 100 xe chỉ xuất phát trong 4 giờ đầu (00:00–03:55) nên bảng cũ quá tải; nay xe xuất phát đều trong 20 giờ, chừa 4 giờ để đến trạm. `fixture_hash` và Parquet không đổi. Tải tăng dần từ normal đến Tết như kỳ vọng. `nearest` thấp một phần vì nhiều xe cùng chọn một trạm gần nhất và tự gây tắc. Đó là đặc tính của chiến lược; không có số liệu nào được chỉnh để định trước người thắng.

## 6. Giới hạn đã biết

- Chiến lược `ai_allocation` chưa chạy: module recommendation chưa hoàn chỉnh (mới có SOC) và module simulation không được import nó. Kiên truyền strategy vào runner hoặc dùng `--ai-strategy`. Mặc định `p_available` là persistence; muốn dùng model của Thắng cần truyền hàm `availability(station_id, observed_at, eta)`.
- Quãng đường lấy đường thẳng nhân 1,3, tốc độ cố định 50 km/h, không có dịch vụ định tuyến.
- Tài xế không đổi sang trạm dự phòng, nên chất lượng backup chưa được đo.
- Toàn bộ dữ liệu là mô phỏng, gắn nhãn `simulated`. Vị trí, công suất trạm và các hệ số là giả định. Kết quả chỉ chứng minh pipeline trên dữ liệu mô phỏng, không chứng minh độ chính xác thực tế.
- Phần what-if (P1) chưa làm.

## 7. Việc tiếp theo

1. Mở public export cho runner (PR-A4, `strategy_for`) để Kiên nối `/simulate`.
2. Báo Kiên: runner đã sẵn sàng; cách gắn `fixture_loader` và `availability` nằm trong `simulation/SPEC.md`.
3. Báo Thắng: lệnh sinh dữ liệu nằm trong `station_data/SPEC.md`; gợi ý `--train-end 2026-10-08T00:00:00+07:00 --calibration-end 2026-10-11T00:00:00+07:00`.
4. Báo Tú: kết quả so sánh nằm ở `compare_results.json` sau khi chạy lệnh `compare`.

## 8. Lệnh tái lập toàn bộ

```bash
uv run python -m app.backend.modules.station_data.cli generate --scenario all --seed 42 --output app/backend/modules/station_data/generated \
&& uv run python -m app.backend.modules.simulation.cli history --input app/backend/modules/station_data/generated \
&& uv run python -m app.backend.modules.simulation.cli compare --input app/backend/modules/station_data/generated --scenario all --vehicles 100
```
