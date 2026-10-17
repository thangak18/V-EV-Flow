# V-EV Flow — Báo cáo dẫn chứng khả năng tạo doanh thu cho các bên nếu được áp dụng

*Tổng hợp chứng cứ từ dự án, từ nghiên cứu và thị trường quốc tế, kèm mô hình doanh thu giả định đã hiệu chỉnh theo chứng cứ · Hành lang TP.HCM–Vũng Tàu*

> **Cách đọc báo cáo này.** Số trong ngoặc vuông, ví dụ [4], là số thứ tự của nguồn trong mục 9 (Nguồn tham khảo), mỗi nguồn có tên bài, đơn vị đăng, ngày và đường dẫn. Mỗi luận điểm được gắn một trong ba mức bằng chứng: **[Đo]** chênh lệch hiệu quả đo trong mô phỏng của dự án (dữ liệu *simulated*) [15]; **[Quốc tế]** dẫn chứng công khai từ nước ngoài; **[Giả định]** con số do người lập mô hình đặt, chưa có dữ liệu. Phần doanh thu tiền tệ chủ yếu là giả định. Báo cáo không khẳng định doanh thu sẽ xảy ra.

## 1. Kết luận

1. **Có khả năng tạo giá trị kinh tế, nhưng quy mô nhỏ nếu chỉ tính hoa hồng phiên sạc.** Với giả định đã hiệu chỉnh theo chứng cứ, một hành lang tạo thêm khoảng 190 phiên sạc mỗi năm (kịch bản cơ sở), tương đương khoảng 20 triệu VND doanh thu phiên cho các bên. Phần Tasco từ hoa hồng chỉ khoảng 0,6 triệu VND/năm.
2. **Bên hưởng lợi doanh thu trực tiếp nhất là đơn vị vận hành trạm**, qua phiên sạc được cứu (khoảng 19 triệu VND/năm) và qua quyết định thêm cổng nhờ công cụ what-if (khoảng 69 triệu VND/năm nếu họ hành động).
3. **Giá trị lớn hơn của Tasco/VETC nằm ngoài hoa hồng:** giữ chân người dùng và đối tác, dữ liệu và công cụ B2B. Tesla và Google cung cấp dự báo khả dụng như một tính năng trong sản phẩm [4][5][6]; PlugShare được EVgo mua với giá 25 triệu USD nhờ tệp người dùng và dữ liệu [12][13]. Phần này có tiền lệ nhưng **chưa thể lượng hóa** cho Việt Nam.
4. **Chưa có dẫn chứng nào cho thấy riêng dự báo khả dụng tạo ra doanh thu tăng thêm đo được.** Các nguồn [4]–[6] cho thấy tính năng tồn tại, không công bố doanh thu của nó. Cách khẳng định trung thực: cơ chế đã chứng minh trên mô phỏng, tiền lệ thị trường ủng hộ hướng đi, và doanh thu thật cần một pilot có đối chứng để đo.

## 2. Chuỗi lập luận và mức bằng chứng

| Mắt xích | Luận điểm | Bằng chứng và nguồn | Mức |
| --- | --- | --- | --- |
| 1 | Nhu cầu sạc dồn vào kỳ nghỉ và gây hàng chờ | Trung Quốc: lượng sạc cao tốc bình quân ngày gấp 2,4 lần ngày thường dịp Quốc khánh 2024 [1]; tăng 52% so với năm trước dịp Tết 2026 [2]. Nghệ An: lượt sạc tăng khoảng 4 lần dịp Tết 2026, xe xếp hàng xuyên đêm [3] | Quốc tế |
| 2 | Hãng lớn đã triển khai dự báo khả dụng khi đến | Tesla (10/2023) [4], nâng cấp 4/2026 [5]; Google Maps (11/2025) [6] | Quốc tế |
| 3 | Dự báo kèm phân bổ tăng tỷ lệ xe có cổng khi đến | Tết: 41,4% (gần nhất), 56,0% (đang trống), 57,8% (AI + phân bổ); 30/4: 65,0%, 79,8%, 82,8% [15] | Đo |
| 4 | Thêm cổng ở nơi cần giảm tắc nghẽn | Thêm 2 cổng tại S001: +9,4 điểm % (30/4), +15,2 điểm % (Tết) [15] | Đo |
| 5 | Xe có cổng hơn thì có thêm phiên sạc hoàn tất | Cần giả định tỷ lệ xe bỏ đi. Tham chiếu: 14% lượt đến trạm tại Mỹ không sạc được năm 2025, chủ yếu do cột hỏng [8][14] | Giả định, có tham chiếu |
| 6 | Phiên sạc thêm quy đổi thành doanh thu cho các bên | Giá sạc, tỷ lệ chia: chưa có dữ liệu Việt Nam | Giả định |
| 7 | Giá trị chiến lược và dữ liệu | PlugShare 25 triệu USD [12][13]; Tesla và Google đưa dự báo vào sản phẩm [4][6] | Quốc tế, không quy đổi được |

Điểm yếu nhất là mắt xích 5 và 6: đây là nơi dự án chưa có bằng chứng ngoài mô phỏng.

## 3. Chứng cứ đo trong dự án

Nguồn [15]: benchmark Runtime V2 của dự án, 5 seed (42–46) × 3 kịch bản × 100 xe, dữ liệu **simulated**, model `lightgbm-0e9c6bb20db734dd`. Tỷ lệ là có cổng ngay khi đến.

| Kịch bản | Có cổng khi đến: gần nhất | đang trống | AI + phân bổ | Chờ TB (phút): gần nhất | đang trống | AI + phân bổ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ngày thường | 86,8% | 94,0% | 96,4% | 1,88 | 0,69 | 0,40 |
| Dịp 30/4 | 65,0% | 79,8% | 82,8% | 6,25 | 2,84 | 2,28 |
| Tết | 41,4% | 56,0% | 57,8% | 13,98 | 8,96 | 8,58 |

**Đường so sánh đúng** với VETC là "đang trống", vì VETC đã hiển thị trạng thái thời gian thực (theo Proposal của dự án). Mức tăng thêm của dự báo so với đường này chỉ +2,4 / +3,0 / +1,8 điểm %. Mức tăng so với "gần nhất" lớn hơn nhiều nhưng chỉ đúng với người lái chọn theo thói quen.

Ở mô phỏng, xe không có cổng vào hàng chờ chứ không rời trạm, nên mô phỏng **không** đo được việc mất phiên sạc. Đây là khoảng trống chính khi quy đổi sang doanh thu.

## 4. Dẫn chứng quốc tế

| Chủ đề | Dẫn chứng | Ý nghĩa cho doanh thu |
| --- | --- | --- |
| Quy mô cao điểm | Quốc khánh 2024: 10,3 triệu kWh/ngày so với khoảng 4,3 triệu kWh ngày thường (gấp 2,4 lần), 24.400 trạm cao tốc, 3,1 triệu phiên sạc trong tuần [1]. Tết 2026 (15–23/2): 6,02 triệu phiên sạc, 149,77 triệu kWh, bình quân ngày tăng 52% so với năm trước [2] | Cao điểm thực tế không thấp hơn giả định của mô hình |
| Sản phẩm tương tự | Tesla dự báo số trụ trống và thời gian chờ khi đến, dựa trên thời gian di chuyển của xe và các xe Tesla khác đang tới trạm [4]. Bản nâng cấp huấn luyện trên dữ liệu 9 triệu dặm, giảm sai số ước lượng hàng chờ còn khoảng 20% [5]. Google Maps dự báo số cột sạc trống khi đến, từ 11/2025 trên Android Auto và xe tích hợp Google [6] | Nhu cầu và tính khả thi đã được chứng minh; các nguồn không nêu doanh thu của tính năng |
| Hiệu quả giảm chờ | Thông tin tắc nghẽn giảm tới 14% thời gian chết so với lập lịch không có dự báo, rõ nhất ở trạm nhỏ và khi mức tắc nghẽn trung bình trên 50%. Đây là mô phỏng Monte Carlo, không dùng dữ liệu thật [7] | Cùng hướng với mô phỏng của dự án; không phải bằng chứng thực tế |
| Xe không sạc được | Khảo sát J.D. Power 2025 tại Mỹ (7.428 chủ xe, tháng 1–6/2025): 14% từng đến trạm mà không sạc được, giảm từ 19% năm 2024; 60% trong số đó do cột hỏng hoặc không hoạt động [8][14] | Cơ sở cho tỷ lệ bỏ đi; chờ đông chỉ là phần nhỏ |
| Giá theo nhu cầu | Giá trung bình giờ cao điểm 63,7 cent/kWh so với 43,8 cent giờ thấp điểm tại các trạm có giá theo khung giờ ở Mỹ, quý 3/2026 [9]. Tesla nói giá theo mức sử dụng thực tế giảm tắc nghẽn và tăng mức sử dụng nhưng không nêu số liệu [10] | Phân hóa giá theo giờ được thị trường chấp nhận; chưa có số hiệu quả |
| Doanh thu nền tảng gom trạm | NaaS (Trung Quốc): net take rate (doanh thu ròng trên giá trị giao dịch, sau khi trừ khuyến mãi cho người dùng) là −8,14% tháng 9/2023, −0,92% tháng 12/2023, 0,02% tháng 1/2024, 0,75% tháng 2/2024 [11] | Hoa hồng ròng của nền tảng gom rất mỏng |
| Giá trị dữ liệu người lái | EVgo mua Recargo (công ty vận hành PlugShare) với giá 25 triệu USD tiền mặt, hoàn tất 9/7/2021; Recargo có doanh thu từ ứng dụng, thanh toán, API dữ liệu, khảo sát người lái và quảng cáo di động [12][13] | Dữ liệu và tệp người dùng được định giá; không so được với quy mô dự án |

## 5. Mô hình doanh thu giả định (đã hiệu chỉnh)

So với báo cáo kịch bản trước, hai giả định được **hạ xuống** theo dẫn chứng quốc tế: tỷ lệ xe bỏ đi (từ 10–50% xuống 5–20%, tham chiếu 14% của J.D. Power [8][14]) và tỷ lệ Tasco hưởng (từ 3–10% xuống 1–5%, tham chiếu net take rate dưới 1% của NaaS [11]). Các tham số còn lại giữ nguyên. Hai tham chiếu này chỉ là mốc so sánh, không phải cơ sở trực tiếp cho thị trường Việt Nam.

**Quy mô (giả định):** 14 trạm × 6 cổng = 84 cổng; số trạm theo demo của dự án, số cổng mỗi trạm là giả định. Phiên mỗi năm: ngày thường 235.200 (350 ngày × 8 phiên/cổng), lễ ngắn 9.408 (8 ngày × 14), Tết 11.760 (7 ngày × 20); tổng 256.368. Mức cao điểm 14 và 20 phiên/cổng/ngày, tức gấp 1,75 và 2,5 lần ngày thường, thấp hơn mức 2,4 lần và 4 lần quan sát được [1][3].

| Tham số (giả định) | Thận trọng | Cơ sở | Lạc quan |
| --- | ---: | ---: | ---: |
| Tỷ lệ phiên dùng lớp V-EV Flow | 10% | 25% | 40% |
| Tỷ lệ người lái chọn theo thói quen | 0% | 20% | 50% |
| Hệ số thực tế so với mô phỏng | 50% | 75% | 100% |
| Tỷ lệ xe không có cổng thực sự bỏ đi | 5% | 10% | 20% |
| Doanh thu mỗi phiên (VND) | 75.000 | 105.000 | 140.000 |
| Tỷ lệ Tasco hưởng | 1% | 3% | 5% |

Doanh thu mỗi phiên là tích của 25/30/35 kWh và 3.000/3.500/4.000 VND/kWh, chưa kiểm chứng. Công thức, với mức tăng lấy từ [15]:

```text
phiên cứu được = phiên_hành_lang × tỷ_lệ_áp_dụng
                 × mức_tăng_hiệu_dụng × hệ_số_thực_tế
                 × tỷ_lệ_bỏ_đi
mức_tăng_hiệu_dụng =
    (1 − tỷ_lệ_thói_quen) × tăng_so_với_đang_trống
    + tỷ_lệ_thói_quen × tăng_so_với_gần_nhất
```

## 6. Kết quả theo từng bên hưởng lợi

Một hành lang, một năm, triệu VND (trừ khi ghi khác). Tính từ mức tăng đo được [15] và các giả định ở mục 5.

| Chỉ số | Thận trọng | Cơ sở | Lạc quan |
| --- | ---: | ---: | ---: |
| Phiên sạc tăng thêm | 15 | 190 | 1.293 |
| Doanh thu phiên tăng thêm | 1,2 | 20,0 | 181,0 |
| **Đơn vị vận hành: phiên sạc được cứu** | 1,1 | 19,4 | 172,0 |
| **Đơn vị vận hành: giá trị what-if thêm cổng** (nếu hành động) | 16,5 | 69,2 | 246,0 |
| **Tasco: hoa hồng phiên sạc** | 0,01 | 0,6 | 9,1 |
| Tasco: hoa hồng nếu nhân lên mạng 350 trụ (×4,17) | 0,05 | 2,5 | 37,7 |

Phiên sạc được cứu chỉ bằng khoảng 0,07% doanh thu cả hành lang (khoảng 26,9 tỷ VND/năm) ở kịch bản cơ sở. Hệ số ×4,17 là 350 trụ chia 84 cổng, trong đó 350 trụ là số VETC công bố được trích trong Proposal của dự án và chưa kiểm chứng; phép nhân giả định mọi trụ có hồ sơ nhu cầu như hành lang cao tốc.

### 6.1. Đơn vị vận hành trạm

- Hưởng phần lớn doanh thu phiên tăng thêm (95–99% sau khi trừ hoa hồng).
- Công cụ what-if cho biết thêm cổng ở đâu hiệu quả: thêm 2 cổng tại S001 tăng tỷ lệ có cổng +2,6 / +9,4 / +15,2 điểm % (ngày thường / 30/4 / Tết) [15]. Kết quả dao động mạnh giữa các seed (ngày thường từ +0,0 đến +8,0 điểm %), và thí nghiệm này đổi cả model lẫn hạ tầng [15]. Chi phí đầu tư cổng chưa tính.
- Tải dàn đều theo trạm và theo giờ; thấy trước nơi quá tải bằng lớp Áp lực sạc.

### 6.2. Tasco / VETC

| Nguồn thu | Mức bằng chứng | Nhận định |
| --- | --- | --- |
| Hoa hồng phiên sạc | Giả định, tham chiếu NaaS [11] | Rất nhỏ: 0,6 triệu VND/năm ở kịch bản cơ sở. Không nên là luận điểm chính |
| Giữ chân người dùng và đối tác | Quốc tế: Tesla và Google đưa dự báo vào sản phẩm [4][6] | Có tiền lệ nhưng không lượng hóa được |
| Thuê bao Charging Intelligence cho đơn vị vận hành | Giả định thuần túy (hướng mở rộng trong Proposal của dự án) | Xem bên dưới |
| Dữ liệu và khảo sát cho hãng xe, quảng cáo | Quốc tế: PlugShare [12][13] | Hướng dài hạn, cần quy mô người dùng lớn |

**Giới hạn của thuê bao.** Giá trị mà đơn vị vận hành nhận được từ các mục đo ở bảng trên, kịch bản cơ sở, là khoảng 88,6 triệu VND/năm (19,4 + 69,2) cho cả hành lang. Nếu cả 14 trạm cùng đăng ký, mức phí để giá trị này bằng chi phí chỉ khoảng **0,5 triệu VND/trạm/tháng**. Ở kịch bản lạc quan mức này khoảng 2,5 triệu. Phí thuê bao hợp lý nên đặt theo giá trị đã chứng minh, và giá trị chỉ chứng minh được bằng pilot.

### 6.3. Người lái xe

Lợi ích là thời gian và độ tin cậy, không phải doanh thu: so với trạng thái thời gian thực, chờ trung bình giảm khoảng 0,3–0,6 phút; so với chọn trạm gần nhất, giảm nhiều hơn (dịp Tết từ 13,98 xuống 8,58 phút) [15]. Có trạm dự phòng và lý do giải thích cho từng gợi ý.

### 6.4. Doanh nghiệp vận tải, xã hội

Giảm thời gian xe gián đoạn và hành trình đi vòng. Chưa lượng hóa; dự án không tuyên bố giảm phát thải.

## 7. Những gì báo cáo này không chứng minh

- **Doanh thu thật.** Tất cả tiền tệ là giả định. Không có dữ liệu giá, chia doanh thu hay giao dịch của Tasco hoặc đối tác.
- **Độ chính xác ngoài thực tế.** Lịch sử trạng thái cổng là mô phỏng. Ở kịch bản Tết, AI + phân bổ chỉ hơn "đang trống" 1,8 điểm %, nằm trong độ dao động giữa các seed [15].
- **Việc xe bỏ đi.** Mô phỏng không có hành vi bỏ đi; tỷ lệ 5–20% chỉ tham chiếu khảo sát tự báo cáo ở Mỹ [8].
- **Tăng thêm thật sự.** Phiên sạc thêm có thể chỉ là chuyển từ trạm này sang trạm khác trong mạng VETC.
- **Chi phí.** Chưa có chi phí phát triển, vận hành, tích hợp, nên chưa kết luận được lợi nhuận.

## 8. Đề xuất để biến giả định thành bằng chứng

1. **Pilot đối chứng** trên một số trạm thật: nhóm dùng và không dùng gợi ý; đo phiên sạc hoàn tất và loại phiên chỉ chuyển trạm.
2. **Đo tỷ lệ xe bỏ đi thật** khi không có cổng, tách riêng nguyên nhân cột hỏng.
3. **Xin từ Tasco:** lịch sử trạng thái cổng (dù một mẫu nhỏ), giá bán, điều khoản chia doanh thu, lưu lượng thu phí tổng hợp theo giờ.
4. **Thử nghiệm dự báo cổng hỏng** như tính năng riêng, vì đây là nguyên nhân chính khiến xe không sạc được [8].
5. **Khảo sát mức sẵn sàng trả phí** của đơn vị vận hành.

Cách trình bày an toàn: "Cơ chế đã được chứng minh trên mô phỏng và có tiền lệ thị trường. Doanh thu phụ thuộc vài biến số chưa biết, và chúng tôi đề xuất pilot để đo chúng."

## 9. Nguồn tham khảo

Ngày truy cập: 10/2026. Các nguồn [8] và [14] là bài đăng lại; trang gốc của J.D. Power không truy cập được.

1. Trang chính phủ Thượng Hải, "Shanghai's highway EV charging hits record high", 11/10/2024, trích số liệu Cục Năng lượng Quốc gia Trung Quốc. https://english.shanghai.gov.cn/en-Latest-WhatsNew/20241011/e69b4d50f929444da27b893f571a6b65.html
2. China Daily, "Holiday rush fuels motorway charging", 2/3/2026. https://www.chinadaily.com.cn/a/202603/02/WS69a4ef5aa310d6866eb3b0e8.html
3. Báo Nghệ An, "Nghệ An: Trạm sạc xe điện quá tải dịp Tết, người dân xếp hàng xuyên đêm chờ nạp pin", 17/2/2026. https://baonghean.vn/nghe-an-tram-sac-xe-dien-qua-tai-dip-tet-nguoi-dan-xep-hang-xuyen-dem-cho-nap-pin-10324124.html
4. Electrek, "Tesla is starting to predict Supercharger availability at arrival", 16/10/2023. https://electrek.co/2023/10/16/tesla-predict-supercharger-availability-at-arrival/
5. Mobility Plaza, "Tesla enhances Supercharger wait-time forecasts with AI", 28/4/2026. https://www.mobilityplaza.com/news/tesla-enhances-supercharger-wait-time-forecasts-with-ai
6. TechCrunch, "Google Maps adds Gemini-powered tips section, EV charger availability predictions, and more", 19/11/2025. https://techcrunch.com/2025/11/19/google-maps-adds-gemini-powered-tips-section-ev-charger-availability-predictions-and-more/
7. arXiv:2605.26970, "Congestion Forecasting for Electric Vehicle Charging Scheduling with Fluid Queues", 26/5/2026. https://arxiv.org/html/2605.26970
8. evchargingstations.com, "J.D. Power: EV Chargers Becoming More Reliable With Fewer Failed Charging Attempts", 14/8/2025, về khảo sát J.D. Power 2025 U.S. EVX Public Charging Study. https://evchargingstations.com/chargingnews/j-d-power-ev-chargers-becoming-more-reliable/
9. Electrek, "Tesla still leads US fast-charger growth, but it's raised prices", 13/10/2026, trích báo cáo quý 3/2026 của Paren. https://electrek.co/2026/10/13/tesla-still-leads-us-supercharger-growth-but-its-raised-prices/
10. evchargingstations.com, "Tesla Expands Live Pricing to an Additional 550 Supercharging Sites", 18/11/2025, phát biểu của Max de Zegher (Tesla). https://evchargingstations.com/chargingnews/tesla-expands-live-pricing/
11. PR Newswire, "NaaS Technology Inc. Records Fifth Consecutive Month of Net Take Rate Growth", 8/3/2024. https://www.prnewswire.com/news-releases/naas-technology-inc-records-fifth-consecutive-month-of-net-take-rate-growth-302084098.html
12. Electrek, "EVgo acquires company behind popular PlugShare EV charging app", 14/7/2021. https://electrek.co/2021/07/14/evgo-acquires-plugshare-ev-charging-app/
13. EVgo Inc., Form 10-K năm tài chính 2021, mục "Recargo Acquisition" (mua 9/7/2021, 25,0 triệu USD tiền mặt). https://www.sec.gov/Archives/edgar/data/1821159/000155837022004199/evgo-20211231x10k.htm
14. Cars.com, "Reliability of Public EV Charging Infrastructure Improving, J.D. Power Finds", 13/8/2025. https://www.cars.com/articles/reliability-of-public-ev-charging-infrastructure-improving-j-d-power-finds-514244/
15. Dự án V-EV Flow, benchmark Runtime V2 mô phỏng (5 seed × 3 kịch bản × 100 xe; what-if thêm 2 cổng tại S001 và dịch 20% xe sang 21h), model `lightgbm-0e9c6bb20db734dd`, chạy tháng 10/2026. Đây là kết quả đo của chính dự án trên dữ liệu simulated, lưu tại `docs/runbooks/runtime-v2-evidence.md` trong kho mã. Số "350 trụ", tỷ lệ phiên VETC và tình trạng VETC Trạm sạc lấy từ Proposal gốc của dự án (`V-EV Flow – Proposal.md`), chưa kiểm chứng.
