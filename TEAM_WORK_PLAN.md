# V-EV Flow — Phân công 4 người và lịch triển khai 5 ngày

Kế hoạch triển khai hiện tại, tổng hợp các quyết định trong trao đổi và bản kế hoạch đến 15/10 có sẵn. Thay lịch 7 ngày ban đầu (đã lưu trong `docs/reference`). A/B/C/D là vai, chưa gán tên thành viên.

## Phân công

| Vai | Chịu trách nhiệm | Đầu ra |
| --- | --- | --- |
| **A — Data & Simulator** | Danh sách 10–20 trạm, simulator NumPy/pandas theo bước 5 phút, 3 kịch bản, tạo lịch sử, sinh 100 xe và bộ chạy so sánh; what-if nếu kịp | Dữ liệu v0, simulator có seed, file kết quả 3 chiến lược. Từ 14/10 tổng hợp slide và quay video với cả nhóm |
| **B — AI/ML** | Phụ A chốt simulator, nhãn/features, baseline, LightGBM, hiệu chỉnh, đóng gói predict; A+B đánh giá mô hình và chiến lược | Model joblib, hàm inference, AUC/Brier/calibration, biểu đồ so sánh. SHAP/time-shift nếu kịp |
| **C — Backend & Điều phối** | Chốt API/Pydantic, Goong client/cache, SOC filter, ranking, trạm dự phòng, tải ảo, pressure và ghép model | Mock API ngày đầu, API thật, reset, lỗi có thông báo; integrator của nhánh main |
| **D — Frontend & Map** | React+Vite, MapView chung, Driver responsive, Operator, hiển thị xác suất và 3 chiến lược | UI dùng mock trước rồi API thật; hỗ trợ A dựng demo và slide |

Bộ chạy mô phỏng 100 xe thuộc A, phương pháp đánh giá thuộc A+B; C cung cấp callable của thuật toán để A dùng, không gánh toàn bộ simulator. D không phải tự làm slide và tích hợp một mình. Trưởng nhóm lo liên lạc BTC/mentor, không gửi tự động từ repo.

## Lịch 11–15/10/2026

| Ngày | A | B | C | D | Mốc chung |
| --- | --- | --- | --- | --- | --- |
| **11/10** | Chốt hành lang/schema, dữ liệu v0 | Phụ A; dựng feature/label pipeline | Chốt contract, mock API, Goong thử | Driver cơ bản + bản đồ/mock trạm | Frontend gọi mock backend; schema thống nhất |
| **12/10** | Simulator v1, lịch sử 3 kịch bản | Baseline/model v1, calibration split | SOC filter, ranking, backup | Thẻ trạm, pin đến, xác suất | Có dữ liệu và model đầu tiên |
| **13/10** | Bộ chạy 100 xe và event/vehicle fixtures | Inference thật, kiểm tra leakage | Ghép model, allocation/reset, pressure | Ghép recommendation; Operator cơ bản | Luồng Data → ML → API → UI chạy thật |
| **14/10** | Chạy so sánh; slide; what-if nếu kịp | Metrics/calibration/chart | Sửa tích hợp/cache; P1 nếu ổn | Pressure + so sánh; P1 nếu ổn | Tối đóng tính năng, P0 hoàn chỉnh |
| **15/10** | Slide, video dự phòng | Kiểm tra số liệu, giúp pitch | Smoke test và sửa lỗi | Responsive, lỗi UI, luyện demo | Chiều diễn tập, tối nộp theo hạn được BTC xác nhận |

16/10 chỉ dùng sửa lỗi nếu BTC chấp thuận lùi; mốc 17/10 trong kế hoạch nguồn là thông tin nhóm cần xác nhận, không coi là lịch chính thức đã kiểm chứng.

## Dependency và làm song song

- A → B: dữ liệu v0 cuối 11/10. B phụ A từ đầu để simulator sinh đúng nhãn.
- C → D: mock `/stations`, `/predict`, `/recommend` trong 11/10, theo contract mới.
- B → C: model v1 cuối 12/10; mock trước đó phải gắn `data_type=mock`.
- A → C/D: kịch bản và dữ liệu pressure ngày 13/10.
- C → A: callable ranking/allocation ngày 13/10 để dùng chung logic API và evaluation.
- Dữ liệu Tasco chỉ thay nếu kiểm tra và tích hợp kịp trước tối 14/10; không đợi đối tác để khởi động.

## Nghiệm thu

| Vai | Đạt khi |
| --- | --- |
| A | Sinh lịch sử hợp lệ với >=10 trạm và 3 kịch bản; cùng seed tái lập; bộ 100 xe trả cả 3 chiến lược |
| B | Split thời gian, calibration tách khỏi test, có Brier/AUC khi đủ lớp, baseline persistence; API dùng model thật |
| C | Loại trạm không đủ pin/cổng, backup đi được sau primary; xử lý trường hợp không có trạm; tải ảo và reset chạy đúng |
| D | Driver responsive + Operator, hiển thị trạng thái loading/error/empty, pressure và biểu đồ kết quả từ API |
| Chung | Demo 20% pin → kế hoạch → đổi kịch bản → 100 xe, ghi rõ mô phỏng, README chạy được, có video |

Mỗi sáng họp 15 phút; cuối ngày ghép PR và chạy demo chung. Đổi schema/API phải cập nhật tài liệu và báo nhóm. Khi trễ: cắt SHAP, time-shift, what-if trước; giữ P0 trong [SCOPE](docs/SCOPE.md).
