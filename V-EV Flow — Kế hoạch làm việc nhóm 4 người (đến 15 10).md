# V-EV Flow — Kế hoạch làm việc nhóm 4 người (đến 15/10)

Oct 10, 2026 · @Thang

## Mục tiêu và mốc

Cả nhóm hoàn thành demo V-EV Flow vào tối 15/10; ngày 16/10 chỉ dùng để sửa lỗi nếu BTC cho phép lùi hạn.

- **Tối 10/10:** chốt vai, tạo repo chung, gửi tin cho mentor/BTC.
- **11/10:** chốt hợp đồng dữ liệu và API (mục 4); dữ liệu thô v0 và API giả có trong ngày.
- **12–13/10:** làm phần lõi: simulator, mô hình, API thật, bản đồ.
- **Tối 14/10:** chốt tính năng, chạy thử toàn bộ. Sau đó chỉ sửa lỗi.
- **15/10:** đánh bóng, slide, quay video dự phòng, nộp vào tối.
- **16/10:** dự phòng, không thêm tính năng.
- **17/10:** BTC Tasco tiếp tục phát triển từ sản phẩm này, nên phần chưa kịp đưa vào danh sách việc tiếp theo.

## Phạm vi MVP

Bắt buộc có 5 thứ để demo chạy trọn một hành lang (TP.HCM–Vũng Tàu); các thứ còn lại làm nếu kịp hoặc để lại cho vòng sau.

| Nhóm | Tính năng | Ghi chú |
| --- | --- | --- |
| Bắt buộc | Dự báo xác suất có cổng tại thời điểm xe đến | LightGBM, hiệu chỉnh xác suất |
| Bắt buộc | Gợi ý trạm chính và dự phòng theo mức pin | Loại trạm không đủ pin trước khi xếp hạng |
| Bắt buộc | Phân bổ nhu cầu để xe sau không bị dồn về cùng trạm | Mỗi gợi ý được tính là một xe sắp đến |
| Bắt buộc | Bản đồ Goong với lớp Áp lực sạc, 3 kịch bản | Ngày thường, 30/4, Tết |
| Bắt buộc | So sánh 3 chiến lược với 100 xe | Gần nhất, đang trống, dự báo kèm phân bổ |
| Nên có nếu kịp (đến 14/10) | Gợi ý lệch giờ | Chạy lại mô hình ở giờ khác |
| Nên có nếu kịp (đến 14/10) | What-if: thêm trụ, dịch 20% xe sang giờ lệch | Dùng lại simulator, khoảng nửa ngày |
| Nên có nếu kịp (đến 14/10) | Giải thích ngắn bằng SHAP | Một dòng lý do cho mỗi gợi ý |
| Hoãn | Mức sạc khuyến nghị | Để sang vòng 17/10 |
| Hoãn | Báo cáo cộng đồng | Chỉ nêu trong slide |
| Hoãn | Tích hợp thật vào VETC Trạm sạc, công cụ vận hành đầy đủ | Cần API và thỏa thuận từ Tasco |

## Phân vai

Mỗi người giữ một mảng và khoảng 5 ngày công; ngày công là ước lượng thô, chưa đo thật.

| Vai | Việc chính | Sản phẩm giao | Ngày công |
| --- | --- | --- | --- |
| **A. Dữ liệu và mô phỏng** | Làm sạch dữ liệu trạm của Tasco; simulator đơn giản với 3 kịch bản; bộ chạy 100 xe; what-if. Từ 14/10: slide, kịch bản, quay video | Bảng trạm và dữ liệu v0 (cuối 11/10), simulator v1 (hết 12/10), bộ chạy 100 xe (13/10), slide và video (15/10) | \~5 |
| **B. Mô hình** | Đặc trưng, LightGBM, hiệu chỉnh, SHAP, baselines, metrics, gợi ý lệch giờ, đóng gói mô hình cho API. Sáng 11/10 phụ A dựng khung simulator | Mô hình v1 (hết 12/10), bảng và biểu đồ so sánh 3 chiến lược (hết 14/10) | \~5 |
| **C. Backend** | Gọi Goong (tuyến, ETA, tìm trạm); FastAPI; trạm chính và dự phòng theo pin; phân bổ nhu cầu; tổng hợp dữ liệu cho lớp Áp lực sạc; ghép các phần | API giả (11/10), API thật (hết 13/10) | \~4,75 |
| **D. Giao diện** | Bản đồ Goong, tô màu theo xác suất, bảng kế hoạch có lý do, lớp Áp lực sạc với nút đổi kịch bản, giao diện what-if và lệch giờ, đánh bóng demo | Bản đồ (11/10), đủ màn hình (hết 14/10) | \~5 |

Trưởng nhóm (người đang giữ liên lạc với BTC) lo việc liên lạc Tasco, không gắn với vai nào. A là người đổi nguồn dữ liệu từ simulator sang dữ liệu thật khi Tasco gửi. Ghép vai theo thế mạnh: ai giỏi ML nhận B, ai giỏi web nhận D, ai giỏi hệ thống và API nhận C.

## Hợp đồng chốt ngày 11/10

Chốt ba thứ trong buổi đầu ngày 11/10 (khoảng 1 giờ, cả nhóm) để bốn vai làm song song mà không phải chờ nhau: bảng trạm, bảng trạng thái cổng, và hai API. Thời gian dùng ISO 8601 với múi giờ +07:00.

**Bảng trạm** (`stations`): `station_id`, `name`, `lat`, `lng`, `n_ports`, `power_kw`, `connector_types`, `network`.

**Bảng trạng thái cổng** (`station_status`, mỗi 5 phút): `station_id`, `ts`, `ports_free`, `ports_busy`, `ports_broken`.

**API dự báo** `POST /predict`:

```json
{
  "request": {"station_id": "S012", "eta": "2026-10-13T17:40:00+07:00", "connector_type": "CCS2"},
  "response": {"p_available": 0.85, "reasons": [{"feature": "hour_of_day", "effect": "-"}], "model_version": "v1"}
}
```

**API gợi ý** `POST /recommend`:

```json
{
  "request": {
    "origin": [10.78, 106.70], "destination": [10.35, 107.08],
    "depart_time": "2026-10-13T16:00:00+07:00",
    "vehicle": {"soc_pct": 20, "battery_kwh": 60, "consumption_kwh_per_km": 0.18, "connector_type": "CCS2"}
  },
  "response": {
    "primary": {"station_id": "S012", "eta": "2026-10-13T16:40:00+07:00", "arrival_soc_pct": 16, "p_available": 0.85, "detour_km": 5.0},
    "backup": {"station_id": "S015", "eta": "2026-10-13T16:55:00+07:00", "arrival_soc_pct": 11, "p_available": 0.6, "detour_km": 7.5},
    "plan_p": 0.94,
    "reasons": ["Trạm A gần hơn nhưng dự báo kín chỗ lúc xe đến"],
    "time_shift": null
  }
}
```

`plan_p` = 1 − (1 − pA)(1 − pB), giả định hai trạm độc lập; giả định này phải ghi rõ trên giao diện và slide. Các số trên chỉ là ví dụ định dạng, không phải kết quả đo.

Còn phải chốt: hành lang (TP.HCM–Vũng Tàu trừ khi Tasco nói khác), repo chung, cách chia khóa Goong, mã loại đầu cắm thống nhất.

## Lịch theo ngày

Tính năng chốt cuối ngày 14/10; ngày 15/10 chỉ sửa lỗi, đánh bóng và nộp.

| Ngày | A. Dữ liệu và mô phỏng | B. Mô hình | C. Backend | D. Giao diện |
| --- | --- | --- | --- | --- |
| **11/10 (CN)** | Bảng trạm, khung simulator, dữ liệu v0 cuối ngày | Sáng phụ A dựng khung simulator; chiều dựng pipeline đặc trưng | Gọi Goong, dựng API giả cho /predict và /recommend | Bản đồ Goong với các trạm đọc từ API giả |
| **12/10** | Simulator v1, 3 kịch bản, lịch sử vài tháng | Mô hình v1 và hiệu chỉnh xác suất | Trạm chính, dự phòng, loại trạm không đủ pin | Tô màu theo xác suất, bảng kế hoạch có lý do |
| **13/10** | Bộ chạy 100 xe | SHAP, baselines, gợi ý lệch giờ | Ghép mô hình thật, làm phân bổ nhu cầu | Lớp Áp lực sạc, nút đổi kịch bản |
| **14/10** | What-if; bắt đầu slide. **Tối: chốt tính năng** | So sánh 3 chiến lược, vẽ biểu đồ | Sửa lỗi ghép, lưu tạm kết quả Goong | Giao diện what-if và lệch giờ; chạy thử toàn bộ |
| **15/10** | Slide, kịch bản, quay video dự phòng | Sửa lỗi mô hình, giúp slide | Sửa lỗi | Đánh bóng. **Chiều: chạy thử demo. Tối: nộp** |
| **16/10** | Dự phòng: chỉ sửa lỗi, không thêm tính năng |  |  |  |

## Điểm phụ thuộc

A và B là cặp phụ thuộc nhau nhất, vì mô hình học từ cách simulator tạo dữ liệu; các phụ thuộc khác đều có bản giả để không ai phải dừng.

- **A → B:** dữ liệu v0 cuối 11/10 (có thể thô); sáng 11/10 B phụ A để dữ liệu ra sớm.
- **C → D:** API giả trong ngày 11/10, D làm giao diện trên dữ liệu giả.
- **B → C:** mô hình v1 hết 12/10; trước đó C dùng xác suất giả.
- **A → C, D:** dữ liệu và kịch bản cho lớp Áp lực sạc, có trong ngày 13/10.
- **Tasco → A:** nếu dữ liệu thật đến muộn, A chỉ đổi nguồn trước tối 14/10, sau đó giữ nguyên.

Khi bị nghẽn, báo cả nhóm ngay trong buổi họp sáng và chuyển sang bản giả thay vì chờ.

## Tiêu chí nghiệm thu

Mỗi vai đạt khi sản phẩm của mình chạy được trên đầu vào của vai khác; cả nhóm đạt khi một người ngoài nhóm chạy hết demo mà không cần hướng dẫn.

| Vai | Đạt khi |
| --- | --- |
| **A** | Simulator sinh dữ liệu cho ít nhất 10 trạm với 3 kịch bản (ngày thường, 30/4, Tết), chạy lại được bằng một lệnh; bộ chạy 100 xe cho ra số liệu của cả 3 chiến lược |
| **B** | Chia dữ liệu theo thời gian; có AUC, Brier score, biểu đồ hiệu chỉnh và so với baseline "giữ trạng thái hiện tại"; gọi qua /predict trả xác suất kèm lý do |
| **C** | /recommend trả trạm chính, dự phòng, plan\_p và lý do; loại trạm không đủ pin; phân bổ làm gợi ý cho xe sau đổi; Goong lỗi thì báo rõ, không treo |
| **D** | Chạy trọn luồng: nhập hành trình → bản đồ có kế hoạch → đổi kịch bản → xem what-if; không lỗi trên trình duyệt chính |
| **Demo chung** | Chạy được kịch bản: xe 20% pin, đổi 3 kịch bản, chạy 100 xe; mọi số trên màn hình ghi rõ là mô phỏng; có video dự phòng |

## Rủi ro và thứ tự cắt

Rủi ro lớn nhất là mô hình học từ dữ liệu do chính simulator tạo ra, nên kết quả đẹp không chứng minh độ chính xác ngoài thực tế.

| Rủi ro | Cách xử lý |
| --- | --- |
| Dữ liệu giả lập làm kết quả "quá đẹp" | Ghi rõ trên slide và demo là mô phỏng; thêm nhiễu và sự cố cổng; hiệu chỉnh theo dữ liệu Tasco nếu có; không nêu độ chính xác thực tế |
| A trễ làm B, C, D nghẽn | API giả và dữ liệu thô v0; B phụ A sáng 11/10 |
| Goong hết hạn mức hoặc chậm | Lưu tạm kết quả tuyến và ETA; hỏi Tasco về hạn mức |
| Hai trạm cùng quá tải dịp lễ làm `plan_p` quá lạc quan | Ghi rõ giả định độc lập; cải tiến ở vòng sau khi có dữ liệu |
| Trễ tiến độ chung | Cắt theo thứ tự phía dưới |

**Thứ tự cắt khi trễ:** SHAP, gợi ý lệch giờ, what-if. Không cắt: bản đồ, dự báo tại ETA, trạm dự phòng, lớp Áp lực sạc, so sánh 3 chiến lược.

## Việc cần hỏi Tasco/BTC

Tasco đã nói dữ liệu trạm sạc có thể là dữ liệu thật, còn phần còn lại là dữ liệu giả; các câu dưới đây làm rõ mức đó và việc đổi ý tưởng. Gửi một tin gộp cho mentor/BTC trước tối 11/10; khi nhắn, nói rõ ý tưởng đầu là "Còn lối vào" và nhóm đã đổi sang V-EV Flow sau phản hồi của ban giám khảo.

1. Việc đổi ý tưởng có cần thủ tục hay việc gì không?
2. Sản phẩm nộp ngày 15/10 ở dạng nào (web demo, API hay video)? Hạn có cho lùi sang 16/10 không?
3. Dữ liệu thật ở mức nào: chỉ danh sách trạm, hay có trạng thái cổng theo thời gian, có lịch sử không? Giao bằng file hay API, cứ bao lâu cập nhật một lần, có được hiển thị trên bản đồ demo không?
4. VETC Trạm sạc đã có dự báo khả dụng tại thời điểm xe đến chưa, có API hay tài liệu để tích hợp thử không?
5. Lưu lượng thu phí tổng hợp theo giờ có chia sẻ được không (hiện coi là dữ liệu giả)?
6. Goong: hạn mức credit và việc lưu tạm kết quả có được không?

Nếu chưa có trả lời, cứ làm theo mặc định: simulator cho trạng thái cổng, Goong cho tuyến và ETA, OSM hoặc Goong Places cho vị trí trạm; web demo trên hành lang TP.HCM–Vũng Tàu; nhắm vào chủ xe cá nhân. Khi có dữ liệu thật, A chỉ thay phần đầu vào, không đổi kiến trúc.

## Nguyên tắc làm việc

Năm nguyên tắc giúp nhóm không dừng vì chờ nhau và không đổi hướng giữa chừng.

- **Họp 15 phút mỗi sáng:** mỗi người nói đã xong gì, hôm nay làm gì, đang chờ ai.
- **Một repo chung:** mỗi vai một nhánh, gộp vào nhánh chính cuối mỗi ngày.
- **Đổi hợp đồng API phải báo cả nhóm** trước khi sửa.
- **Chốt tính năng tối 14/10.** Ý tưởng mới sau mốc này ghi vào danh sách việc cho vòng 17/10, không làm ngay.
- **Số liệu minh họa luôn ghi rõ** là mô phỏng trên giao diện, slide và video.
