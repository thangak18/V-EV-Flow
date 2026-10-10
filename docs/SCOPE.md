# Phạm vi triển khai

## P0 — Phải hoàn thành

1. Một hành lang TP.HCM–Vũng Tàu, 10–20 trạm: vị trí thật nếu có, thông số thiếu là giả định có ghi nguồn.
2. Dự báo xác suất có ít nhất một cổng phù hợp ở ETA bằng model; SOC filter, primary và backup khả thi.
3. Điều phối nhiều gợi ý qua tải ảo theo thời gian để giảm dồn xe; xác suất model và điểm điều phối được tách rõ.
4. Driver mobile-first: nhập hành trình/pin, bản đồ, kế hoạch, xác suất, lý do ngắn.
5. Operator desktop: lớp Áp lực sạc, ngày thường/30-4/Tết; so sánh gần nhất, đang trống, AI+phân bổ trên 100 xe.
6. Kết quả có thể tái lập, có reset và video dự phòng; nguồn dữ liệu/giả định minh bạch.

## P1 — Chỉ nhận trước tối 14/10 nếu P0 đã chạy

- Gợi ý lệch giờ, dùng lại model cho các mốc khác.
- What-if thêm 2 **cổng** hoặc dịch 20% xe sang giờ lệch (đơn vị cổng khác trụ).
- SHAP: giải thích dự báo từng mẫu nếu kịp; nếu dùng quy tắc đơn giản phải ghi là lý do gợi ý, không giả là SHAP.

## Hoãn

Charge-to advice, báo cáo cộng đồng, dashboard vận hành đầy đủ, database server, deploy phức tạp, app React Native/Flutter, tích hợp VETC/Vmap thật, dữ liệu thu phí thật và tính phát thải.

Proposal gốc là tầm nhìn rộng hơn. Operator ở MVP chỉ là màn hình demo pressure/simulation, không đồng nghĩa công cụ vận hành sản xuất. Không tuyên bố dự báo chính xác thực tế từ kết quả mô phỏng.
