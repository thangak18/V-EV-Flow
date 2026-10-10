# Hai màn hình trong một web app

React + Vite, cùng API và component bản đồ; Driver và Operator là hai route/tab, không cần hai app. MapView dùng chung code và metadata, mỗi màn hình cấu hình layer/state riêng, không bắt buộc giữ cùng một map instance.

## Driver — P0, dựng trước

Desktop trình bày khung khoảng 390px; điện thoại thật chiếm chiều rộng viewport, không có viền điện thoại thừa. Responsive ngay từ đầu; thẻ trạm và font phải đủ đọc trên máy chiếu.

Thứ tự nội dung:

1. Tên V-EV Flow, nhãn dữ liệu mô phỏng/demo.
2. Nhập origin/destination (preset hành lang để demo nhanh), SOC 20%, loại đầu cắm; cấu hình xe mặc định rõ.
3. Nút “Tìm kế hoạch sạc”; loading, retry/error và không có trạm khả thi.
4. Bản đồ tuyến và marker, primary/backup khác nhau.
5. Thẻ primary: ETA, pin khi đến, xác suất khả dụng **tại ETA**, khoảng cách, lý do.
6. Thẻ backup: nhánh đi tiếp khi primary không sạc được; kế hoạch ước lượng có ghi giả định độc lập.
7. Gợi ý lệch giờ P1; tránh tự gọi recommend mỗi lần render vì endpoint có ghi tải ảo.

## Operator — P0 tối giản

Full desktop: header chọn ngày thường/30-4/Tết + mốc giờ; bản đồ pressure có legend; vùng mô phỏng 100 xe và bảng/bar chart ba strategy. Hiển thị seed, scenario, số xe, model/data version và nhãn mô phỏng.

Chỉ số: tỷ lệ có cổng ngay lúc đến, km đi vòng, thời gian chờ; không chỉ hiển thị chiến lược thắng. What-if thêm 2 cổng hoặc dịch 20% xe là P1, có before/after và giả định.

## Components dự kiến

```text
web/src/
  components/MapView.jsx
  components/StationCard.jsx
  components/ProbabilityBadge.jsx
  components/ScenarioSelector.jsx
  pages/DriverPage.jsx
  pages/OperatorPage.jsx
  services/api.js
  App.jsx
```

Đây là layout mục tiêu, chưa có các file code. Phân biệt p_available (model), pressure proxy và ranking (heuristic); không hiển thị điểm xếp hạng thành xác suất. Dùng màu kèm text/icon để hiểu kể cả khi nhìn máy chiếu kém rõ.

## Ưu tiên 5 ngày cho D

11/10 Driver khung + map/mock; 12/10 thẻ kế hoạch; 13/10 ghép API thật + Operator; 14/10 pressure/so sánh và P1 nếu kịp; 15/10 responsive, lỗi, luyện demo. C giao mock ngày đầu, A/B giao số liệu/chart, A tổng hợp slide/video để D tập trung giao diện.
