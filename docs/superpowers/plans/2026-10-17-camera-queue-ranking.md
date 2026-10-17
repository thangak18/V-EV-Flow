# Kế hoạch: hàng đợi camera trong xếp hạng

Spec: `docs/superpowers/specs/2026-10-17-camera-queue-ranking-design.md`. Nhánh `codex/camera-queue-ranking`. Mỗi bước: viết test trước, thấy fail, code, thấy pass, commit nhỏ. Dùng test của module trong lúc làm; `make ci` chạy một lần ở cuối.

## Bước 1: Contract (commit riêng để review)

1. `app/backend/contracts/queue.py`: `QueueObservation` (StrictModel, `observed_at` có múi giờ, `vehicles_*` >= 0, `confidence` 0-1, `source`, `data_type`).
2. `contracts/ports.py`: thêm `QueueObservationSource.observe(station_id, at, scenario) -> QueueObservation | None`.
3. `contracts/examples/`: một ví dụ hợp lệ. Cập nhật `contracts/SPEC.md` và `docs/DATA_CONTRACT.md`.
4. Sinh lại OpenAPI và types bằng lệnh trong `backend/AGENTS.md`; chạy `make contract-check`.

## Bước 2: Công thức xếp hạng

1. `modules/recommendation/tests/test_ranking.py`: thêm test mới theo spec (không camera; `confidence=0`; quan sát cũ; `confidence=1` cho `c=0.8`; đơn điệu theo `vehicles_waiting`; trạm đông xếp thấp hơn).
2. `ranking.py`: hàm thuần `blend_wait_minutes(...)`; `RankingInput.wait_minutes`; thành phần thời gian dùng `travel + wait`; thêm cấu hình `mean_service_minutes=30`, `camera_trust=0.8`, `max_observation_age_minutes=15`.
3. Sửa các test cũ có điểm kỳ vọng đổi, ghi lại từng chỗ trong commit message.

## Bước 3: Adapter mock

1. `infrastructure/services/camera_mock.py`: `MockCameraQueueSource` theo giờ và scenario, seed cố định; đọc danh sách trạm có camera và ghi đè từ một file JSON cấu hình đặt trong `app/` (không chứa dữ liệu đối tác).
2. Test: tái lập theo seed, ghi đè JSON, `None` cho trạm không camera, có vài quan sát `confidence` thấp.

## Bước 4: Service và API

1. `modules/recommendation/service.py`: nhận `QueueObservationSource` tùy chọn (mặc định không có = hành vi cũ), tính `wait`, thêm lý do hiển thị.
2. `api/routes/stations.py`: endpoint đọc quan sát theo trạm; nối nguồn mock trong `api/dependencies.py`. Test route và test `test_service.py`.

## Bước 5: Giao diện

1. Hiện icon camera ở danh sách trạm, marker bản đồ (`components/map`) và `StationPlanCard.tsx`, kèm tooltip; dùng `AsyncState` cho loading, lỗi, rỗng.
2. Test component cho có/không camera và các trạng thái.

## Bước 6: Tài liệu và kiểm tra cuối

1. Cập nhật `docs/ML_AND_ALLOCATION.md` (công thức mới, giả định, giới hạn) và `docs/USER_GUIDE.md` (ý nghĩa icon).
2. Chạy `make ci`; ghi lệnh, kết quả, HEAD. Nếu không chạy được ghi `NOT RUN` hoặc `BLOCKED`.

## Thứ tự nếu thiếu thời gian

Bước 1, 2, 3, 4 là lõi (có thể demo qua API). Bước 5 là phần ban giám khảo nhìn thấy, nên làm ngay sau lõi. Bước 6 phần tài liệu rút gọn cuối cùng, nhưng không bỏ `make ci`.
