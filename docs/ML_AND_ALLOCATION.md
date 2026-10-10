# Mô hình, gợi ý và phân bổ

## Dự báo

Nhãn `y(t, h)` bằng 1 khi ở thời điểm `t+h` còn ít nhất một cổng hoạt động phù hợp. `h` là phút từ `observed_at` đến ETA. Feature chỉ dùng thông tin biết được tại t: cổng trống/bận/hỏng, lag 15/30/60 phút, giờ/thứ/lễ, mưa nếu có nguồn phù hợp, loại trạm/công suất, horizon. Nếu chưa có weather thật thì giả định có ghi rõ hoặc bỏ feature; không dùng thời tiết tương lai đã quan sát để giả làm dự báo thời điểm t.

LightGBM → calibrator → `p_available`. Isotonic hoặc Platt chọn trên validation; train/calibration/test tách theo thời gian. Giữa ranh giới split chừa khoảng theo horizon tối đa để nhãn train không lấn vào thời gian test. Không random split các snapshot/lag liên quan.

Baseline dự báo: giữ nguyên trạng thái hiện tại (persistence), có thể thêm tỷ lệ khả dụng theo giờ. Báo AUC (khi đủ hai lớp), Brier score, calibration curve và lượng mẫu; không dùng AUC làm bằng chứng xác suất đã chuẩn.

Test thêm scenario/seed và tham số mô phỏng khác train, đặc biệt holiday peak và outage. Lưu model version, feature schema và config. Kết quả chỉ chứng minh pipeline trên mô phỏng, chưa chứng minh độ chính xác thực tế.

## Simulator và đánh giá chiến lược

NumPy/pandas theo bước 5 phút; phải giữ trạng thái phiên sạc, thời lượng dịch vụ, xe chờ và lỗi/sửa cổng giữa các bước. Không sinh snapshot độc lập vì như vậy lag/ETA và hiệu ứng điều phối không có ý nghĩa.

Ba strategy dùng cùng vehicles/background events/service durations và seed được sinh trước:

1. `nearest`: trạm gần nhất trong số trạm tương thích và đủ pin.
2. `currently_available`: trạm hiện có cổng trống, trong số khả thi; nếu không có, dùng quy tắc fallback chung đã ghi rõ.
3. `ai_allocation`: dự báo + ranking + tải ảo.

A chạy simulator, C cung cấp thuật toán, B kiểm tra kết quả. Thành công tại ETA = tới trạm có cổng phù hợp ngay lúc đến; tách khỏi thành công sau khi chờ. Báo `success_rate`, `mean_detour_km`, `mean_wait_minutes`, `failed_count`, số xe thực sự được xử lý. Xe thất bại không biến mất khỏi mẫu số; định nghĩa chờ tối đa và cách tính detour/wait trước khi chạy. Cùng seed chưa đủ nếu mỗi strategy tự random theo nhánh khác nhau: dùng fixtures/background đã sinh trước.

## SOC và backup

`arrival_soc_pct = soc_pct - 100 * distance_km * consumption_kwh_per_km / battery_kwh`.

Loại trạm không phù hợp hoặc SOC khi đến dưới ngưỡng dự phòng (mặc định demo đề xuất 10%, cấu hình được; không phải bảo đảm an toàn thực tế). Backup phải đi được từ primary khi không sạc được ở primary, dùng pin còn lại và ETA của nhánh đó. Nếu không có trạm/backup phù hợp, trả null và lý do; không tạo backup giả.

`plan_p = 1 - (1 - p_primary) * (1 - p_backup)` chỉ là ước lượng theo giả định độc lập; p_backup dùng ETA nhánh fallback. Hai trạm có thể cùng quá tải; UI ghi giả định và không gọi là bảo đảm. Một trạm duy nhất thì plan_p = p_primary; không có trạm thì null.

## Phân bổ tải ảo

Không nhân trực tiếp `p_available` với `(1 - virtual_load / n_ports)` rồi gọi đó là xác suất đã hiệu chỉnh. Bản đầu dùng tải ảo như mức phạt ranking:

`score = w_p * p_available - w_t * normalized_travel_time - w_r * normalized_soc_risk - w_l * normalized_virtual_load`.

SOC filter chạy trước. Trọng số và chuẩn hóa là heuristic, phải ghi trong config và kiểm tra sensitivity. Tải chia cho cổng hoạt động, xử lý capacity=0 bằng loại trạm. Xác suất model vẫn là dự báo theo snapshot đầu vào, chưa phản ánh đầy đủ tác động của chính các gợi ý; hiển thị giới hạn này và đo hệ quả bằng simulator.

- Khi chấp nhận kế hoạch, thêm tải kỳ vọng cho **primary**, phủ các bucket từ ETA đến thời điểm kết thúc sạc giả định; không chỉ một mốc đến.
- MVP có thể mặc định tuân theo 100% trong kịch bản, ghi rõ giả định và thử thêm tỷ lệ khác nếu kịp.
- Mỗi request có `request_id`; cùng id/payload trả kế hoạch cũ, không cộng tải hai lần do retry. Cùng id khác payload trả conflict.
- TTL hoặc reset xóa tải; không cộng backup như thể xe sẽ chắc chắn đến cả hai trạm. Backup có thể dùng xác suất có điều kiện ở phiên bản sau.
- Một worker; cập nhật dict có lock; simulation có state riêng, reset Driver không sửa lịch sử/model/kết quả evaluation.

## Lý do và P1

P0 giải thích bằng quy tắc từ dữ liệu: đủ pin, compatible, ETA, xác suất, tải ảo. Feature importance toàn cục không giải thích một dự báo cụ thể. SHAP từng mẫu là P1; không gán lý do như “trời không mưa” nếu không có feature đó. Time-shift chạy lại pipeline cho các giờ thay thế với feature có thể biết ở thời điểm quyết định; ghi rõ các giả định khi thay giờ.
