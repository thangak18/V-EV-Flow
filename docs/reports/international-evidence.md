# V-EV Flow — Dẫn chứng quốc tế cho khả năng tạo doanh thu

*Các mô hình tương tự đã được triển khai ở nước ngoài và những gì chúng cho biết về doanh thu nếu V-EV Flow được đầu tư*

> **Tóm tắt trung thực.** Dẫn chứng quốc tế **ủng hộ mạnh** ba điều: nhu cầu sạc dồn vào kỳ nghỉ là có thật, dự báo khả dụng khi đến là sản phẩm đã được các hãng lớn triển khai, và dữ liệu về người lái xe điện có thể bán được. Dẫn chứng **không chứng minh** được rằng riêng việc dự báo tạo ra doanh thu lớn: Tesla và Google đưa tính năng này ra miễn phí, và các nền tảng gom trạm sạc lớn nhất Trung Quốc có tỷ lệ doanh thu ròng trên giao dịch rất thấp. Vì vậy báo cáo này đề xuất thay đổi cách đặt luận điểm doanh thu (xem mục 6).

Mọi số liệu dưới đây được tra từ nguồn công khai trong tháng 10/2026. Mục 7 ghi rõ số liệu nào đã đối chiếu với nguồn gốc và số liệu nào chưa.

## 1. Vấn đề có thật: nhu cầu sạc dồn vào kỳ nghỉ

| Dẫn chứng | Số liệu | Nguồn |
| --- | --- | --- |
| Trung Quốc, Quốc khánh 2024, các trạm cao tốc | Lượng sạc bình quân ngày gấp 2,4 lần ngày thường (10,3 triệu kWh so với khoảng 4,3 triệu kWh); 24.400 trạm, 3,1 triệu phiên sạc trong tuần | Cục Năng lượng Quốc gia Trung Quốc, qua trang chính phủ Thượng Hải (11/10/2024) |
| Trung Quốc, Tết Nguyên đán 2026 (15–23/2) | 6,02 triệu phiên sạc, 149,77 triệu kWh trên 53.300 cột sạc cao tốc; lượng sạc bình quân ngày tăng 52% so với năm trước | China Daily (2/3/2026) |
| Trung Quốc, Quốc khánh 2026 | Có tài xế báo tổng thời gian hơn 6 giờ kể cả sạc; mỗi phiên trung bình chỉ nạp khoảng 24,1 kWh; tỷ lệ xe điện trên điểm sạc công cộng khoảng 8:1 | 36Kr (10/10/2026) |
| Việt Nam, Tết 2026 tại Nghệ An | Lượt sạc tăng khoảng 4 lần ngày thường, xe xếp hàng xuyên đêm | Báo Nghệ An (17/2/2026), dẫn trong Proposal |

**Ý nghĩa:** mô hình doanh thu trước đó giả định lễ ngắn gấp 1,75 lần và Tết gấp 2,5 lần ngày thường. Hai mức này **không cao hơn** thực tế quan sát được ở Trung Quốc (2,4 lần) và Nghệ An (4 lần), nên giả định về cường độ cao điểm là thận trọng.

## 2. Dự báo khả dụng khi đến đã là sản phẩm thật

| Dẫn chứng | Nội dung | Nguồn |
| --- | --- | --- |
| Tesla, 10/2023 | Hiển thị số trụ dự kiến còn trống và thời gian chờ khi đến, dựa trên thời gian di chuyển của xe và các xe Tesla khác đang tới trạm. Hạn chế đã được nêu: kém chính xác hơn khi có xe không phải Tesla | Electrek (16/10/2023) |
| Tesla, nâng cấp 4/2026 | Mô hình học máy nhận diện xe có ý định sạc, huấn luyện trên dữ liệu quỹ đạo ẩn danh của 9 triệu dặm; sai số ước lượng độ dài hàng chờ giảm còn khoảng 20%; khi hơn 10 xe đang chờ, sai lệch còn 1–2 xe | Mobility Plaza (28/4/2026) |
| Google Maps, 11/2025 | Dùng AI phân tích dữ liệu khả dụng lịch sử và thời gian thực để dự báo số cột sạc còn trống khi đến; triển khai trên Android Auto và xe tích hợp Google | TechCrunch (19/11/2025) |

**Ý nghĩa:** các hãng lớn đã chứng minh nhu cầu và tính khả thi. Bài học đáng chú ý từ Tesla: độ chính xác phụ thuộc vào việc biết có bao nhiêu xe **đang hướng tới** trạm. Cơ chế tải ảo trong V-EV Flow cố gắng giải bài toán tương tự cho mạng đa thương hiệu, nơi không có dữ liệu đội xe riêng.

## 3. Mức độ hiệu quả: bằng chứng từ nghiên cứu

| Nghiên cứu | Kết quả | Loại bằng chứng |
| --- | --- | --- |
| Congestion Forecasting for EV Charging Scheduling with Fluid Queues (arXiv, 26/5/2026) | Chia sẻ thông tin tắc nghẽn giảm tới 14% thời gian chết so với lập lịch không có dự báo; hiệu quả lớn nhất ở trạm nhỏ ít cổng và khi mức tắc nghẽn trung bình vượt 50% | Mô phỏng Monte Carlo, không dùng dữ liệu thật |
| Optimizing EV Charging Station Placement Using RL and Agent-Based Simulations (arXiv, 3/11/2025), ca nghiên cứu Hà Nội | Giảm 53,28% thời gian chờ trung bình so với trạng thái ban đầu. Đây là bài toán **chọn vị trí và số cổng**, không phải gợi ý trạm | Mô phỏng; không rõ có dùng dữ liệu vận hành thật |

**Ý nghĩa:** các nghiên cứu độc lập cho kết quả cùng hướng với mô phỏng của dự án (thông tin tắc nghẽn giúp giảm chờ; thêm cổng giúp giảm chờ). Nhưng **tất cả đều là mô phỏng**, giống dự án, nên chưa phải bằng chứng ngoài thực tế. Kết quả "tới 14%" cũng cho thấy lợi ích phụ thuộc mạnh vào mức độ tắc nghẽn, phù hợp với việc dự án chỉ cải thiện rõ ở kịch bản lễ.

## 4. Cơ sở cho giả định "xe bỏ đi" (tham số nhạy nhất)

J.D. Power, khảo sát EVX về sạc công cộng tại Mỹ năm 2025 (7.428 chủ xe điện, khảo sát tháng 1–6/2025):

- 14% chủ xe điện cho biết từng đến trạm mà không sạc được, giảm từ 19% năm 2024.
- Lý do hàng đầu là cột sạc hỏng hoặc không hoạt động (60% số lần thất bại). Lý do chờ cột trống chiếm tỷ lệ nhỏ hơn nhiều, thay đổi theo vùng (khoảng 5–12%).

**Ý nghĩa:** đây là số đo thật duy nhất tìm được về xe rời trạm mà không sạc, nhưng nó là khảo sát tự báo cáo ở Mỹ, và nguyên nhân chính là **trạm hỏng**, không phải đông. Hai điểm rút ra:

- Tỷ lệ bỏ đi 25% (kịch bản cơ sở) và 50% (lạc quan) trong mô hình trước **khó được biện minh** bằng dẫn chứng này, vì chờ cột trống chỉ là một phần nhỏ trong số lần thất bại. Mức 10% (thận trọng) hợp lý hơn.
- Dự báo xác suất cổng hỏng (đã có trong mô phỏng) có thể là tính năng giá trị không kém dự báo cổng bận, vì lỗi trạm là nguyên nhân lớn nhất. Điều này đáng thử nghiệm khi có dữ liệu thật.

## 5. Các mô hình doanh thu thực tế gần nhất

### 5.1. Định giá theo nhu cầu: Tesla

Tesla đã thử nghiệm giá theo mức sử dụng trực tiếp từ năm 2025 và tuyên bố giảm tắc nghẽn giờ cao điểm, tăng mức sử dụng, **nhưng không công bố số liệu định lượng** (Tesla, 18/11/2025). Tại các trạm có giá theo khung giờ ở Mỹ, giá trung bình giờ cao điểm là 63,7 cent/kWh so với 43,8 cent giờ thấp điểm, chênh khoảng 45% (Paren, quý 3/2026, qua Electrek 13/10/2026).

**Ý nghĩa:** thị trường chấp nhận giá phân hóa theo giờ, và nhà vận hành thu được doanh thu cao hơn ở giờ đông. Tính năng gợi ý lệch giờ của V-EV Flow có thể kết hợp với giá giờ cao điểm và thấp điểm đã có trong ứng dụng VETC. Cần lưu ý: gợi ý lệch giờ trong mô phỏng của dự án cho kết quả không ổn định (xem báo cáo trước), nên chưa nên coi đây là nguồn doanh thu chắc chắn.

### 5.2. Nền tảng gom trạm sạc: NaaS Technology (Trung Quốc)

NaaS là nền tảng kết nối trạm sạc niêm yết trên Nasdaq. Tỷ lệ doanh thu ròng trên giá trị giao dịch (net take rate), đã trừ khuyến mãi trả cho người dùng, thay đổi như sau:

| Tháng | Net take rate |
| --- | ---: |
| 9/2023 | −8,14% |
| 12/2023 | −0,92% |
| 1/2024 | 0,02% |
| 2/2024 | 0,75% |

Nguồn: thông cáo của NaaS (8/3/2024).

**Ý nghĩa:** ngay cả nền tảng gom trạm lớn nhất Trung Quốc cũng chỉ đạt doanh thu ròng dưới 1% giá trị giao dịch tại thời điểm đó. Con số này bao gồm khuyến mãi người dùng, điều mà một lớp dự báo thuần túy không cần trả, nên không so sánh trực tiếp được. Nhưng nó là **bằng chứng rằng doanh thu hoa hồng mỏng**, ủng hộ kết luận trước đó là không nên dựa vào hoa hồng.

### 5.3. Dữ liệu và ứng dụng cho người lái: PlugShare

EVgo mua Recargo, công ty vận hành ứng dụng PlugShare, với giá **25 triệu USD tiền mặt** (ngày 9/7/2021, theo hồ sơ 10-K của EVgo). Recargo có nhiều nguồn thu ngoài ứng dụng: thanh toán, API dữ liệu cho hãng xe, bảng khảo sát người lái PlugInsights, quảng cáo di động (28 triệu lượt hiển thị quảng cáo năm 2021). Khoảng 7/10 chủ xe điện tại Mỹ đã tải ứng dụng.

**Ý nghĩa:** một ứng dụng hướng đến người lái được định giá nhờ **tệp người dùng và dữ liệu**, không nhờ hoa hồng phiên sạc. Cơ cấu doanh thu của PlugShare (dữ liệu, quảng cáo, nghiên cứu) tương ứng với hướng B2B và dữ liệu trong lộ trình của V-EV Flow. Giá 25 triệu USD phản ánh quy mô người dùng toàn nước Mỹ, không thể so với một dự án hackathon.

### 5.4. Các biện pháp vận hành ở Trung Quốc

Theo 36Kr và China Daily, các khu dịch vụ cao tốc đã áp dụng hệ thống số thứ tự, giới hạn sạc 80% để tăng vòng quay, chuyển xe sang khu dịch vụ bên kia hoặc trạm gần lối ra, và dùng công cụ theo dõi khả dụng theo thời gian thực. Đây là các biện pháp ứng với tính năng mức sạc khuyến nghị, phân bổ nhu cầu và lớp áp lực của V-EV Flow, cho thấy bài toán được coi là cần giải ở cấp quốc gia.

## 6. Đối chiếu với mô hình doanh thu của dự án

| Giả định trong mô hình trước | Dẫn chứng quốc tế | Đánh giá |
| --- | --- | --- |
| Lễ gấp 1,75–2,5 lần ngày thường | Trung Quốc 2,4 lần; Nghệ An 4 lần | **Thận trọng**, có cơ sở |
| Tỷ lệ xe bỏ đi 10–50% | Mỹ: 14% xe đến trạm không sạc được, chờ chỉ là nguyên nhân nhỏ | Mức 10% hợp lý; **25% và 50% thiếu cơ sở** |
| Tasco hưởng 3–10% doanh thu phiên | NaaS: net take rate dưới 1% (đã trừ khuyến mãi) | **Chưa có cơ sở**; nên xem 3–10% là cận trên |
| Thuê bao B2B 1–4 triệu VND/trạm/tháng | PlugShare cho thấy dữ liệu bán được, nhưng không có giá tham chiếu công khai | **Chưa kiểm chứng**; cần khảo sát khách hàng |
| Hiệu quả dự báo cùng hướng với mô phỏng | Nghiên cứu arXiv: giảm tới 14% thời gian chết, chỉ ở mô phỏng | Cùng hướng, **không phải bằng chứng thực tế** |

**Thay đổi nên làm khi thuyết phục:**

1. **Bỏ hoa hồng khỏi luận điểm chính.** Dẫn chứng quốc tế khẳng định kết luận trước: hoa hồng mỏng, nhất là sau khuyến mãi.
2. **Đặt giá trị chính ở tệp người dùng và dữ liệu**, theo mô hình PlugShare. Tính năng dự báo ở Tesla và Google được cung cấp miễn phí nhằm giữ người dùng, nên chiều giữ chân người dùng của VETC mới là phần có tiền lệ.
3. **Thêm dự báo cổng hỏng** như một tính năng riêng, vì đây là nguyên nhân chính khiến xe không sạc được.
4. **Dùng gợi ý lệch giờ kết hợp giá theo khung giờ** như hướng thử nghiệm, theo tiền lệ Tesla, nhưng nói rõ chưa có số liệu công bố.
5. **Đề xuất thử nghiệm đối chứng** vì chưa có hãng nào công bố số liệu doanh thu tăng thêm trực tiếp nhờ dự báo.

## 7. Mức độ kiểm chứng các nguồn

**Đã đọc trực tiếp nguồn gốc hoặc bản đăng lại đầy đủ:**

- Tesla 2023 (Electrek), Tesla 2026 (Mobility Plaza), Google Maps (TechCrunch).
- Quốc khánh 2024 (trang chính phủ Thượng Hải), Tết 2026 (China Daily), hàng chờ 2026 (36Kr).
- Hai bài arXiv (tóm tắt trên trang arXiv).
- Giá Tesla và Paren (Electrek 13/10/2026), tuyên bố của Tesla về giá động (evchargingstations.com).
- NaaS net take rate (thông cáo trên PR Newswire), mua PlugShare (10-K của EVgo và Electrek).

**Chỉ qua nguồn thứ cấp, mức độ tin cậy thấp hơn:**

- J.D. Power 2025: trang gốc trả lỗi truy cập; số liệu lấy từ evchargingstations.com và Cars.com. Tỷ lệ 60% do cột hỏng và khoảng 5–12% do chờ là từ bài đăng lại.
- Tỷ lệ 5–12% do chờ thay đổi theo vùng và cần đối chiếu với báo cáo gốc.

**Đã tìm thấy nhưng không dùng vì không xác minh được:**

- Một bài trên Nature Scientific Reports nêu giảm 63,3% thời gian chờ nhờ định tuyến nhận biết hàng chờ, nhưng không mở được trang gốc.
- Một con số "gross take rate" của NaaS khoảng 13–15% xuất hiện trong kết quả tìm kiếm nhưng không có trong thông cáo đã đọc, nên không dùng. Gross take rate (trước khi trừ chi phí và khuyến mãi) và net take rate (sau khi trừ) là hai chỉ số khác nhau, nên không thể dùng con số gross để suy ra doanh thu ròng.
- Một báo cáo thị trường nêu mức hoa hồng nền tảng gom 5–12%, nguồn thương mại không rõ phương pháp.

## 8. Nguồn

- Electrek, [Tesla is starting to predict Supercharger availability at arrival](https://electrek.co/2023/10/16/tesla-predict-supercharger-availability-at-arrival/), 16/10/2023.
- Mobility Plaza, [Tesla enhances Supercharger wait-time forecasts with AI](https://www.mobilityplaza.com/news/tesla-enhances-supercharger-wait-time-forecasts-with-ai), 28/4/2026.
- TechCrunch, [Google Maps adds Gemini-powered tips section, EV charger availability predictions, and more](https://techcrunch.com/2025/11/19/google-maps-adds-gemini-powered-tips-section-ev-charger-availability-predictions-and-more/), 19/11/2025.
- Trang chính phủ Thượng Hải, [Shanghai's highway EV charging hits record high](https://english.shanghai.gov.cn/en-Latest-WhatsNew/20241011/e69b4d50f929444da27b893f571a6b65.html), 11/10/2024.
- China Daily, [Holiday rush fuels motorway charging](https://www.chinadaily.com.cn/a/202603/02/WS69a4ef5aa310d6866eb3b0e8.html), 2/3/2026.
- 36Kr, [Why Do Long Queues at Expressway EV Charging Stations During Long Holidays Seem Permanently Unsolvable?](https://eu.36kr.com/en/p/4019957099909256), 10/10/2026.
- arXiv, [Congestion Forecasting for Electric Vehicle Charging Scheduling with Fluid Queues](https://arxiv.org/html/2605.26970), 26/5/2026.
- arXiv, [Optimizing Electric Vehicle Charging Station Placement Using Reinforcement Learning and Agent-Based Simulations](https://arxiv.org/abs/2511.01218), 3/11/2025.
- evchargingstations.com, [J.D. Power: EV Chargers Becoming More Reliable With Fewer Failed Charging Attempts](https://evchargingstations.com/chargingnews/j-d-power-ev-chargers-becoming-more-reliable/), 14/8/2025.
- Cars.com, [Reliability of Public EV Charging Infrastructure Improving, J.D. Power Finds](https://www.cars.com/articles/reliability-of-public-ev-charging-infrastructure-improving-j-d-power-finds-514244/), 13/8/2025.
- evchargingstations.com, [Tesla Expands Live Pricing to an Additional 550 Supercharging Sites](https://evchargingstations.com/chargingnews/tesla-expands-live-pricing/), 18/11/2025.
- Electrek, [Tesla still leads US fast-charger growth](https://electrek.co/2026/10/13/tesla-still-leads-us-supercharger-growth-but-its-raised-prices/), 13/10/2026.
- PR Newswire, [NaaS Technology Inc. Records Fifth Consecutive Month of Net Take Rate Growth](https://www.prnewswire.com/news-releases/naas-technology-inc-records-fifth-consecutive-month-of-net-take-rate-growth-302084098.html), 8/3/2024.
- Electrek, [EVgo acquires company behind popular PlugShare EV charging app](https://electrek.co/2021/07/14/evgo-acquires-plugshare-ev-charging-app/), 14/7/2021.
- EVgo, [Form 10-K năm 2021](https://www.sec.gov/Archives/edgar/data/1821159/000155837022004199/evgo-20211231x10k.htm).
- Báo Nghệ An, [Trạm sạc xe điện quá tải dịp Tết](https://baonghean.vn/nghe-an-tram-sac-xe-dien-qua-tai-dip-tet-nguoi-dan-xep-hang-xuyen-dem-cho-nap-pin-10324124.html), 17/2/2026 (dẫn trong Proposal của dự án).
