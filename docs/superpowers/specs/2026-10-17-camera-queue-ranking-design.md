# Hàng đợi từ camera trạm sạc trong xếp hạng gợi ý

## Mục tiêu

Ban giám khảo yêu cầu hàng đợi của trạm lấy từ dữ liệu camera đặt tại trạm thay vì chỉ tính toán. Camera thật chưa có, nên dùng **mock ở mức đầu ra của camera**: một nguồn trả số xe đang chờ và đang sạc theo trạm. Camera thật cắm vào cùng port sau này. Thành công khi: (1) gợi ý né trạm camera thấy đông; (2) trạm có camera hiện icon; (3) trạm không có camera vẫn xếp hạng như cũ; (4) mọi chỗ dùng dữ liệu này ghi rõ là mock.

## Ngoài phạm vi

Huấn luyện lại model dự báo với feature hàng đợi; nạp hàng đợi vào simulator/benchmark; nhận diện xe từ video thật. Ghi là hướng phát triển. Hệ số `0.8`, `15 phút`, `0.2` là giả định demo, chưa hiệu chỉnh.

## Contract (PR riêng, nhánh `codex/`)

`QueueObservation`: `station_id`, `observed_at` (có múi giờ), `vehicles_waiting >= 0`, `vehicles_charging >= 0`, `confidence` trong [0, 1], `source` (`camera_mock`), `data_type = mock`. Port `QueueObservationSource.observe(station_id, at, scenario) -> QueueObservation | None`; `None` nghĩa là trạm không có camera. OpenAPI và types sinh bằng lệnh, không sửa tay.

## Công thức

Với mỗi ứng viên, `L` là tải ảo, `S` là `mean_service_minutes`, `P` là số cổng hoạt động:

- `wait_est = L × S / P` (xấp xỉ cũ: coi tải kỳ vọng như số xe phải chờ)
- `wait_cam = vehicles_waiting × S / P`
- `c = 0.8 × confidence` nếu có quan sát và tuổi quan sát <= 15 phút; ngược lại `c = 0`
- `wait = c × wait_cam + (1 − c) × wait_est`
- `score = 1.0·p_available − 0.2·norm(travel + wait) − 0.2·soc_risk − 0.3·norm(L)`

`norm(x) = x / (x + travel_reference_minutes)`. Trạm không có camera hoặc quan sát cũ cho `c = 0`, nên chỉ thêm thời gian chờ ước lượng vào thành phần thời gian. `S` là cấu hình, mặc định 30 phút. Simulator tính thời lượng theo từng xe (kẹp 10-120 phút) nên không có giá trị trung bình cố định để dùng lại; 30 phút là giả định demo, chưa hiệu chỉnh.

## Thành phần

- `ranking.py`: `RankingInput` thêm `wait_minutes`; thành phần thời gian dùng `travel + wait`. Hàm trộn nằm riêng, thuần, dễ test.
- `service.py`: lấy quan sát cho từng ứng viên theo ETA, tính `wait`, thêm lý do: "Trạm X: N xe chờ, ước tính M phút (camera mock, hh:mm)" hoặc "ước lượng, trạm chưa có camera".
- `infrastructure/`: `MockCameraQueueSource`; hàng đợi theo giờ trong ngày và scenario (normal, holiday_30_4, tet), seed cố định; danh sách trạm có camera (~50-60%) và ghi đè từng trạm trong file JSON; vài quan sát có `confidence` thấp.
- API: endpoint đọc quan sát hàng đợi theo trạm.
- Frontend: icon camera trên danh sách, marker bản đồ và thẻ gợi ý, tooltip "Camera (mock), N xe chờ, cập nhật hh:mm, độ tin cậy X%". Giữ trạng thái loading, lỗi, rỗng.

## Kiểm thử

Test công thức trước khi sửa code (TDD): không camera cho kết quả bằng ước lượng; `confidence = 0` hoặc quan sát cũ bằng không camera; `confidence = 1` có `c = 0.8`; đơn điệu theo `vehicles_waiting`; trạm đông bị xếp thấp hơn. Test adapter: tái lập theo seed, ghi đè JSON, `None` cho trạm không camera. Test API và UI cho icon. Test cũ của `ranking.py` cập nhật có chủ đích và ghi lại. Giữ ngưỡng coverage 75% và chạy `make ci` một lần ở cuối.

## Rủi ro

Công thức điểm đổi nên điểm kỳ vọng của test cũ đổi. `wait_est` xấp xỉ thô. Dữ liệu là mock, không chứng minh độ chính xác thực tế.
