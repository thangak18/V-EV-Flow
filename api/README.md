# Backend — C

FastAPI + Pydantic, `schemas.py` dùng chung ở root khi triển khai, Goong client/cache riêng. Tạo mock theo [API_CONTRACT](../docs/API_CONTRACT.md) ngày đầu; ghép model, SOC/backup, ranking/allocation, pressure và runner A. Một worker và lock cho demo; simulation state riêng. [Kiến trúc](../docs/ARCHITECTURE.md). Chưa có server chạy; bổ sung lệnh setup/start và kiểm tra khi thêm code.
