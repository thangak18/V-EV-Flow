# Hướng dẫn sử dụng V-EV Flow — Driver và Operator

Tài liệu giải thích từng phần trên giao diện: dùng để làm gì, thao tác thế nào và đọc kết quả ra sao.

> Bản hiện tại dùng **dữ liệu trạng thái trạm mô phỏng (simulated)**. Tìm địa điểm, nền bản đồ và các tuyến đường có thể lấy thật từ Goong; điều đó **không có nghĩa trạng thái cổng sạc là dữ liệu trực tiếp**. Dự báo không phải xác nhận giữ chỗ.

## 1. Mở đúng không gian làm việc

| Không gian | Đường dẫn | Dùng cho việc gì? |
| --- | --- | --- |
| **Tài xế — Driver** | `/driver` | Tìm trạm phù hợp với hành trình, pin và đầu cắm; chuẩn bị trạm dự phòng. |
| **Điều hành — Operator** | `/operator` | Theo dõi nguy cơ hết chỗ theo khu vực; so sánh điều phối và thử phương án cải thiện. |

Trên máy đang chạy sản phẩm, mở:

- Driver: <http://127.0.0.1:5176/driver>.
- Operator: <http://127.0.0.1:5176/operator>.

Nếu chạy ứng dụng ở cổng/địa chỉ khác, giữ `/driver` hoặc `/operator` và thay phần địa chỉ phía trước. Địa chỉ `127.0.0.1` chỉ mở trên chính máy đang chạy web.

### Thanh đầu trang

| Thành phần | Ý nghĩa và cách dùng |
| --- | --- |
| **DÀNH CHO TÀI XẾ / TRUNG TÂM ĐIỀU HÀNH** | Cho biết bạn đang ở không gian nào. |
| **Chuyển không gian** | Bấm mở menu, chọn **Tài xế** hoặc **Điều hành**. |
| Dòng kết nối backend/model | Cho biết cấu hình dịch vụ đang kết nối. Không phải bằng chứng rằng mọi dịch vụ bản đồ hoặc trạm ngoài thực tế đều đang hoạt động. |
| **Đặt lại phiên** | Xóa tải phân bổ ảo của backend và đưa màn hình hiện tại về trạng thái ban đầu sau khi đặt lại thành công. Dùng khi muốn bắt đầu lượt trình diễn mới. Không xóa model/lịch sử trạm và không hủy hay tạo đặt chỗ vật lý. |

**Kịch bản của hai trang độc lập.** Chọn Tết ở Driver không tự chuyển Operator sang Tết. Khi sang Operator, kiểm tra nhãn **Đang xem / Đã chọn** và chọn lại kịch bản nếu cần.

## 2. Driver — Tìm kế hoạch sạc cho một hành trình

### 2.1. Quy trình nhanh

1. Chờ kết nối dữ liệu trạm hoàn tất.
2. Chọn **Điểm đi** và **Điểm đến** trong danh sách gợi ý.
3. Chọn **Kịch bản**, nhập **Pin hiện tại**, kiểm tra **Đầu cắm**.
4. Nếu cần, mở **Thông số xe** để chỉnh dung lượng pin và mức tiêu hao.
5. Bấm **Tìm kế hoạch sạc**.
6. Đọc trạm chính, trạm dự phòng, xác suất còn cổng và pin khi đến.
7. Xem các tuyến trên bản đồ; bấm **Định vị trạm chính/dự phòng** để phóng đến từng trạm.

### 2.2. Các ô nhập hành trình và xe

| Thành phần | Dùng để làm gì? | Thao tác |
| --- | --- | --- |
| **Điểm đi** | Nơi bắt đầu hành trình. | Gõ tên địa điểm, chọn một gợi ý để xác nhận tọa độ. |
| **Điểm đến** | Đích cuối hành trình. | Chọn tương tự điểm đi. Hai địa điểm phải có tọa độ khác nhau. |
| **Kịch bản** | Chọn điều kiện nhu cầu sạc mô phỏng: Ngày thường, Lễ 30/4 hoặc Tết. | Chọn kịch bản trước khi tìm kế hoạch; đây không phải thao tác đổi ngày thực tế. |
| **Pin hiện tại (SOC %)** | Phần trăm pin xe đang còn. Hệ thống dùng để kiểm tra có đủ pin đến trạm không. | Nhập từ 0 đến 100. Ví dụ 20 nghĩa là còn 20% pin. |
| **Đầu cắm** | Kiểm tra trạm có hỗ trợ loại cổng của xe. | Nhập đúng tên loại cổng, ví dụ `CCS2`; không để trống. |
| **Thông số xe** | Chứa các thông số ảnh hưởng đến ước tính pin khi đến. | Bấm để mở/đóng phần nâng cao. |
| **Dung lượng pin (kWh)** | Dung lượng bộ pin dùng trong phép tính. | Nhập số lớn hơn 0; giá trị khởi tạo hiện tại là 60 kWh. |
| **Tiêu hao (kWh/km)** | Năng lượng ước tính xe dùng cho mỗi km. | Nhập số lớn hơn 0; 0,18 kWh/km tương đương 18 kWh/100 km. |
| **Tìm kế hoạch sạc** | Gửi hành trình và thông số để chọn trạm. | Bấm sau khi thông tin hợp lệ. Chờ kết quả trước khi thao tác tiếp. |

Giá trị khởi tạo không tự đại diện chính xác cho mọi mẫu xe. Sau khi sửa SOC hoặc thông số xe, bấm **Tìm kế hoạch sạc** để tính lại; kết quả đang xem không tự cập nhật chỉ vì bạn sửa ô nhập.

### 2.3. Chọn địa điểm đúng cách

Khi Goong Places đang kết nối:

1. Bấm ô địa điểm hoặc nút mở danh sách.
2. Chọn nguồn **Địa điểm Goong**, nhập ít nhất 2 ký tự.
3. Chờ gợi ý và bấm đúng địa điểm.
4. Nếu muốn chọn vị trí trạm trong dữ liệu hiện có, chuyển nguồn sang **Danh mục trạm**.

Chỉ gõ tên địa điểm chưa đủ: phải chọn một gợi ý để có tọa độ. Nếu sửa tên đã chọn, chọn lại gợi ý trước khi tìm kế hoạch.

**Danh mục trạm** là các trạm đã có dữ liệu trong hệ thống; không phải kết quả tìm tất cả trạm trên bản đồ. Khi dịch vụ tìm địa điểm không được cấu hình, giao diện dùng danh sách địa điểm có sẵn.

Bạn có thể tìm địa điểm ngoài hành lang dữ liệu, nhưng hệ thống chỉ gợi ý những trạm trong danh mục có dữ liệu và có thể tiếp cận được với pin/horizon hiện tại. Tìm được địa chỉ không đồng nghĩa có phủ dữ liệu sạc tại địa chỉ đó.

### 2.4. Dòng “Dữ liệu lúc…”

Đây là mốc trạng thái trạm backend cung cấp, hiển thị theo giờ Việt Nam. Người lái không cần nhập chuỗi thời gian.

- Với chế độ phát lại lịch sử mô phỏng, hệ thống sử dụng mốc trong dữ liệu; không nhất thiết là giờ hiện tại trên máy.
- Giới hạn dự báo hiển thị trên form do backend cung cấp. Release đang dùng hỗ trợ tối đa 180 phút.
- Trạm nằm ngoài khả năng dự báo hoặc không đủ điều kiện sẽ không được suy diễn thành một phương án hợp lệ.

### 2.5. Đọc thẻ “Trạm chính”

| Thông tin | Cách hiểu |
| --- | --- |
| **Tên trạm** | Trạm được ưu tiên trong kế hoạch. |
| **Khả năng có cổng** | Xác suất mô hình ước tính còn cổng tại lúc bạn đến. Ví dụ 80% không phải “80% cổng đang trống”. |
| **Đến lúc (+07:00)** | ETA dự kiến dùng cho kế hoạch/dự báo, hiển thị theo giờ Việt Nam. Không phải thời điểm sạc xong. |
| **Từ điểm xuất phát** | Quãng đường từ điểm đi đến trạm. |
| **Pin khi đến** | SOC còn lại ước tính sau quãng đường tới trạm. Không phải lượng pin sẽ sạc thêm. |
| **Đi thêm để ghé trạm** | Quãng đường phát sinh để ghé trạm so với hành trình tham chiếu. |
| **Khả năng kế hoạch có chỗ** | Ước lượng cho kế hoạch có cả phương án dự phòng khi có dữ liệu; có thể dùng giả định hai trạm độc lập. Xem phần độ tin cậy trước khi diễn giải. |
| **Định vị trạm chính** | Phóng bản đồ đến trạm, làm nổi bật marker và mở thẻ thông tin. Không tạo lại kế hoạch hoặc ghi thêm phân bổ. |

### 2.6. Đọc “Trạm dự phòng / Phương án B”

Đây là trạm có thể đi tiếp nếu trạm chính không còn chỗ.

- Xác suất, giờ đến, pin còn lại và tổng quãng đường **đã tính hành trình qua trạm chính rồi mới tới trạm dự phòng**.
- Không đọc pin/ETA dự phòng như thể xe đi thẳng từ điểm xuất phát tới đó.
- **Định vị trạm dự phòng** phóng đến đúng trạm dự phòng, không chỉ cuộn đến bản đồ.
- Không có trạm dự phòng nghĩa là hệ thống chưa tìm được phương án B thỏa điều kiện; không tự suy ra mọi trạm khác đều đóng cửa.
- Nút định vị có thể bị vô hiệu hóa nếu danh mục không có tọa độ trạm.

### 2.7. Các mục giải thích

| Mục | Khi nào nên mở? | Đọc thế nào? |
| --- | --- | --- |
| **Vì sao kế hoạch này phù hợp?** | Muốn biết nguyên nhân chọn hoặc loại trạm. | Đọc các lý do liên quan tới hành trình, pin, khả dụng và điều kiện phân bổ. |
| **Vì sao có dự báo này?** | Muốn xem những yếu tố ảnh hưởng tới dự báo của model; chỉ hiện khi có phần giải thích. | Các đóng góp SHAP làm tăng/giảm điểm model; không phải phần trăm xác suất cộng thẳng. Xác suất hiển thị đã qua hiệu chỉnh. |
| **Cách tính & độ tin cậy** | Muốn hiểu xác suất, pin khi đến, đường vòng và giới hạn của kế hoạch. | Chú ý giả định độc lập giữa hai trạm và nguồn dữ liệu. |
| **Thông tin kiểm chứng mô hình** | Khi kiểm thử hoặc đối chiếu với nhóm phát triển. | Xem phiên bản model và phương pháp phân bổ; không cần chỉnh gì ở đây. |
| **Gợi ý khởi hành lệch giờ** | Khi hệ thống tìm được một giờ khởi hành muộn hơn có thể cải thiện xác suất. | Đọc số phút dời, giờ khởi hành, xác suất mới và mức tăng theo **điểm phần trăm**. Đây là gợi ý, chưa tự đổi kế hoạch hoặc giữ chỗ. |
| **Giả định của gợi ý** | Muốn hiểu điều kiện của phép ước tính lệch giờ. | Mở để xem trước khi dùng số liệu trình bày. |

Nếu hiện **“Giữ giờ khởi hành hiện tại…”**, lần đánh giá đó chưa có gợi ý lệch giờ phù hợp; không phải nút bấm bị hỏng. Gợi ý lệch giờ không bắt buộc xuất hiện ở mọi hành trình.

### 2.8. Bản đồ Driver

| Ký hiệu/lớp | Ý nghĩa |
| --- | --- |
| **A — Điểm đi** | Vị trí xuất phát đã chọn. |
| **1 — Trạm chính** | Điểm dừng sạc được ưu tiên. |
| **2 — Trạm dự phòng** | Phương án tiếp theo nếu trạm chính không còn chỗ. |
| **B — Điểm đến** | Đích cuối hành trình. |
| **Tuyến xanh lá** | Điểm đi → trạm chính. |
| **Tuyến xanh dương** | Trạm chính → điểm đến. |
| **Tuyến cam nét đứt** | Nhánh từ trạm chính → trạm dự phòng khi cần. |
| **+/− và thao tác kéo/zoom** | Thay đổi góc nhìn bản đồ, không thay đổi kế hoạch. |
| **Danh sách điểm trên bản đồ** | Mở để đọc tên, vai trò và tọa độ khi cần, kể cả khi nền bản đồ bị lỗi. |
| **Thẻ thông tin trạm / Đóng** | Thẻ hiện sau khi bấm định vị; đóng chỉ ẩn thẻ. Bấm định vị lần nữa để mở lại. |

Tuyến đường chỉ được vẽ khi nhận được hình học đường thực tế từ Goong. Nếu thiếu dữ liệu tuyến, hệ thống báo thiếu, không dùng đường thẳng giả làm đường giao thông. Tuyến đi tiếp không khẳng định bạn đủ pin tới đích nếu chưa sạc hoặc dự báo thời điểm sạc xong. Bản web hiện giúp lập kế hoạch và quan sát tuyến, không phải chức năng dẫn đường GPS từng chặng.

### 2.9. Khi không có kế hoạch

Đọc lý do dưới **“Không có trạm khả thi cho chuyến này”**. Có thể do pin không đủ tới trạm với mức dự phòng, không có trạm phù hợp, hoặc ETA vượt khả năng dự báo.

Kiểm tra lại điểm đi/đến, SOC thực tế, đầu cắm và thông số xe. Không tăng số pin giả chỉ để ép hệ thống đưa ra một kế hoạch khi sử dụng thực tế.

## 3. Operator — Theo dõi và thử điều phối mạng lưới

Operator có ba nhóm công việc:

1. **Thiết lập theo dõi:** chọn điều kiện và phạm vi cho dự báo/bản đồ.
2. **Đánh giá nhu cầu & điều phối:** chạy cùng nhóm xe qua ba chiến lược.
3. **Thử phương án cải thiện:** so sánh trước/sau một thay đổi cụ thể.

### 3.1. Thiết lập theo dõi

| Thành phần | Dùng để làm gì? | Cách thao tác |
| --- | --- | --- |
| **Kịch bản** | Chọn Ngày thường, Lễ 30/4 hoặc Tết cho trang Operator. | Chọn rồi bấm **Áp dụng kịch bản**, hoặc lọc/xem tất cả trạm để tải dự báo tương ứng. |
| **Dữ liệu lúc…** | Mốc trạng thái từ backend, dùng làm điểm bắt đầu dự báo. | Đọc ngày giờ và nguồn; mặc định không cần chỉnh. |
| **Áp dụng kịch bản** | Tải dự báo cho kịch bản và thời điểm đang chọn. | Bấm khi muốn áp dụng/làm mới dự báo. Không tự chạy so sánh chiến lược hoặc what-if. |
| **Thiết lập nâng cao** | Mở tùy chọn xem lịch sử. | Chỉ dùng khi cần đổi mốc thời gian. |
| **Xem dữ liệu tại** | Chọn ngày giờ lịch sử theo giờ Việt Nam. | Chọn mốc cách nhau 5 phút, nằm trong lịch sử backend có thể phục vụ; sau đó bấm áp dụng. Không tự kéo dữ liệu ngoài khoảng hỗ trợ. |
| **Dùng mốc hệ thống** | Bỏ mốc lịch sử chỉnh tay, quay về mốc backend cung cấp. | Bấm trong phần nâng cao; áp dụng lại để xem dự báo cho mốc vừa khôi phục. |
| **Khu vực theo dõi** | Chọn một địa điểm làm tâm quan sát. | Tìm qua Goong hoặc chọn từ Danh mục trạm, xác nhận một gợi ý. |
| **Bán kính theo dõi** | Giới hạn các trạm quanh tâm đã chọn. | Chọn 10, 25, 50 hoặc 100 km rồi bấm **Lọc khu vực**. Đây là khoảng cách địa lý quanh tâm, không phải khoảng cách chạy xe dọc đường. |
| **Lọc khu vực** | Áp dụng tâm và bán kính cho bản đồ/tổng quan khu vực, đồng thời tải dự báo nếu cần. | Phải chọn địa điểm hợp lệ trước. Chỉ đổi bán kính khi chưa có tâm sẽ không đủ điều kiện lọc. |
| **Xem tất cả trạm** | Bỏ bộ lọc địa điểm/bán kính và xem toàn bộ danh mục có dữ liệu. | Bấm để xóa địa điểm đang lọc và đưa phạm vi về toàn mạng. Giữ nguyên kịch bản và thời điểm. |

Hiện danh mục có **14 trạm**. “Tất cả” ở đây không có nghĩa là toàn bộ trạm sạc Việt Nam.

### 3.2. Nhãn “Đã chọn / Đang xem”

- **Đã chọn: Tết…:** đang chọn điều kiện đó, nhưng chưa có dự báo hợp lệ đã tải cho lựa chọn hiện tại; đọc trạng thái bên cạnh.
- **Đang xem: Tết…:** các chỉ số/bản đồ đã có dữ liệu cho lựa chọn đó.
- Nhãn phạm vi cho biết đang xem toàn mạng hay một địa điểm và bán kính cụ thể.
- Đổi kịch bản/thời điểm không có nghĩa tự chạy lại mọi thử nghiệm bên dưới. Kết quả so sánh có nhãn cấu hình riêng; bấm chạy lại để có kết quả cho lựa chọn mới.

### 3.3. Ba ô tổng quan khu vực

| Ô chỉ số | Ý nghĩa |
| --- | --- |
| **Trạm trong khu vực — ví dụ 3/14** | Có 3 trạm trong phạm vi đang lọc, trên tổng danh mục 14 trạm. Không phải có 3 cổng trống. |
| **Trạm có nguy cơ hết chỗ — ví dụ 2 trạm** | Đếm các trạm có dự báo mà nguy cơ hết chỗ **từ 66% trở lên**, ở thời điểm **30 phút sau mốc dữ liệu**. |
| **Khả năng còn chỗ trung bình — ví dụ 40%** | Trung bình xác suất còn cổng của những trạm có dự báo trong phạm vi. Không phải tỷ lệ cổng vật lý đang trống và không phải xác suất thành công của cả hành trình. |

**Cách xác định** giải thích ngưỡng cảnh báo và ý nghĩa số 0. Ngưỡng 66% là lựa chọn của nhóm cho cảnh báo, chưa phải tiêu chuẩn được kiểm chứng vận hành thực tế.

Ví dụ: một trạm có khả năng còn chỗ 20% → nguy cơ hết chỗ 80% → được đếm vào ô cảnh báo.

**Vì sao thay địa điểm vẫn thấy 0?**

Số 0 chỉ nói chưa trạm nào trong phạm vi vượt ngưỡng 66%. Các địa điểm khác nhau có thể đều bằng 0. Hãy đối chiếu cả số trạm trong khu vực, xác suất trung bình và nhãn kịch bản. Chọn Tết bên Driver không tự đổi Operator.

**Vì sao bấm “Xem tất cả trạm” mà kết quả nhìn giống trước?**

Nếu bộ lọc trước đã bao trùm cả danh mục, phạm vi mới không khác. Hoặc số trạm cảnh báo vẫn bằng 0 dù phạm vi đã mở rộng. Kiểm tra ô đầu có về 14/14 và nhãn phạm vi có về **Toàn bộ mạng lưới** không. Nút này không xóa hoặc chạy lại bảng so sánh/what-if.

### 3.4. Các trạng thái của chỉ số

| Trạng thái | Cần làm gì? |
| --- | --- |
| **Chưa tải dự báo** | Chọn kịch bản rồi áp dụng, hoặc chọn phạm vi và bấm lọc/xem tất cả trạm. |
| **Đang tải…** | Chờ yêu cầu hoàn tất. Bấm lọc liên tục không tạo dữ liệu mới cho cùng mốc/kịch bản. |
| **Chưa có dữ liệu** | Phạm vi không có dự báo phù hợp; thử kiểm tra địa điểm, mở rộng bán kính hoặc chọn mốc có dữ liệu. Không đọc như số 0. |
| **Không tải được** | Đọc lỗi và bấm **Thử lại** trong khối bản đồ. Nếu dữ liệu backend chưa sẵn sàng, kiểm tra kết nối trước. |

### 3.5. Bản đồ khả năng phục vụ

Bản đồ hiển thị nguy cơ không còn cổng sau 30 phút kể từ mốc dữ liệu:

| Màu | Ngưỡng nguy cơ | Cách đọc |
| --- | --- | --- |
| Xanh | Dưới 33% | Nguy cơ thấp hơn theo dự báo. |
| Vàng/cam | Từ 33% đến dưới 66% | Nguy cơ trung bình. |
| Đỏ | Từ 66% trở lên | Nguy cơ cao, được tính vào ô cảnh báo. |

Màu không biểu thị số xe đang xếp hàng. Đây là lớp dự báo từ lịch sử mô phỏng, không phải bản đồ trạng thái trực tiếp.

- Bộ lọc khu vực thay đổi những trạm xuất hiện trên bản đồ và ba ô tổng quan.
- Mở **Danh sách điểm trên bản đồ** để đọc tên và mức áp lực khi cần.
- Marker khu vực chỉ là tâm bạn đã chọn, không phải một trạm sạc mới.

### 3.6. Đánh giá nhu cầu & điều phối

Khối này trả lời: **với cùng một nhóm xe, cách chọn trạm nào phục vụ tốt hơn?**

1. Kiểm tra kịch bản đang chọn ở đầu trang.
2. Nhập **Số xe**, ví dụ 100.
3. Có thể giữ nguyên **Thiết lập lần chạy**.
4. Bấm **So sánh 3 chiến lược**.
5. Đọc biểu đồ, bảng số liệu và cấu hình ghi trên kết quả.

| Thành phần | Ý nghĩa |
| --- | --- |
| **Số xe** | Số xe trong lượt mô phỏng, không phải số xe thực đang chạy ngoài đường. Nhập số nguyên dương. |
| **Thiết lập lần chạy** | Phần nâng cao chứa mã tạo nhóm xe. |
| **Mã lần chạy** | Seed của bộ mô phỏng. Giữ mã và cấu hình để đối chiếu cùng nhóm xe; đổi mã để thử nhóm xe khác. Nhập số nguyên không âm; 0 hợp lệ. |
| **So sánh 3 chiến lược** | Chạy ba phương thức dưới đây trên cùng nhóm xe và điều kiện nền. |

| Chiến lược | Cách chọn trạm |
| --- | --- |
| **Gần nhất** | Ưu tiên trạm gần theo quy tắc của bộ mô phỏng. |
| **Đang trống** | Dựa vào tình trạng còn chỗ tại lúc lựa chọn. Không dự báo khả dụng tại lúc đến như AI. |
| **Phân bổ AI** | Sử dụng dự báo tại ETA và phân bổ nhu cầu giữa các trạm. |

So sánh sử dụng **toàn bộ 14 trạm**, không chỉ các trạm còn lại sau bộ lọc bán kính. Các xe trong lượt mô phỏng có lịch di chuyển riêng; không đọc số liệu như thể tất cả cùng xuất phát tại đúng mốc dự báo 30 phút trên bản đồ.

### 3.7. Đọc kết quả so sánh chiến lược

| Chỉ số | Cách hiểu |
| --- | --- |
| **Tỷ lệ thành công / Có cổng ngay khi đến** | Số xe có cổng ngay khi đến chia tổng số xe. Xe phải chờ rồi mới được phục vụ không được tính vào tỷ lệ có cổng ngay này. |
| **Thời gian chờ trung bình** | Trung bình trên các xe đã đến trạm; xe bỏ chờ vẫn được tính phần thời gian đã chịu chờ theo quy tắc mô phỏng. |
| **Quãng đường đi thêm / Đường vòng** | Trung bình quãng đường vòng của các xe đã được phân trạm. |
| **Xe chưa được phục vụ** | Xe không có kế hoạch khả thi, bỏ cuộc sau giới hạn chờ hoặc không đến trong cửa sổ mô phỏng. |
| **Điểm %** | Chênh lệch hai tỷ lệ. Ví dụ 63% → 73% là tăng **10 điểm phần trăm**, không phải tăng 10% tương đối. |
| **Phiên bản model/fixture** | Giúp đối chiếu nguồn và tái lập phép thử. |

Số xe không có cổng ngay **không nhất thiết bằng** số xe chưa được phục vụ: một số xe vẫn được sạc sau khi chờ. AI có thể tốt hơn, bằng hoặc kém hơn baseline; không mặc định AI luôn thắng. Nếu một chiến lược lỗi, đọc trạng thái lỗi của lượt đó, không thay bằng số liệu giả.

### 3.8. Thử phương án cải thiện — What-if

Khối này trả lời: **nếu thay đổi hạ tầng hoặc giờ xuất phát, kết quả sẽ khác thế nào?**

Hai lựa chọn hiện có:

| Phương án | Thay đổi được thử |
| --- | --- |
| **Bổ sung cổng sạc** | Thêm 2 cổng tại trạm bạn chọn. |
| **Chuyển xe sang giờ thấp điểm** | Dời 20% nhóm xe sang 21:00–21:55, giữ nguyên tổng số xe. |

Cách dùng:

1. Chọn kịch bản ở đầu trang và số xe/mã lần chạy trong khối điều phối.
2. Chọn một phương án thay đổi.
3. Với bổ sung cổng, chọn **Trạm cần bổ sung cổng**.
4. Chọn **Phương thức điều phối** cho cả hai lượt thử.
5. Bấm **So sánh trước / sau**.
6. Đọc tỷ lệ có cổng ngay khi đến, thời gian chờ và bản đồ thay đổi.

What-if dùng số xe và mã lần chạy hiện đang nhập. Không bắt buộc chạy ba chiến lược trước khi chạy what-if. Với chuyển 20% xe, cần ít nhất 5 xe để thực sự dịch được một xe. Hai lượt trước/sau giữ cùng nhóm xe và điều kiện nền để đối chiếu.

### 3.9. Bản đồ trước/sau của what-if

| Thành phần | Ý nghĩa và thao tác |
| --- | --- |
| **Thay đổi ở đâu trên mạng lưới?** | Chỉ ra vị trí trạm được thêm cổng hoặc mô tả nhóm xe đổi giờ trên mạng lưới. |
| **Trước thay đổi** | Bấm để xem cấu hình cổng ban đầu và chỉ số toàn mạng của lượt trước. |
| **Sau thay đổi** | Bấm để xem cấu hình sau thay đổi và chỉ số toàn mạng của lượt sau. |
| **Trạm tím / nhãn +2** | Nơi đang thử thêm cổng. Ví dụ trước có 4 cổng, sau có 6 cổng. |
| **Trạm xám** | Vị trí các trạm khác. Không có nghĩa các trạm này hết chỗ hay không được phục vụ. |
| **Dòng tỷ lệ và thời gian chờ** | Chỉ số của **toàn mạng**, không phải chỉ số riêng của trạm đang tô tím. |

**Màu trong bản đồ what-if khác ý nghĩa với bản đồ áp lực phía trên.** Màu tím đánh dấu nơi thay đổi cấu hình; không phải mức nguy cơ. API hiện chưa có kết quả phục vụ/chờ riêng từng trạm để tô màu cải thiện theo trạm.

Với chuyển giờ, vị trí trạm trước/sau có thể giống nhau vì thay đổi nằm ở giờ xuất phát của xe. Đọc số xe được dịch và chỉ số mạng lưới, không chờ xuất hiện một trạm mới.

### 3.10. Các mục chi tiết what-if

- **Xem đầy đủ chỉ số so sánh:** bảng trước, sau và chênh lệch tỷ lệ phục vụ ngay, chờ, đường vòng, xe chưa phục vụ.
- **Cách so sánh & nguồn dữ liệu:** các điều kiện giữ cố định và giới hạn của phép thử.
- **Thông tin kiểm chứng phép thử:** model, fixture, cấu hình trước/sau và các giả định.
- **Đã dùng mô hình riêng phù hợp với số cổng mới:** lần chạy có model capacity được huấn luyện riêng; kết quả phản ánh thay đổi cả hạ tầng và model.
- Nếu giao diện ghi model giữ cấu hình ban đầu, số cổng mới chỉ áp dụng theo phạm vi bộ mô phỏng/cách chọn trạm đã công bố; không trình bày như đã huấn luyện lại.

Đổi tham số what-if sẽ ẩn kết quả không còn tương ứng. Bấm chạy lại để có kết quả cho lựa chọn mới. Chức năng này không thực sự xây thêm cổng, đổi lịch xe ngoài đời hay sửa hạ tầng vận hành.

## 4. Phân biệt phạm vi và các nút dễ nhầm

| Thao tác | Thay đổi gì? | Không tự làm gì? |
| --- | --- | --- |
| Driver: **Tìm kế hoạch sạc** | Tạo kế hoạch cho một xe/hành trình và tải tuyến tham khảo. | Không đặt chỗ vật lý, không thanh toán hay kích hoạt sạc. |
| **Định vị trạm chính/dự phòng** | Đổi góc nhìn và thẻ thông tin bản đồ. | Không chọn lại trạm, không ghi thêm phân bổ. |
| Operator: **Áp dụng kịch bản** | Tải dự báo theo kịch bản/thời điểm cho lớp bản đồ. | Không chạy lại bảng chiến lược hoặc what-if. |
| **Lọc khu vực** | Đổi phạm vi bản đồ áp lực và các ô tổng quan. | Không thu hẹp nhóm trạm của simulator/what-if. |
| **Xem tất cả trạm** | Bỏ lọc địa điểm/bán kính, trở về danh mục toàn mạng. | Không đổi kịch bản và không đặt lại các phép thử. |
| **So sánh 3 chiến lược** | Chạy ba lượt mô phỏng cùng nhóm xe. | Không tạo đặt chỗ cho người lái. |
| **So sánh trước / sau** | Chạy hai lượt cho một thay đổi giả định. | Không thay đổi hạ tầng ngoài thực tế. |
| **Tải lại bản đồ** | Khởi tạo lại phần hiển thị bản đồ sau lỗi. | Không tự tạo lại khuyến nghị hoặc chạy lại mô phỏng. |
| **Đặt lại phiên** | Đặt lại tải phân bổ ảo và màn hình hiện tại sau xác nhận thành công từ backend. | Không xóa lịch sử/model hoặc biến dữ liệu mô phỏng thành dữ liệu thật. |

## 5. Lỗi thường gặp và cách xử lý

| Hiện tượng | Kiểm tra/thao tác |
| --- | --- |
| Nút tìm kế hoạch bị mờ | Chờ runtime; chọn rõ hai địa điểm khác nhau; kiểm tra SOC, đầu cắm, dung lượng và mức tiêu hao hợp lệ. |
| Không gập được Thông số xe | Đang có thông số không hợp lệ; sửa số trước khi đóng. |
| Gõ đúng tên nhưng chưa tìm được | Chọn một gợi ý để xác nhận tọa độ; chỉ nhập chữ chưa đủ. |
| Không lấy được mốc dữ liệu/backend | Driver có nút **Thử kết nối lại**; kiểm tra backend đang chạy đúng cấu hình. Operator kiểm tra kết nối và tải lại trang nếu chưa lấy được runtime. |
| Lọc khu vực bị mờ | Phải chọn một địa điểm làm tâm và chờ mốc dữ liệu hợp lệ. Chọn bán kính đơn lẻ chưa đủ. |
| Mọi khu vực đều có 0 trạm cảnh báo | Kiểm tra kịch bản của chính Operator, mốc thời gian và số trạm trong phạm vi; 0 có thể là kết quả hợp lệ. |
| Địa điểm không có trạm | Hệ thống chưa có dữ liệu trạm ở đó; mở rộng phạm vi hoặc chọn trạm trong danh mục. Không đồng nghĩa bản đồ địa lý bị hỏng. |
| Bản đồ trắng/quá thời gian chờ | Bấm **Tải lại bản đồ**. Nếu vẫn lỗi, kiểm tra mạng/cấu hình dịch vụ. Dùng danh sách điểm để tiếp tục đọc kế hoạch; không cần bấm tìm lại liên tục. |
| Có điểm nhưng thiếu đường đi | Đọc thông báo tuyến chưa tải đủ. Không suy ra điểm được nối bằng đường thẳng là đường có thể lái xe. |
| Bảng so sánh chưa có kết quả | Bấm **So sánh 3 chiến lược**; chỉ áp dụng kịch bản chưa chạy simulator. |
| Đổi bán kính nhưng bảng chiến lược giống trước | Bảng dùng toàn mạng và chỉ chạy lại khi bấm nút so sánh; bộ lọc khu vực không thay đổi phép thử đó. |
| What-if chưa chạy được | Kiểm tra số xe/mã lần chạy, danh mục trạm, và ít nhất 5 xe với chuyển giờ. Đọc lỗi nếu backend không hỗ trợ cấu hình thử. |
| Kết quả mô phỏng khác giữa các lượt | Đối chiếu kịch bản, seed, số xe, chiến lược, model và cấu hình trước/sau; chỉ so sánh như cùng một phép thử khi các điều kiện tương ứng được giữ cố định. |

## 6. Một lượt trình bày sản phẩm gợi ý

1. **Driver:** chọn hành trình trong phạm vi dữ liệu, SOC 20%, đầu cắm CCS2 và thông số xe phù hợp; tìm kế hoạch.
2. Chỉ trạm chính, xác suất tại ETA và pin khi đến; mở trạm dự phòng để giải thích phương án B.
3. Trên bản đồ, chỉ các tuyến xanh lá/xanh dương/cam; bấm định vị từng trạm.
4. **Operator:** chọn lại Tết tại chính trang này, áp dụng và xem tất cả trạm.
5. Đổi sang một địa điểm/bán kính; giải thích phạm vi chỉ số đã thay đổi.
6. Với 100 xe, seed 42, chạy so sánh ba chiến lược; đọc số liệu thực trả về, không hứa AI luôn thắng.
7. Thử thêm 2 cổng ở một trạm, chọn chiến lược rồi chạy trước/sau; chuyển hai chế độ bản đồ để chỉ vị trí thay đổi.
8. Nếu cần, thử chuyển 20% xe sang 21h để so sánh phương án thay đổi nhu cầu với phương án tăng hạ tầng.
9. Kết thúc bằng giới hạn nguồn **simulated**, chưa có đặt chỗ vật lý và cần kiểm chứng ngoài thực tế khi có dữ liệu đối tác.

## 7. Thuật ngữ ngắn

| Từ | Nghĩa trong sản phẩm |
| --- | --- |
| **SOC** | Phần trăm pin đang còn. |
| **ETA** | Thời điểm dự kiến đến trạm/điểm đang xét. |
| **Cổng sạc** | Vị trí/cổng cho một xe kết nối để sạc; một trạm có thể có nhiều cổng. |
| **Scenario / Kịch bản** | Bộ điều kiện nhu cầu mô phỏng, không phải dữ liệu lễ thực tế được khẳng định đã thu thập. |
| **Seed / Mã lần chạy** | Mã giúp tạo và đối chiếu cùng nhóm sự kiện/xe dưới cùng cấu hình. |
| **Calibrator** | Bước hiệu chỉnh đầu ra model thành xác suất phù hợp hơn với dữ liệu đánh giá. Không đảm bảo xác suất đúng tuyệt đối ngoài thực tế. |
| **SHAP** | Cách giải thích đóng góp của đặc trưng vào điểm model, không phải chứng minh quan hệ nhân quả. |
| **What-if** | Thử thay đổi giả định để so sánh trước/sau. |
| **Mock / Simulated / Real** | Minh họa / mô phỏng / dữ liệu thật đã xác lập nguồn. Không đánh đồng ba loại này. |

---

Đối chiếu với giao diện hiện tại ngày 16/10/2026. Hướng dẫn kỹ thuật và bằng chứng bản đồ: [Map completion](runbooks/map-completion.md). Khởi chạy runtime và giới hạn tích hợp: [Runtime completion](runbooks/runtime-completion.md).
