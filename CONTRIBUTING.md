# Làm việc chung

- `main` là bản tích hợp; mỗi người tạo nhánh: A `feat/data-simulator`, B `feat/ml-predict`, C `feat/recommend-api`, D `feat/web-map`.
- Task ghi owner, đầu ra, dependency và tiêu chí done; PR nhỏ có thay đổi, cách chạy/kiểm tra, giới hạn. Gộp cuối ngày khi demo chung chạy.
- A↔B review dữ liệu/nhãn/evaluation; C↔D review contract/UI. C làm integrator, cả nhóm hỗ trợ sửa lỗi.
- Thay contract cập nhật `docs/DATA_CONTRACT.md`, `docs/API_CONTRACT.md` và thông báo trước khi sửa consumer; `schemas.py` tạo khi bắt đầu code theo cùng tên field.
- Họp 15 phút mỗi sáng, chốt tính năng tối 14/10. Ý tưởng mới chuyển backlog.
- Không commit `.env`, key, cache thật, model binary/lịch sử sinh lớn; dữ liệu đối tác cần rõ quyền dùng. Chỉ đưa sample nhỏ có nguồn và nhãn giả định.
- Chọn runtime/dependency versions thống nhất, thêm lockfile khi code được khởi tạo. Commit đầu chưa có code nên chưa có lệnh test ứng dụng.
- Khi hoàn thành, cập nhật README module bằng lệnh thực đã chạy; không ghi TODO là chức năng đã hoàn thành.
