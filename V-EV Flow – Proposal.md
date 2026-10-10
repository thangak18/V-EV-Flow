# V-EV Flow – Dự báo và điều phối nhu cầu sạc xe điện trên hành lang cao tốc

*MLAI Hackathon 2026 · Bảng A · Đề xuất giải pháp: lớp ứng dụng trên nền tảng bản đồ của Tasco*

## 1. Tóm tắt

V-EV Flow là một lớp ứng dụng thông minh đặt trên bản đồ, giúp người lái xe điện biết **trạm sạc nào sẽ còn cổng khi mình thực sự đến**, thay vì chỉ biết trạng thái ở thời điểm hiện tại. Hệ thống trả lời ba câu hỏi: đi trạm nào, đi vào lúc nào, và nếu trạm đó gặp sự cố thì đi đâu tiếp theo. Đồng thời, hệ thống phân bổ các gợi ý giữa nhiều trạm để tránh việc nhiều xe cùng bị dẫn đến một chỗ.

Giải pháp nhắm vào một bài toán đặc trưng của Việt Nam: nhu cầu sạc dồn vào các hành lang cao tốc trong dịp lễ (Tết, 30/4, 2/9, cuối tuần về quê), trong khi ngày thường nhiều trụ sạc vắng. V-EV Flow được thiết kế để gắn vào VETC Trạm sạc và Vmap, tận dụng nền tảng và hệ sinh thái mà Tasco đang có. Ngoài việc chọn trạm và giờ sạc, hệ thống gợi ý mức sạc phù hợp để nhường chỗ khi trạm đông, và cho phép Tasco mô phỏng các phương án chuẩn bị trước mùa lễ.

## 2. Bối cảnh và vấn đề

**Xe điện đã phổ biến tại Việt Nam.** Theo số liệu của Bộ Xây dựng, đến hết tháng 5/2026 cả nước có khoảng 375 nghìn xe điện đăng ký lưu hành, trong đó 369.849 là ô tô con. Doanh số ô tô điện năm 2025 vượt 180.000 xe, chiếm hơn 30% thị phần ô tô. Theo IEA, xe điện và hybrid chiếm gần 40% doanh số ô tô mới tại Việt Nam, cao nhất Đông Nam Á.

**Nhiều chủ xe phụ thuộc vào sạc công cộng.** Báo cáo của PwC ghi nhận phần lớn người dùng xe điện tại Việt Nam không có chỗ sạc tại nhà.

**Nhu cầu dồn vào cao điểm.** Hiện tượng này đã được ghi nhận ở thị trường khác: tại Trung Quốc, trong tuần nghỉ Quốc khánh 2024, lượng sạc trung bình mỗi ngày tại các trạm cao tốc gấp 2,4 lần ngày thường. Việt Nam cũng đã ghi nhận hiện tượng tương tự, như trường hợp Nghệ An dịp Tết 2026 dưới đây.

**Bằng chứng tại Việt Nam: Tết 2026 ở Nghệ An.** Theo [Báo Nghệ An, ngày 17/02/2026](https://baonghean.vn/nghe-an-tram-sac-xe-dien-qua-tai-dip-tet-nguoi-dan-xep-hang-xuyen-dem-cho-nap-pin-10324124.html), nhiều trạm sạc trong tỉnh quá tải dịp Tết, người dân phải xếp hàng chờ đến lượt, có nơi xuyên đêm.

- Tối 30 Tết, một trạm ở xã Yên Thành có 2 cột, 4 đầu cắm đều kín chỗ, xe phải đỗ thành hàng chờ.
- Chủ trạm cho biết ngày thường có 40–60 lượt sạc mỗi ngày, dịp Tết tăng khoảng 4 lần.
- Một chủ xe từ Hà Nội về quê kiểm tra ứng dụng thấy trạm báo hết chỗ nhưng vẫn phải đến xếp hàng. Trường hợp này cho thấy biết trạng thái hiện tại chưa giúp người lái tìm được phương án thay thế.
- Chủ xe tự áp dụng cách sạc nhanh từ 10% lên khoảng 70% rồi nhường chỗ, và các chuyên gia khuyến nghị ưu tiên khung giờ thấp điểm. Đây là nhu cầu thực cho tính năng gợi ý lệch giờ và phân bổ nhu cầu.
- Toàn tỉnh có hơn 100 trạm với trên 500 cổng, khoảng cách trung bình giữa các trạm trên quốc lộ và cao tốc khoảng 65 km. Vì vậy một lần đến trạm kẹt hoặc hỏng rất tốn kém, và cần có trạm dự phòng.

Đây là một bài báo địa phương về một tỉnh, nhóm sẽ bổ sung thêm nguồn cho các hành lang khác khi có.

**Nền tảng của Tasco đã sẵn sàng để thêm lớp thông minh.** VETC Trạm sạc ra mắt giữa tháng 6/2026 và đến tháng 7/2026 đã kết nối 7 đối tác vận hành với hơn 350 trụ sạc, tương đương khoảng 50% mạng trạm đa thương hiệu. Người dùng đã có thể tìm trạm theo vị trí, công suất và tình trạng, dẫn đường, kích hoạt phiên sạc, thanh toán, xem trạng thái thời gian thực và đặt lịch. Theo các thông tin công bố mà nhóm tìm được, chưa thấy chức năng dự báo khả dụng tại thời điểm xe đến.

**Vấn đề cốt lõi:** biết trạm đang trống không có nghĩa là trạm sẽ trống khi xe đến sau 40 phút. Khi pin thấp và đang ở giữa hành trình liên tỉnh, một lần đến trạm kẹt hoặc trạm hỏng là rủi ro lớn đối với người lái.

## 3. Người dùng mục tiêu

| Nhóm | Nhu cầu | Giá trị V-EV Flow mang lại |
| --- | --- | --- |
| Chủ ô tô điện và hybrid sạc ngoài đi liên tỉnh | Chắc chắn sạc được trong hành trình, nhất là dịp lễ | Kế hoạch sạc có xác suất thành công và trạm dự phòng |
| Đơn vị vận tải dùng xe điện | Giảm thời gian xe gián đoạn | Lên lịch sạc tránh cao điểm |
| Đơn vị vận hành trạm sạc (đối tác của VETC) | Khai thác trụ đều hơn, giảm quá tải giờ cao điểm | Nhu cầu được dàn đều theo giờ và theo trạm |
| Tasco/VETC | Tăng phiên sạc hoàn tất trên nền tảng, giữ chân người dùng | Lớp thông minh tạo khác biệt cho VETC Trạm sạc |

Nhóm người dùng ban đầu là chủ xe điện và hybrid sử dụng mạng trạm đa thương hiệu. Mô hình dự báo không phụ thuộc vào một mạng cụ thể nên có thể mở rộng sang các mạng khác khi có dữ liệu.

## 4. Giải pháp

### 4.1. Các chức năng

**① Dự báo khả dụng tại thời điểm xe đến (Availability Prediction).** Với mỗi trạm trên tuyến, mô hình dự báo xác suất có ít nhất một cổng phù hợp và hoạt động bình thường sau số phút di chuyển còn lại (ETA).

**② Gợi ý theo mức pin (SOC-aware Recommendation).** Hệ thống kết hợp mức pin hiện tại, quãng đường, xác suất khả dụng, công suất, khả năng tương thích và mức pin dự phòng an toàn để đề xuất một trạm chính và một trạm dự phòng. Kết quả là một kế hoạch sạc kèm xác suất thành công tổng hợp.

**③ Gợi ý lệch giờ (Time-shift Advice).** Ngoài câu hỏi đi trạm nào, hệ thống trả lời câu hỏi đi lúc nào. Ví dụ: *Nếu xuất phát sớm 2 tiếng hoặc sạc sau 20h, xác suất có cổng tăng từ 40% lên 90%.* Tính năng này giải quyết gốc của vấn đề là nhu cầu dồn vào một khung giờ, và có thể kết hợp với giá sạc theo khung giờ cao điểm và thấp điểm mà ứng dụng VETC đã hiển thị. Chức năng này tái sử dụng cùng mô hình dự báo, chỉ chạy lại cho các mốc giờ khác nhau.

**④ Phân bổ nhu cầu (Demand Distribution).** Khi nhiều xe được gợi ý cùng lúc, mỗi gợi ý được cộng một lượng tải ảo vào trạm trong khung giờ xe dự kiến đến. Xe tiếp theo sẽ thấy xác suất đã giảm và được phân sang trạm khác. Đây là thuật toán tối ưu cập nhật liên tục, không cần mô hình AI riêng. Chức năng này xử lý vấn đề dự báo tự làm sai chính nó: nếu mọi người cùng được dẫn đến trạm có xác suất 85%, trạm đó sẽ kẹt.

**⑤ Giải thích lý do (Explainability).** Dưới mỗi xác suất, hệ thống hiện một dòng lý do dễ hiểu, ví dụ: *Giờ này thường vắng, không phải ngày lễ, trời không mưa.* Lý do được lấy từ mức đóng góp của các đặc trưng trong mô hình (feature importance hoặc SHAP). Cách này giúp người dùng tin vào con số và giúp nhà vận hành hiểu nguyên nhân quá tải.

**⑥ Lớp bản đồ Áp lực sạc.** Một lớp dữ liệu chuyên đề trên bản đồ thể hiện mức áp lực của từng trạm và hành lang theo thời gian, có thanh trượt: ngày thường, 30/4, Tết. Người dùng và nhà vận hành nhìn là thấy ngay nơi nào dễ quá tải.

**⑦ Mức sạc khuyến nghị (Charge-to Advice).** Thay vì mặc định sạc đầy, hệ thống gợi ý nên sạc đến bao nhiêu phần trăm. Mức này đủ để xe tới trạm kế tiếp hoặc trạm dự phòng với pin an toàn, và được giảm khi trạm đang đông để nhường chỗ cho xe khác. Bài báo Nghệ An ghi nhận chủ xe tự sạc nhanh từ 10% lên khoảng 70% rồi nhường chỗ dịp Tết; tính năng này biến thói quen đó thành khuyến nghị có tính toán. Công suất sạc thường giảm khi pin vượt khoảng 80%, nên phần cuối phiên sạc chiếm cổng lâu hơn. Trong demo dùng đường cong sạc đơn giản, khi có dữ liệu thật sẽ hiệu chỉnh theo từng dòng xe.

**⑧ Mô phỏng mùa lễ (What-if Digital Twin).** Dành cho Tasco và đơn vị vận hành: một bảng điều khiển cho phép đặt giả định và xem kết quả trên chính simulator của demo. Ví dụ: thêm 2 trụ ở một trạm, hoặc dời 20% lượng xe sang sạc lệch 2 giờ, thì tỷ lệ xe đến nơi có cổng và số km đi vòng thay đổi ra sao. Bảng này biến lớp bản đồ thành công cụ chuẩn bị trước mùa cao điểm thay vì chỉ cảnh báo khi đã quá tải. Kết quả mang tính tham khảo vì dựa trên dữ liệu mô phỏng.

**⑨ Báo cáo cộng đồng (nếu kịp thời gian).** Người dùng có thể báo nhanh *trụ hỏng* hoặc *xe chiếm chỗ*. Dữ liệu này bổ sung cho trạng thái từ đối tác và là đầu vào cho mô hình khi triển khai thật.

### 4.2. Kịch bản minh họa

Chủ xe điện khởi hành đi liên tỉnh vào dịp lễ, pin còn 20%. Hệ thống nhận mức pin, điểm đến, các trạm trên tuyến và trạng thái cổng hiện tại, sau đó trả về:

| Tiêu chí | Trạm A | Trạm B |
| --- | --- | --- |
| Khoảng cách | 4 km | 9 km |
| Xác suất có cổng trống tại ETA | 25% | 85% |
| Mức pin dự kiến khi đến | 18% | 16% |
| Khuyến nghị | Không ưu tiên | Ưu tiên (kèm trạm dự phòng) |

*Số liệu minh họa.* Hệ thống đề xuất trạm B vì xe vẫn đủ pin an toàn để đến nơi. Nếu người dùng linh hoạt về giờ, hệ thống bổ sung gợi ý lệch giờ để tăng xác suất sạc thành công.

## 5. Vai trò thiết yếu của bản đồ

Bài toán không thể giải nếu thiếu yếu tố không gian. Bản đồ cung cấp tuyến đường, thời gian di chuyển (ETA) và khoảng cách đến từng trạm, là cơ sở để tính mức pin khi đến và xác suất khả dụng đúng thời điểm. Dịch vụ bản đồ Goong được dùng cho chỉ đường, ước tính thời gian và hiển thị lớp dữ liệu. Lớp Áp lực sạc là một lớp dữ liệu chuyên đề mới, thể hiện nhu cầu hạ tầng theo không gian và thời gian mà các bản đồ phổ thông chưa có.

### 5.1. So sánh với giải pháp hiện có

Nhu cầu dự báo khả dụng khi xe đến đã được các nền tảng lớn chứng minh là có thật. Điểm khác của V-EV Flow nằm ở bối cảnh áp dụng và cách gắn vào hệ sinh thái.

| Giải pháp | Đã có | Khác biệt của V-EV Flow |
| --- | --- | --- |
| [Tesla](https://www.techradar.com/vehicle-tech/hybrid-electric-vehicles/teslas-can-now-predict-future-supercharger-availability-for-smoother-ev-trips) | Dự báo số trụ trống và thời gian chờ khi đến, dựa trên thời gian di chuyển của xe và các xe Tesla khác đang tới trạm | Chủ yếu dựa trên dữ liệu đội xe và mạng của Tesla; V-EV Flow hướng tới mạng sạc đa thương hiệu trong VETC |
| [Google Maps](https://engadget.com/apps/google-maps-will-use-ai-to-predict-if-ev-chargers-will-be-available-on-arrival-191808879.html) | Dự báo số trụ khả dụng khi đến, ban đầu trên Android Auto và xe có Google tích hợp | Theo [hướng dẫn tại Việt Nam](https://vnreview.vn/threads/huong-dan-cach-tim-tram-sac-xe-dien-nhanh-nhat-2024.45314/latest), bản đồ hiển thị loại cổng, tốc độ, số cổng và giờ hoạt động; nhóm chưa thấy nguồn nói có dự báo khả dụng cho trạm Việt Nam |
| [HERE](https://here.com/solutions/ev-routing-charging-optimization) | Mô hình học máy dự báo khả dụng, cung cấp cho hãng xe và nhà phát triển | Giải pháp B2B toàn cầu; nhóm chưa thấy thông tin về bản địa hóa theo lịch và mạng sạc Việt Nam |
| [Trạm Sạc EVCS.VN](https://apps.apple.com/app/id6733224950) | Gom nhiều mạng sạc, hiển thị trạng thái, đề xuất trạm dọc tuyến | Mô tả ứng dụng không nhắc đến dự báo hay phân bổ nhu cầu |
| VETC Trạm sạc | Trạng thái thời gian thực, đặt lịch, kích hoạt và thanh toán | Chưa thấy dự báo tại thời điểm xe đến; V-EV Flow là lớp bổ sung |

**Định vị:** Google và Tesla đã chứng minh nhu cầu dự báo khả dụng là có thật. V-EV Flow áp dụng cho mạng sạc đa thương hiệu của Việt Nam, học theo mùa vụ về quê của người Việt, và gắn vào luồng đặt lịch, thanh toán của VETC. Nhóm không khẳng định chưa ai làm; phần so sánh dựa trên thông tin công khai mà nhóm tìm được.

## 6. Dữ liệu và AI

### 6.1. Dữ liệu

| Dữ liệu | Nguồn | Trạng thái trong demo |
| --- | --- | --- |
| Vị trí và thông số trạm sạc | OpenStreetMap, Open Charge Map, Goong Places, bổ sung thủ công | Thật, bổ sung giả định |
| Tuyến đường, ETA, khoảng cách | Goong | Thật |
| Thời tiết | Open-Meteo | Thật |
| Lịch lễ Việt Nam | Nhập thủ công | Thật |
| Số cổng, công suất mỗi trạm | Giả định theo thông số phổ biến | Giả định |
| **Lịch sử trạng thái cổng sạc** | Mô phỏng bằng mô hình hàng đợi (SimPy) | **Giả lập** |
| Mức tiêu thụ pin theo quãng đường | Công thức đơn giản theo loại xe | Giả định |
| Lưu lượng thu phí tổng hợp theo giờ (VETC) | Đề xuất Tasco chia sẻ | Mô phỏng nếu chưa có |

Lịch sử trạng thái cổng sạc được mô phỏng với tốc độ xe đến thay đổi theo giờ, thứ trong tuần, ngày lễ và loại trạm, kèm xác suất cổng hỏng ngẫu nhiên. Hệ thống ghi một bản chụp trạng thái mỗi 5 phút trong 6–12 tháng. Khi có dữ liệu thật từ Tasco hoặc đối tác, chỉ cần thay nguồn dữ liệu đầu vào.

### 6.2. Mô hình dự báo

- **Bài toán:** phân loại nhị phân, dự báo có ít nhất một cổng phù hợp còn trống sau ETA phút.
- **Đặc trưng:** số cổng trống, bận, hỏng hiện tại; số cổng trống 15, 30, 60 phút trước; giờ và thứ trong tuần; cờ ngày lễ; mưa; loại trạm và công suất; ETA. Nếu có, thêm lưu lượng thu phí tổng hợp trên hành lang làm tín hiệu sớm.
- **Mô hình:** LightGBM hoặc XGBoost, sau đó hiệu chỉnh xác suất (isotonic hoặc Platt) để con số hiển thị có ý nghĩa.
- **Đánh giá:** chia dữ liệu huấn luyện và kiểm tra theo thời gian, so sánh với ba phương án cơ bản là chọn trạm gần nhất, chọn trạm đang trống và giữ nguyên trạng thái hiện tại. Chỉ số: AUC, Brier score, biểu đồ hiệu chỉnh.

### 6.3. Lớp gợi ý và phân bổ

Mức pin dự kiến khi đến được tính từ mức pin hiện tại, quãng đường và mức tiêu thụ. Các trạm làm mức pin xuống dưới ngưỡng dự phòng bị loại. Các trạm còn lại được xếp hạng theo thời gian đi, thời gian chờ kỳ vọng và mức phạt rủi ro. Xác suất sạc thành công của cặp trạm chính và dự phòng được ước tính là 1 − (1 − pA)(1 − pB), với giả định hai trạm độc lập.

### 6.4. Giới hạn cần nói rõ

Vì lịch sử trạng thái trong demo là dữ liệu mô phỏng, kết quả đo được chứng minh rằng quy trình dữ liệu và mô hình hoạt động, chưa khẳng định độ chính xác ngoài thực tế. Nhóm sẽ hiệu chỉnh tham số mô phỏng bằng một mẫu dữ liệu thật nhỏ nếu được Tasco hoặc mentor cung cấp.

## 7. Phù hợp với Việt Nam

- **Lịch Việt Nam:** mô hình nhu cầu có yếu tố Tết, 30/4, 2/9 và cuối tuần về quê, vốn là các đỉnh di chuyển liên tỉnh quen thuộc.
- **Thời tiết:** mưa ảnh hưởng đến hành vi di chuyển và nhu cầu sạc.
- **Hạ tầng phân mảnh:** nhiều đơn vị vận hành, nhiều ứng dụng riêng. Giải pháp tận dụng nền tảng liên thông của VETC thay vì yêu cầu hạ tầng mới.
- **Điều kiện dữ liệu:** thiết kế chịu được tình huống dữ liệu còn hạn chế, bắt đầu bằng dữ liệu mô phỏng và chuyển dần sang dữ liệu thật.

## 8. Giá trị đối với Tasco

### 8.1. Nguồn 1: tăng giao dịch sạc qua VETC

Khi hệ thống giúp người dùng chọn đúng trạm và đúng giờ, nhiều phiên sạc hoàn tất hơn trên nền tảng. VETC cho biết các mạng sạc đã kết nối ghi nhận số phiên sạc tăng đáng kể, cho thấy mô hình nền tảng mở có tiềm năng. Doanh thu tăng thêm có thể tính theo thỏa thuận thương mại giữa VETC và đối tác vận hành; điều khoản thực tế nhóm chưa biết nên đây là giả định.

Để tránh tính trùng, nhóm đề xuất đo **giao dịch tăng thêm thực sự**, ví dụ so sánh nhóm dùng gợi ý với nhóm không dùng, và loại các giao dịch chỉ chuyển từ trạm này sang trạm khác.

### 8.2. Giá trị khác

- Giữ chân người dùng trong ứng dụng VETC và hệ sinh thái điểm thưởng Tasco.
- Giúp đối tác vận hành khai thác trụ đều hơn, tạo động lực để họ ở lại và mở rộng trên nền tảng.
- Gợi ý lệch giờ góp phần dàn đều tải, giảm quá tải giờ cao điểm.

### 8.3. Hướng mở rộng: Charging Intelligence cho đơn vị vận hành

Sau MVP, các kết quả dự báo có thể đóng gói thành công cụ chuẩn bị mùa cao điểm cho đơn vị vận hành: dự báo khung giờ nhu cầu cao, xác định trạm quá tải hoặc ít sử dụng, hỗ trợ quyết định phân bổ công suất hoặc mở rộng. Hướng này chỉ đưa vào lộ trình, không nằm trong MVP.

## 9. Tác động xã hội và chỉ số đo lường

| Đối tượng | Tác động kỳ vọng | Chỉ số đánh giá |
| --- | --- | --- |
| Người lái xe điện | Giảm nguy cơ đến trạm không có cổng trống | Tỷ lệ tìm được cổng khả dụng khi đến |
| Doanh nghiệp vận tải | Giảm thời gian xe gián đoạn vì tìm nơi sạc | Thời gian xe ngừng hoạt động |
| Đơn vị vận hành | Khai thác trụ hiệu quả hơn, dàn đều tải | Tỷ lệ sử dụng trụ giờ cao điểm so với giờ thấp |
| Xã hội | Giảm hành trình đi vòng để tìm trạm | Số km phát sinh mỗi phiên sạc |

Nhóm không tuyên bố giảm phát thải ở giai đoạn này vì cần thêm dữ liệu về năng lượng và quãng đường thực tế.

## 10. Trả lời ba câu hỏi của Tasco

| Câu hỏi | Trả lời |
| --- | --- |
| **Người dùng mục tiêu là ai?** | Chủ ô tô điện và hybrid đi liên tỉnh, đơn vị vận tải điện; nhóm hưởng lợi thứ hai là đơn vị vận hành trạm và Tasco/VETC. |
| **Ưu tiên tiêu chí nào?** | Độ chính xác và độ tin cậy của dự báo (tránh đưa người dùng đến trạm kẹt khi pin thấp), cùng khả năng mở rộng. Tốc độ và chi phí xếp sau. |
| **Tích hợp ra sao?** | Một lớp Dự báo khả dụng gắn vào VETC Trạm sạc và Vmap qua API: nhận trạng thái cổng và hành trình, trả về xác suất, khuyến nghị và lý do. |

## 11. Kiến trúc và tích hợp

- **Giao diện web:** bản đồ Goong, danh sách trạm, thanh trượt thời gian, thẻ khuyến nghị.
- **Backend:** dịch vụ API (ví dụ FastAPI) gồm mô-đun dự báo, mô-đun gợi ý và mô-đun phân bổ.
- **Dữ liệu:** cơ sở dữ liệu lưu trạng thái trạm, lịch sử và báo cáo cộng đồng.
- **Simulator:** tiến trình đẩy trạng thái cổng mô phỏng để demo giống thời gian thực.
- **Điểm tích hợp với hệ sinh thái Tasco:** API nhận trạng thái trạm từ VETC Trạm sạc, trả kết quả dự báo để hiển thị trong ứng dụng VETC và Vmap.

## 12. Phạm vi MVP và kịch bản demo

**MVP gồm:** dự báo khả dụng tại ETA, gợi ý theo mức pin với trạm dự phòng, phân bổ nhu cầu, gợi ý lệch giờ, giải thích lý do, lớp bản đồ Áp lực sạc, mức sạc khuyến nghị và bảng mô phỏng mùa lễ. Báo cáo cộng đồng làm nếu còn thời gian. Dashboard cho đơn vị vận hành, tính phát thải và các phương thức di chuyển khác nằm ngoài MVP.

**Phạm vi thử nghiệm:** một hành lang cao tốc với khoảng 10–20 trạm (đề xuất TP.HCM–Vũng Tàu hoặc Hà Nội–Hải Phòng, chọn theo dữ liệu có được).

**Kịch bản demo:**

1. Xe còn 20% pin, so sánh “trạm gần nhất” với gợi ý của V-EV Flow.
2. Kéo thanh trượt từ ngày thường sang 30/4 và Tết để xem lớp Áp lực sạc thay đổi.
3. Hiển thị gợi ý lệch giờ, mức sạc khuyến nghị và lý do đi kèm.
4. Mô phỏng 100 xe cùng cần sạc trong giờ cao điểm và so sánh ba chiến lược: gần nhất, đang trống, và dự báo kèm phân bổ. Chỉ số hiển thị là tỷ lệ xe đến nơi có cổng trống và số km đi vòng trung bình. Cuối cùng dùng bảng mô phỏng mùa lễ: thêm 2 trụ ở một trạm hoặc dời 20% lượng xe sang sạc lệch 2 giờ, rồi xem tỷ lệ xe có cổng thay đổi thế nào.

## 13. Rủi ro và giả định

| Rủi ro hoặc giả định | Cách xử lý |
| --- | --- |
| Chưa chắc có lịch sử trạng thái cổng thật | Dùng dữ liệu mô phỏng, nói rõ giới hạn, thiết kế để thay bằng dữ liệu thật |
| Chưa chắc có dữ liệu lưu lượng thu phí | Mô phỏng trong demo, xác nhận với mentor |
| Dự báo có thể tự làm sai khi nhiều xe cùng nghe theo | Mô-đun phân bổ cộng tải ảo theo từng gợi ý |
| Mạng VETC không bao gồm hệ sinh thái VinFast | Mô hình không phụ thuộc mạng, demo trên trạm VETC |
| Giao dịch tăng thêm có thể chỉ là chuyển dịch giữa các trạm | Đo bằng so sánh nhóm dùng và không dùng gợi ý |
| Giả định hai trạm độc lập khi tính xác suất kế hoạch | Ghi rõ giả định, cải tiến sau khi có dữ liệu |

## 14. Lộ trình mở rộng

1. **Giai đoạn 1 – Hackathon:** demo trên một hành lang với dữ liệu mô phỏng.
2. **Giai đoạn 2 – Thử nghiệm:** nhận dữ liệu lịch sử thật từ một số trạm đối tác, hiệu chỉnh và đánh giá so với ba phương án cơ bản.
3. **Giai đoạn 3 – Tích hợp:** đưa lớp dự báo vào VETC Trạm sạc và Vmap, đo giao dịch tăng thêm.
4. **Giai đoạn 4 – Mở rộng:** mở công cụ chuẩn bị mùa cao điểm cho đơn vị vận hành, thêm dữ liệu năng lượng để đánh giá phát thải.

## 15. Các điểm cần xác nhận với mentor

1. Tasco có cung cấp lịch sử trạng thái cổng sạc không, dù chỉ một mẫu nhỏ?
2. Có thể chia sẻ dữ liệu lưu lượng thu phí tổng hợp theo giờ không?
3. VETC hiện đã có chức năng dự báo khả dụng tại thời điểm xe đến chưa?
4. Điều khoản thương mại giữa VETC và đối tác vận hành trạm thường như thế nào để nhóm xây mô hình doanh thu sát thực tế?

## Nguồn số liệu tham khảo

- Bộ Xây dựng, số liệu xe điện đến hết tháng 5/2026 (qua Diễn đàn Doanh nghiệp và Tạp chí Kinh tế Tài chính).
- PwC, báo cáo thị trường ô tô ASEAN-6 và thị trường xe điện ASEAN; IEA, Global EV Outlook 2026 (qua VnBusiness).
- VETC và Tasco, thông tin ra mắt và mở rộng VETC Trạm sạc tháng 6–7/2026 (qua VTV, VnEconomy, Báo Pháp luật).
- National Energy Administration và State Grid Shanghai, số liệu sạc cao tốc trong tuần Quốc khánh 2024 (qua english.shanghai.gov.cn).
- Báo Nghệ An (17/02/2026), [Nghệ An: Trạm sạc xe điện quá tải dịp Tết, người dân xếp hàng xuyên đêm chờ nạp pin](https://baonghean.vn/nghe-an-tram-sac-xe-dien-qua-tai-dip-tet-nguoi-dan-xep-hang-xuyen-dem-cho-nap-pin-10324124.html).
