# Làm việc chung

- `main` là bản tích hợp. Chỉ tạo bốn nhánh sau khi Phase 0 Foundation đã xanh và merge: Bảo `feat/data-simulator`, Thắng `feat/ml-predict`, Kiên `feat/recommend-api`, Tú `feat/web-map`.
- Task ghi owner, đầu ra, dependency và tiêu chí done; PR nhỏ có thay đổi, cách chạy/kiểm tra, giới hạn. Gộp cuối ngày khi demo chung chạy.
- A↔B review dữ liệu/nhãn/evaluation; C↔D review contract/UI. C làm integrator, cả nhóm hỗ trợ sửa lỗi.
- Thay contract phải qua PR riêng, cập nhật `app/backend/contracts`, OpenAPI sinh tự động, examples/tests, `docs/DATA_CONTRACT.md`, `docs/API_CONTRACT.md` và thông báo trước khi sửa consumer.
- Họp 15 phút mỗi sáng, chốt tính năng tối 14/10. Ý tưởng mới chuyển backlog.
- Không commit `.env`, key, cache thật, model binary/lịch sử sinh lớn; dữ liệu đối tác cần rõ quyền dùng. Chỉ đưa sample nhỏ có nguồn và nhãn giả định.
- Phase 0 chọn runtime/dependency versions, tạo lockfiles và lệnh chuẩn trước khi tách nhánh. Hiện repo vẫn chưa có code hoặc lệnh test ứng dụng.
- Mỗi agent đọc `app/SPEC.md` và `SPEC.md` gần module nhất. Khi hoàn thành, cập nhật tài liệu module bằng lệnh thực đã chạy; không ghi việc dự kiến như chức năng đã hoàn thành.
