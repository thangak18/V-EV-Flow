# V-EV Flow — Kịch bản doanh thu và lợi ích nếu được áp dụng

*Mô hình giả định cho một hành lang TP.HCM–Vũng Tàu, tính theo năm · Phục vụ thảo luận với Tasco/VETC*

> **Đây là kịch bản giả định, không phải dự báo hay kết quả đo.** Chỉ có **chênh lệch hiệu quả giữa các chiến lược** lấy từ mô phỏng của dự án. Mọi con số về giá sạc, lượng xe, mức chia doanh thu, tỷ lệ áp dụng và hành vi bỏ đi đều là **giả định của người lập mô hình**, cần thay bằng số thật khi có dữ liệu từ Tasco và đối tác.

## 1. Kết luận

- **Cơ chế tạo giá trị có thật và dương ở cả ba kịch bản.** Dự báo khả dụng và phân bổ giúp thêm xe có cổng ngay khi đến, nghĩa là thêm phiên sạc hoàn tất và bớt thời gian chờ.
- **Doanh thu hoa hồng từ phiên sạc tăng thêm là nhỏ.** Trong kịch bản cơ sở, một hành lang tạo thêm khoảng 476 phiên sạc mỗi năm; phần Tasco hưởng chỉ khoảng **2,5 triệu VND/năm**. Chỉ riêng hoa hồng thì không đủ để biện minh cho dự án.
- **Giá trị lớn hơn nằm ở hai nguồn khác:** gói thuê bao Charging Intelligence cho đơn vị vận hành (kịch bản cơ sở khoảng **201,6 triệu VND/năm** cho một hành lang) và giá trị chiến lược về giữ chân người dùng, đối tác. Hai nguồn này phụ thuộc hoàn toàn vào giả định chưa kiểm chứng.
- **Cách khẳng định trung thực:** "Cơ chế đã được chứng minh trên mô phỏng; quy mô doanh thu phụ thuộc vài biến số chưa biết và cần pilot để đo."

## 2. Chứng cứ đo được từ mô phỏng

Nguồn: `docs/runbooks/runtime-v2-evidence.md`, 5 seed × 3 kịch bản × 100 xe, dữ liệu **simulated**.

| Kịch bản | Có cổng khi đến: gần nhất | đang trống | AI + phân bổ | Chờ TB (phút): gần nhất | đang trống | AI + phân bổ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ngày thường | 86,8% | 94,0% | 96,4% | 1,88 | 0,69 | 0,40 |
| Dịp 30/4 | 65,0% | 79,8% | 82,8% | 6,25 | 2,84 | 2,28 |
| Tết | 41,4% | 56,0% | 57,8% | 13,98 | 8,96 | 8,58 |

**Đường so sánh đúng cho VETC** là cột "đang trống", vì VETC Trạm sạc đã hiển thị trạng thái thời gian thực. Mức tăng thêm của dự báo so với đường này chỉ là +2,4 / +3,0 / +1,8 điểm %. Mức tăng so với "gần nhất" (+9,6 / +17,8 / +16,4 điểm %) chỉ áp dụng cho người lái chọn theo thói quen.

## 3. Cách tính

Số phiên sạc được cứu mỗi năm, tính riêng cho từng kịch bản rồi cộng lại:

```text
phiên cứu được = phiên_hành_lang × tỷ_lệ_áp_dụng
                 × mức_tăng_hiệu_dụng × hệ_số_thực_tế
                 × tỷ_lệ_bỏ_đi
mức_tăng_hiệu_dụng =
    (1 − tỷ_lệ_thói_quen) × tăng_so_với_đang_trống
    + tỷ_lệ_thói_quen × tăng_so_với_gần_nhất
doanh_thu_phiên = phiên cứu được × kWh_mỗi_phiên × giá_mỗi_kWh
phần_Tasco = doanh_thu_phiên × tỷ_lệ_chia
phần_đối_tác = doanh_thu_phiên × (1 − tỷ_lệ_chia)
```

Điểm then chốt: một xe không có cổng khi đến **chưa chắc mất phiên sạc**, vì simulator cho xe vào hàng chờ chứ không mô phỏng việc bỏ đi. Vì thế cần tham số **tỷ_lệ_bỏ_đi** và **hệ_số_thực_tế** (phần hiệu quả mô phỏng còn giữ lại ngoài đời).

## 4. Giả định đầu vào

**Quy mô hành lang** (giả định chung cho ba kịch bản): 14 trạm × 6 cổng = 84 cổng, theo số trạm của demo. Số cổng mỗi trạm là giả định, vì dữ liệu trạm trong repo là giả định.

| Loại ngày | Số ngày/năm | Phiên/cổng/ngày | Phiên/năm |
| --- | ---: | ---: | ---: |
| Ngày thường | 350 | 8 | 235.200 |
| Lễ ngắn (30/4, 2/9...) | 8 | 14 | 9.408 |
| Tết | 7 | 20 | 11.760 |
| **Tổng** | | | **256.368** |

| Tham số | Thận trọng | Cơ sở | Lạc quan |
| --- | ---: | ---: | ---: |
| Tỷ lệ phiên dùng lớp V-EV Flow | 10% | 25% | 40% |
| Tỷ lệ người lái chọn theo thói quen (đường "gần nhất") | 0% | 20% | 50% |
| Hệ số thực tế so với mô phỏng | 50% | 75% | 100% |
| Tỷ lệ xe không có cổng thực sự bỏ đi | 10% | 25% | 50% |
| kWh mỗi phiên | 25 | 30 | 35 |
| Giá mỗi kWh (VND) | 3.000 | 3.500 | 4.000 |
| Doanh thu mỗi phiên (VND) | 75.000 | 105.000 | 140.000 |
| Tỷ lệ Tasco hưởng trên doanh thu phiên | 3% | 5% | 10% |

Giá sạc và tỷ lệ chia chưa được xác nhận. Proposal ghi rõ điều khoản thương mại giữa VETC và đối tác chưa biết.

## 5. Kết quả: nguồn 1, hoa hồng từ phiên sạc tăng thêm

Cho một hành lang, một năm.

| Chỉ số | Thận trọng | Cơ sở | Lạc quan |
| --- | ---: | ---: | ---: |
| Phiên dùng lớp V-EV Flow | 25.637 | 64.092 | 102.547 |
| **Phiên sạc tăng thêm** | **31** | **476** | **3.232** |
| Doanh thu phiên tăng thêm (triệu VND) | 2,3 | 49,9 | 452,5 |
| **Phần Tasco (triệu VND)** | **0,07** | **2,5** | **45,2** |
| Phần đơn vị vận hành (triệu VND) | 2,2 | 47,4 | 407,2 |
| Giờ chờ tiết kiệm cho người lái | 65 | 475 | 1.756 |
| Phần Tasco nếu nhân lên toàn mạng 350 trụ, hệ số ×4,17 (triệu VND) | 0,29 | 10,4 | 188,5 |

**Nhận xét:** trong kịch bản cơ sở, doanh thu phiên tăng thêm chỉ bằng khoảng **0,19%** doanh thu của cả hành lang (khoảng 26,9 tỷ VND). Muốn riêng khoản hoa hồng đạt 1 tỷ VND/năm cho Tasco ở kịch bản cơ sở, cần khoảng **400 hành lang** tương đương. Vì vậy hoa hồng không nên là luận điểm chính.

## 6. Các nguồn giá trị khác

### 6.1. Nguồn 2: thuê bao Charging Intelligence cho đơn vị vận hành

Đóng gói lớp Áp lực sạc và what-if thành gói trả phí. **Mức giá hoàn toàn là giả định**, repo không có mô hình giá hay khảo sát khách hàng.

| Tham số và kết quả | Thận trọng | Cơ sở | Lạc quan |
| --- | ---: | ---: | ---: |
| Tỷ lệ trạm đăng ký (trên 14 trạm) | 30% | 60% | 90% |
| Phí mỗi trạm mỗi tháng (triệu VND) | 1 | 2 | 4 |
| **Doanh thu thuê bao mỗi năm (triệu VND)** | **50,4** | **201,6** | **604,8** |
| Nếu nhân lên mạng 350 trụ (triệu VND) | 210 | 840 | 2.520 |

Phí 2 triệu VND/tháng ở kịch bản cơ sở bằng khoảng 1,3% doanh thu một trạm (6 cổng × 8 phiên × 365 ngày × 105.000 VND, khoảng 1,84 tỷ VND/năm), nằm ở mức đơn vị vận hành có thể chấp nhận nếu họ thấy giá trị.

### 6.2. Giá trị của what-if đối với đơn vị vận hành

Kết quả mô phỏng thêm 2 cổng tại một trạm: +2,6 / +9,4 / +15,2 điểm % tỷ lệ có cổng (ngày thường / lễ ngắn / Tết). Nếu đơn vị vận hành hành động theo, mức doanh thu phiên sạc tăng thêm ước tính (theo cùng hệ số thực tế và tỷ lệ bỏ đi như bảng trên):

| Chỉ số | Thận trọng | Cơ sở | Lạc quan |
| --- | ---: | ---: | ---: |
| Phiên sạc tăng thêm mỗi năm | 439 | 1.648 | 4.394 |
| Doanh thu phiên (triệu VND/năm) | 33,0 | 173,0 | 615,1 |

Kết quả thêm cổng dao động mạnh giữa các seed (ví dụ ngày thường từ +0,0 đến +8,0 điểm %) và thí nghiệm này đổi cả mô hình lẫn hạ tầng. Chi phí đầu tư cổng sạc chưa được tính.

**Cân đối giá trị cho đơn vị vận hành, kịch bản cơ sở:** phần doanh thu từ phiên sạc tăng thêm (47,4 triệu) cộng giá trị what-if (173,0 triệu) vào khoảng 220 triệu VND, chỉ vừa bằng phí thuê bao 201,6 triệu. Ở kịch bản cơ sở, gói thuê bao chưa chắc đủ hấp dẫn nếu đặt giá như trên. Cần giảm phí hoặc chứng minh thêm giá trị trong pilot.

### 6.3. Nguồn 3: giữ chân người dùng và đối tác (chưa lượng hóa)

Giữ người dùng trong ứng dụng VETC và hệ sinh thái điểm thưởng, giữ đối tác vận hành ở lại nền tảng. Không có dữ liệu để gán con số, nên báo cáo không đưa số nào. Đây có thể là giá trị lớn nhất nhưng cũng khó chứng minh nhất.

## 7. Lợi ích theo từng bên (kịch bản cơ sở, một hành lang, một năm)

| Bên liên quan | Lợi ích định lượng | Lợi ích khác |
| --- | --- | --- |
| Người lái xe | Tiết kiệm khoảng 475 giờ chờ cho toàn bộ người dùng; so với trạng thái thời gian thực, mỗi xe chờ ít hơn khoảng 0,3–0,6 phút (mô phỏng) | Có trạm dự phòng, biết lý do gợi ý, ít rủi ro đến trạm kẹt khi pin thấp |
| Đơn vị vận hành | Thêm khoảng 47,4 triệu VND doanh thu phiên; khoảng 173 triệu nếu thêm cổng theo what-if | Tải dàn đều, thấy trước nơi quá tải, có cơ sở ra quyết định đầu tư |
| Tasco / VETC | Hoa hồng khoảng 2,5 triệu; thuê bao khoảng 201,6 triệu nếu bán được | Khác biệt cạnh tranh, giữ người dùng và đối tác, mở đường lên mạng lưới lớn hơn |
| Doanh nghiệp vận tải | Chưa lượng hóa | Lên lịch sạc tránh cao điểm, giảm thời gian xe gián đoạn |
| Xã hội | Chưa lượng hóa | Giảm hành trình đi vòng; không tuyên bố giảm phát thải |

## 8. Độ nhạy và rủi ro

- **Biến số nhạy nhất** là tỷ lệ xe bỏ đi và tỷ lệ áp dụng. Giữa kịch bản thận trọng và lạc quan, phần Tasco từ hoa hồng chênh nhau hơn 600 lần. Phần lớn chênh lệch đến từ việc các giả định cùng chuyển động một chiều.
- **Mô phỏng chưa phản ánh thực tế.** Dữ liệu trạng thái cổng là mô phỏng; chênh lệch +1,8 đến +3,0 điểm % so với đường "đang trống" nằm gần mức dao động giữa các seed.
- **Chuyển dịch, không phải tăng thêm.** Nếu xe vốn sạc ở trạm khác trong mạng VETC thì Tasco không có giao dịch mới. Chỉ phiên bị mất hẳn mới tính là tăng thêm.
- **Chưa tính chi phí.** Báo cáo chỉ tính doanh thu và lợi ích, chưa có chi phí phát triển, vận hành, tích hợp, nên chưa kết luận được lợi nhuận.
- **Nhân lên toàn mạng chỉ là phép nhân.** Hệ số ×4,17 giả định mọi trụ có hồ sơ nhu cầu giống hành lang cao tốc, điều thường không đúng với trạm đô thị.

## 9. Cần đo gì để biến giả định thành bằng chứng

1. Tỷ lệ xe thực sự bỏ đi khi không có cổng (khác với việc xếp hàng chờ).
2. Giá bán và tỷ lệ chia doanh thu thực tế giữa VETC và đối tác.
3. Số phiên sạc theo giờ trên hành lang cao tốc, đặc biệt dịp lễ.
4. Kết quả thử nghiệm đối chứng: nhóm dùng và nhóm không dùng gợi ý, đo phiên sạc hoàn tất và loại các phiên chỉ chuyển trạm.
5. Mức sẵn sàng trả phí của đơn vị vận hành cho công cụ chuẩn bị mùa cao điểm.

---

*Nguồn chứng cứ: `docs/runbooks/runtime-v2-evidence.md`, Proposal gốc, `docs/SCOPE.md`. Mọi tham số kinh tế là giả định của người lập mô hình.*
