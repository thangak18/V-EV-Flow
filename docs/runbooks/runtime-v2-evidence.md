# Runtime V2 — kết quả simulated

**Nguồn simulated, chưa phải bằng chứng vận hành thực tế.**

Model: `lightgbm-0e9c6bb20db734dd`. Horizons: 15/30/60/90/120/180 phút.
Train/calibration/test: 571.788 / 208.656 / 213.318 nhãn ETA. Cutoff 08/10 và 11/10/2026, embargo 180 phút.

## Test theo thời gian

| Predictor | Brier | Log Loss | AUC |
|---|---:|---:|---:|
| lightgbm_raw | 0.087807 | 0.283538 | 0.935012 |
| lightgbm_calibrated | 0.087965 | 0.282716 | 0.934921 |
| persistence | 0.160521 | 5.785760 | 0.790089 |
| hourly_rate | 0.167853 | 0.500205 | 0.732223 |

Isotonic chọn bằng calibration. Brier test hơi kém raw, Log Loss cải thiện. Không chọn lại từ test.
Model V2 đánh giá nhiều horizon hơn V1 nên không so trực tiếp aggregate hai model như cùng một bài toán.

## Holdout khác seed và thời gian

Seed91, 21–27/10/2026, 503,874 nhãn. Model/calibrator đóng băng.

| Predictor | Brier | Log Loss | AUC |
|---|---:|---:|---:|
| lightgbm_raw | 0.081204 | 0.265836 | 0.946062 |
| lightgbm_calibrated | 0.080670 | 0.262079 | 0.946041 |
| persistence | 0.151935 | 5.476286 | 0.807083 |
| hourly_rate | 0.170943 | 0.504142 | 0.737300 |

Cùng họ simulator và metadata, chưa xác minh dịch chuyển sang dữ liệu thật.

## So sánh chiến lược: 5 seed × 3 scenario × 100 xe

45 lượt chạy. Seed 42–46, không lựa seed thắng. Tỷ lệ là có cổng **ngay khi đến**.

| Scenario / chiến lược | Tỷ lệ trung bình | Độ lệch chuẩn giữa seed | Chờ trung bình (phút) |
|---|---:|---:|---:|
| normal/nearest | 86.8% | 6.94 điểm % | 1.88 |
| normal/currently_available | 94.0% | 3.32 điểm % | 0.69 |
| normal/ai_allocation | 96.4% | 3.29 điểm % | 0.40 |
| holiday_30_4/nearest | 65.0% | 11.00 điểm % | 6.25 |
| holiday_30_4/currently_available | 79.8% | 6.69 điểm % | 2.84 |
| holiday_30_4/ai_allocation | 82.8% | 3.96 điểm % | 2.28 |
| tet/nearest | 41.4% | 5.59 điểm % | 13.98 |
| tet/currently_available | 56.0% | 7.78 điểm % | 8.96 |
| tet/ai_allocation | 57.8% | 6.98 điểm % | 8.58 |

## What-if nhiều seed

30 lượt what-if: mỗi seed/scenario thử +2 cổng S001 và dịch 20% xe sang 21h.
Trường hợp +2 cổng dùng variant `lightgbm-f01a2875bada1b0d`, kiểm tra SHA metadata/history và model cha.
Dịch giờ giữ model cơ sở. Hai chế độ không trộn lẫn khi diễn giải.

| Scenario / thay đổi | Có cổng trước | Có cổng sau | Delta trung bình | Khoảng delta giữa 5 seed |
|---|---:|---:|---:|---:|
| normal / add_ports | 96.4% | 99.0% | +2.6 điểm % | +0.0…+8.0 |
| normal / shift_departures | 96.4% | 97.0% | +0.6 điểm % | -2.0…+5.0 |
| holiday_30_4 / add_ports | 82.8% | 92.2% | +9.4 điểm % | +6.0…+14.0 |
| holiday_30_4 / shift_departures | 82.8% | 83.8% | +1.0 điểm % | -2.0…+4.0 |
| tet / add_ports | 57.8% | 73.0% | +15.2 điểm % | +10.0…+18.0 |
| tet / shift_departures | 57.8% | 55.8% | -2.0 điểm % | -11.0…+6.0 |

Giới hạn: AI đọc background, currently_available đọc engine có foreground; đường/speed simulator là giả định, không phải Goong traffic.
Capacity experiment đổi cả model lẫn hạ tầng, không chứng minh tác động riêng của số cổng. Cổng thêm chưa có fault trace riêng.
Tái lập bằng CLI và release checksum theo [runbook](runtime-completion.md). Raw histories/binaries/results ở artifacts/results ignored.
