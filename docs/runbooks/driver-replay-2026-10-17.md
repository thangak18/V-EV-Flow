# Driver: giờ khởi hành và ba kịch bản — 17/10/2026

## Thay đổi

Giờ đi 20:00 không còn bị chặn chỉ vì mốc mặc định là 16:00. Trong replay,
UI chọn snapshot lịch sử 20:00 có thật trong file và gửi observed_at=20:00,
depart_time=20:00. Giờ 20:02 dùng snapshot 20:00 và giữ departure 20:02.
Đây không phải mở rộng horizon model hay giả lập snapshot mới. Live vẫn giữ
snapshot mới nhất, không gán observed_at vào tương lai.

Form có hai hàng, mỗi hàng ba cột cùng chiều rộng. Nhắc giờ Việt Nam/reset
và nhóm nút nằm ở hàng riêng. Chọn lại cùng kịch bản không làm mất runtime.

## Kiểm tra dữ liệu hiện có

Release `simulator-v2-180m`: 169.344 dòng trạng thái, 14 trạm, 14 ngày,
30/09–13/10/2026. Mỗi kịch bản có 56.448 dòng.

| Kịch bản | Cổng trống trung bình mỗi snapshot trạm | Tỷ lệ snapshot không còn cổng |
| --- | ---: | ---: |
| Ngày thường | 4,765 | 1,5% |
| Lễ 30/4 | 2,955 | 22,2% |
| Tết | 1,492 | 59,7% |

Đây là thống kê **simulated**, không phải độ chính xác dự đoán hoặc dữ liệu ngày
lễ ngoài thực tế. Manifest model ghi nhận đủ cả ba scenario; split theo thời
gian, max horizon 180 phút. Không có bằng chứng ba lựa chọn dùng chung một
lịch sử trạng thái hoặc thiếu scenario khi train.

Lượt kiểm tra Driver cùng hành trình, khởi hành 20:00, snapshot 20:00:

| Scenario | Trạm chính | ETA | p_available |
| --- | --- | --- | ---: |
| normal | S001 | 20:05 | 0,995624 |
| holiday_30_4 | S001 | 20:05 | 0,924008 |
| tet | S001 | 20:05 | 0,088670 |

Cùng trạm/tuyến không có nghĩa cùng dự báo. Hiện scenario điều chỉnh nhu cầu sạc,
không có mô hình giao thông ngày lễ làm đổi tuyến/ETA. Form ghi rõ phạm vi này.
Chưa có dữ liệu vận hành thật để khẳng định accuracy thực tế.

## Xác minh

Tests bao gồm: lịch sử 08:00/19:00/20:00/20:02, floor snapshot đúng mốc 5 phút,
ngoài khoảng lịch sử bị chặn, live không tạo snapshot tương lai, reset giờ,
chọn lại scenario, xóa kế hoạch cũ, căn cột và không tràn ngang 360–1440 px.
Gate canonical: make ci; log local `/tmp/vev-driver-replay-ci.log`.
