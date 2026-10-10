# Demo, nghiệm thu và việc hỏi mentor

## Luồng 3–5 phút

1. Reset phân bổ; chọn preset hành lang, normal, xe 20% pin.
2. Driver: tìm kế hoạch; giải thích vì sao trạm gần nhất không nhất thiết tốt nhất ở ETA, primary và backup còn đủ pin.
3. Operator: đổi normal → 30/4 → Tết, thấy pressure thay đổi theo model/scenario.
4. Chạy 100 xe trên ba strategy với cùng fixtures/seed; xem thành công, km vòng, thời gian chờ. Nêu kết quả thực tế của runner kể cả không thắng.
5. Nếu có P1: thêm 2 cổng hoặc dịch 20% xe 2 giờ; so before/after, nêu giả định.
6. Kết thúc bằng giới hạn dữ liệu mô phỏng và đường tích hợp khi có dữ liệu Tasco.

Các số 25%, 85% hoặc plan_p 94% trong proposal/API là minh họa, không mặc định là kết quả demo. Không đặt chỉ tiêu “AI phải thắng” rồi hard-code biểu đồ.

## Checklist trước nộp

- [ ] Mỗi module có lệnh cài/chạy đã kiểm tra, env mẫu và không có key thật trong repo.
- [ ] Driver trên desktop/điện thoại, Operator trên laptop; loading/error/empty chạy được.
- [ ] Cổng và SOC hợp lệ; không gợi ý trạm không tương thích hoặc backup ngoài tầm pin.
- [ ] Inference dùng model thật; mock/data nguồn có nhãn rõ.
- [ ] Calibration/test tách thời gian và không leakage qua horizon.
- [ ] 100 xe so cùng fixtures/config/seed, state độc lập với Driver, metrics có định nghĩa.
- [ ] Reset rồi chạy lại cho kết quả lặp được; retry không cộng tải hai lần.
- [ ] Cache/fallback route được ghi nguồn; map cần mạng thì có video dự phòng.
- [ ] Slide có problem, kiến trúc, số liệu đánh giá, giới hạn và giá trị Tasco.
- [ ] Đóng P0 tối 14/10, 15/10 chỉ sửa lỗi/đánh bóng/nộp theo hạn BTC xác nhận.

## Hỏi Tasco/BTC — trưởng nhóm tự gửi

1. Thủ tục đổi ý tưởng từ “Còn lối vào” sang V-EV Flow nếu nhóm cần.
2. Hạn và định dạng nộp 15/10; có được dùng 16/10 làm dự phòng không; mốc tiếp theo 17/10.
3. Dữ liệu thật gồm trạm hay trạng thái/lịch sử cổng; file/API, quyền hiển thị và chia sẻ, tần suất cập nhật.
4. VETC đã có dự báo tại ETA chưa; tài liệu/API tích hợp thử.
5. Lưu lượng thu phí tổng hợp theo giờ có chia sẻ được không.
6. Credit Goong và điều kiện cache; key bản đồ và REST/API dùng thế nào.

Không chờ câu trả lời để làm P0: trạm công khai có nguồn, thông số thiếu ghi giả định, simulator cho cổng, Goong cho route/ETA nếu có key. Proposal chứa số liệu/nguồn tham khảo do nhóm thu thập; cần kiểm chứng trước khi đưa vào pitch, repo sơ khai này chưa kiểm chứng các số liệu đó.
