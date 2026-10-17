# V-EV Flow — Báo cáo lợi ích của các bên liên quan

*Dự báo và điều phối nhu cầu sạc xe điện trên hành lang cao tốc · MLAI Hackathon 2026 · Bảng A*

> **Lưu ý về dữ liệu.** Mọi số liệu hiệu năng trong báo cáo này đến từ **dữ liệu mô phỏng** (simulated), hành lang TP.HCM–Vũng Tàu, 14 trạm, ba kịch bản. Chúng chứng minh quy trình dữ liệu và mô hình hoạt động, **chưa** chứng minh độ chính xác ngoài thực tế.

## 1. Tóm tắt điều hành

V-EV Flow là một lớp ứng dụng thông minh đặt trên bản đồ. Hệ thống trả lời ba câu hỏi: **đi trạm nào, đi vào lúc nào, và nếu trạm đó gặp sự cố thì đi đâu tiếp theo**. Khác với việc chỉ biết trạng thái trạm ở hiện tại, hệ thống dự báo xác suất còn cổng **tại thời điểm xe thực sự đến**, đồng thời phân bổ các gợi ý để nhiều xe không cùng bị dẫn vào một trạm.

Vấn đề có thật: dịp Tết 2026 tại Nghệ An, nhiều trạm quá tải, người dân xếp hàng xuyên đêm; một chủ xe thấy ứng dụng báo hết chỗ nhưng vẫn phải đến xếp hàng vì không có phương án thay thế.

| Bên liên quan | Lợi ích chính |
| --- | --- |
| Người lái xe điện | Đến trạm còn cổng, có trạm dự phòng, ít chờ và ít đi vòng |
| Đơn vị vận hành trạm | Tải dàn đều, thấy trước nơi quá tải, thử phương án đầu tư trước khi chi tiền |
| Tasco / VETC | Khác biệt cạnh tranh, tăng phiên sạc hoàn tất, giữ chân người dùng và đối tác |
| Doanh nghiệp vận tải | Giảm thời gian xe gián đoạn nhờ lên lịch sạc tránh cao điểm |
| Xã hội và đối tác bản đồ | Giảm hành trình đi vòng, thêm một lớp dữ liệu chuyên đề trên bản đồ |

## 2. Người lái xe điện

Nhóm này gồm chủ ô tô điện và hybrid đi liên tỉnh, đặc biệt dịp lễ khi nhu cầu sạc dồn vào hành lang cao tốc.

| Lợi ích | Cách hệ thống mang lại |
| --- | --- |
| Biết trạm nào còn cổng **khi mình đến** | Dự báo xác suất ở các mốc 15, 30, 60, 90, 120, 180 phút theo ETA |
| Có phương án dự phòng | Mỗi kế hoạch có trạm chính và trạm dự phòng, kèm xác suất thành công tổng hợp |
| Không bị dẫn đến trạm quá xa so với mức pin | Bộ lọc mức pin loại trạm làm pin xuống dưới ngưỡng an toàn |
| Biết nên đi giờ nào | Gợi ý lệch giờ, tái sử dụng cùng mô hình cho các mốc giờ khác |
| Hiểu lý do gợi ý | Giải thích từng dự báo bằng TreeSHAP |
| Dùng được trên điện thoại | Giao diện Driver thiết kế mobile-first, có trạng thái đang tải, lỗi và trống |

**Kết quả mô phỏng 100 xe** (trung bình 5 seed, tỷ lệ có cổng ngay khi đến):

| Kịch bản | Trạm gần nhất | Trạm đang trống | AI + phân bổ |
| --- | ---: | ---: | ---: |
| Ngày thường | 86,8% | 94,0% | 96,4% |
| Dịp 30/4 | 65,0% | 79,8% | 82,8% |
| Tết | 41,4% | 56,0% | 57,8% |

**Thời gian chờ trung bình** giảm rõ khi so với chiến lược "trạm gần nhất": dịp 30/4 từ 6,25 xuống 2,28 phút; dịp Tết từ 13,98 xuống 8,58 phút.

## 3. Đơn vị vận hành trạm sạc

| Lợi ích | Cách hệ thống mang lại |
| --- | --- |
| Tải dàn đều theo trạm và theo giờ | Cơ chế tải ảo: mỗi gợi ý cộng tải vào trạm trong khung giờ xe dự kiến đến, xe sau được phân sang trạm khác |
| Thấy trước nơi quá tải | Lớp bản đồ Áp lực sạc theo ngày thường, 30/4, Tết |
| Thử phương án trước khi đầu tư | Bảng what-if: thêm cổng hoặc dời 20% xe sang giờ lệch, xem tỷ lệ có cổng thay đổi thế nào |
| Khai thác trụ đều hơn | Dàn đều nhu cầu giúp giảm quá tải giờ cao điểm và tăng sử dụng giờ thấp điểm |

**Kết quả what-if** (thêm 2 cổng tại trạm S001, trung bình 5 seed):

| Kịch bản | Có cổng trước | Có cổng sau | Thay đổi |
| --- | ---: | ---: | ---: |
| Ngày thường | 96,4% | 99,0% | +2,6 điểm % |
| Dịp 30/4 | 82,8% | 92,2% | +9,4 điểm % |
| Tết | 57,8% | 73,0% | +15,2 điểm % |

Thêm cổng cho hiệu quả lớn nhất ở các kịch bản đông nhất. Đây là cơ sở để ra quyết định đầu tư có số liệu thay vì phỏng đoán.

**Giới hạn cần nêu rõ:** phương án dời giờ không phải lúc nào cũng có lợi. Ở kịch bản Tết, dời 20% xe sang 21h thay đổi từ −11 đến +6 điểm % giữa các seed, trung bình −2,0 điểm %. Thí nghiệm thêm cổng đổi cả mô hình lẫn hạ tầng nên không tách riêng được tác động của số cổng.

## 4. Tasco / VETC

| Lợi ích | Diễn giải |
| --- | --- |
| Khác biệt cạnh tranh | Theo thông tin công khai nhóm tìm được, VETC Trạm sạc đã có trạng thái thời gian thực, đặt lịch và thanh toán nhưng chưa thấy dự báo khả dụng tại thời điểm xe đến |
| Tăng phiên sạc hoàn tất | Người dùng chọn đúng trạm, đúng giờ nên nhiều phiên sạc hoàn tất hơn trên nền tảng |
| Giữ chân người dùng | Ở lại trong ứng dụng VETC và hệ sinh thái điểm thưởng Tasco |
| Giữ chân đối tác vận hành | Đối tác khai thác trụ đều hơn nên có động lực ở lại và mở rộng |
| Tích hợp ít rủi ro | Chỉ là lớp API gắn vào VETC Trạm sạc và Vmap; không cần database server; đã có cổng nhận dữ liệu đối tác có xác thực |
| Hướng mở rộng B2B | Đóng gói thành công cụ Charging Intelligence cho đơn vị vận hành (sau MVP) |
| Bản địa hóa | Mô hình có yếu tố Tết, 30/4, 2/9 và cuối tuần về quê |

**Về doanh thu.** Điều khoản thương mại giữa VETC và đối tác vận hành chưa được biết, nên doanh thu tăng thêm là giả định. Nhóm đề xuất đo **giao dịch tăng thêm thực sự** bằng cách so sánh nhóm dùng và nhóm không dùng gợi ý, loại các giao dịch chỉ chuyển từ trạm này sang trạm khác.

## 5. Doanh nghiệp vận tải dùng xe điện

- Lên lịch sạc tránh cao điểm, giảm thời gian xe ngừng hoạt động.
- Có trạm dự phòng cho từng chuyến, giảm rủi ro gián đoạn lộ trình.
- Chỉ số theo dõi: thời gian xe ngừng hoạt động và số km phát sinh mỗi phiên sạc.

## 6. Xã hội và đối tác bản đồ

- Giảm hành trình đi vòng để tìm trạm, tiết kiệm thời gian và quãng đường.
- Thêm một lớp dữ liệu chuyên đề mới (Áp lực sạc) cho bản đồ, dùng Goong cho địa điểm, tuyến đường và hiển thị.
- Báo cáo **không** tuyên bố giảm phát thải, vì chưa có dữ liệu năng lượng và quãng đường thực tế.

## 7. Độ tin cậy kỹ thuật

| Nội dung | Bằng chứng |
| --- | --- |
| Mô hình vượt baseline | Brier 0,081–0,088 so với 0,152–0,168 của hai baseline (persistence, hourly_rate) |
| Khả năng phân biệt | AUC 0,935 trên tập test theo thời gian; 0,946 trên holdout khác seed và khác thời gian |
| Đánh giá không rò rỉ | Chia train, calibration, test theo thời gian; embargo 180 phút |
| Không chọn seed thắng | Benchmark 5 seed × 3 kịch bản × 100 xe, báo cả độ lệch chuẩn |
| Kết quả tái lập | Cùng seed và fixture cho cùng kết quả; có reset; retry không cộng tải hai lần |
| Chất lượng phần mềm | Kiểm thử cuối 16/10/2026: `make ci` exit 0, 920 test backend (coverage 92,55%), 147 test frontend, 32 E2E |
| Trạng thái bền | Phân bổ lưu SQLite qua restart và nhiều worker trên một host |
| Minh bạch dữ liệu | Mọi dữ liệu mô phỏng gắn nhãn **simulated**; giao diện báo lỗi thay vì tự bịa tọa độ |

## 8. Giới hạn và điều kiện để chuyển sang thực tế

- Lịch sử trạng thái cổng trong demo là mô phỏng; cần ít nhất một mẫu dữ liệu thật từ Tasco hoặc đối tác để hiệu chỉnh.
- Ở kịch bản Tết, AI + phân bổ chỉ hơn chiến lược "trạm đang trống" khoảng 1,8 điểm %, nằm trong độ dao động giữa các seed. Lợi thế lớn nhất là so với "trạm gần nhất".
- Tốc độ và đường đi trong simulator là giả định, không phải dữ liệu giao thông Goong.
- Một số số liệu thị trường trong proposal (số xe điện, số đối tác VETC, mức tăng dịp Tết) do nhóm tự thu thập và cần kiểm chứng trước khi đưa vào bài thuyết trình.

## 9. Lộ trình

1. **Hackathon:** demo trên một hành lang với dữ liệu mô phỏng.
2. **Thử nghiệm:** nhận dữ liệu lịch sử thật từ một số trạm đối tác, hiệu chỉnh và đánh giá so với các baseline.
3. **Tích hợp:** đưa lớp dự báo vào VETC Trạm sạc và Vmap, đo giao dịch tăng thêm.
4. **Mở rộng:** công cụ chuẩn bị mùa cao điểm cho đơn vị vận hành, thêm dữ liệu năng lượng để đánh giá phát thải.

## 10. Cần Tasco hỗ trợ để bước sang giai đoạn 2

1. Lịch sử trạng thái cổng sạc, dù chỉ một mẫu nhỏ.
2. Lưu lượng thu phí tổng hợp theo giờ trên hành lang.
3. Xác nhận VETC hiện đã có hay chưa chức năng dự báo khả dụng tại thời điểm xe đến.
4. Điều khoản thương mại thông thường giữa VETC và đối tác vận hành.

---

*Nguồn: Proposal gốc, `docs/runbooks/runtime-v2-evidence.md`, `docs/runbooks/final-qa-2026-10-16.md`, `docs/SCOPE.md`.*
