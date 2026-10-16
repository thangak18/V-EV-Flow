# Runtime V2: địa chỉ, thời gian, model và trạng thái bền

## Phạm vi đã triển khai

- Goong Places V2 đi qua `/api/places/search` và `/api/places/detail`. REST key ở backend.
  UI debounce 350ms, hủy truy vấn/detail cũ, cho chọn bằng chuột hoặc bàn phím,
  chỉ gửi tọa độ đã resolve. Danh mục trạm là lựa chọn offline có nhãn rõ.
  Địa chỉ toàn quốc không tự tạo thêm trạm hoặc năng lực dự báo ngoài dataset.
- `/api/runtime?scenario=...` trả clock mode, mốc lịch sử, khả năng dữ liệu,
  horizon từ manifest và trạng thái Places. Driver/Operator lấy thời gian này.
  File replay vẫn ghi simulated. `REPLAY_OBSERVED_AT` là tùy chọn +07 căn 5 phút.
  Không dùng giờ máy để giả lập trạng thái hiện tại trên lịch sử cũ.
  Live mode giữ observed_at từ snapshot, còn depart_time là thời điểm bấm tìm
  theo đồng hồ trình duyệt (+07). Thiết bị cần đồng hồ đúng; retry giữ payload gốc.
- File/model adapter cho phép thiếu lag 15/30/60 phút, dùng medians đã fit trên train.
  Snapshot hiện tại vẫn bắt buộc. Không nội suy hay lấy tương lai.
- Model V2 train lại với horizons 15/30/60/90/120/180, embargo 180 phút.
  Model V1 vẫn dùng được và vẫn có horizon 60; runtime đọc capability từng artifact.
- Benchmark chạy nhiều seed, lưu từng fixture/hash và paired delta, không chọn seed thắng.
- SQLite allocation giữ receipts/counters qua restart. `BEGIN IMMEDIATE` bao trọn
  read/decision/commit để nhiều worker trên **một host, cùng file local** không đè nhau.
  Retry cùng request/payload trả cùng receipt, khác payload cùng ID trả 409.
  Hủy/lỗi transaction rollback. Reset và TTL đồng bộ qua database.
- Canonical partner ingestion có bearer token, kiểm tra capacity/connector/clock,
  duplicate keys, không ghi đè snapshot đã tồn tại và không nhận scenario lễ mô phỏng.
  Live context chỉ sẵn sàng khi tất cả trạm có snapshot cùng mốc đủ mới.
  Model trained simulated + status real phải trả mixed, không tuyên bố model đã học dữ liệu thật.
- What-if có thể dùng model riêng đã train lại cho capacity mới khi có variant khớp.
  Response mang cả hai model version và hash lịch sử. Đổi capacity **và** model là
  hai thay đổi, không coi chênh lệch là tác động riêng của số cổng.
  Variant chưa có thì trả chế độ frozen với caveat rõ, không giả vờ đã retrain.

## Chạy bản model mới

Nhận release và capacity ZIP từ owner, kiểm tra CHECKSUMS trước khi load joblib.
Binary/Parquet/SQLite/keys không nằm trong Git.

```bash
make setup
uv run python -m app.backend.api.demo \
  --release-dir /path/simulator-v2-180m \
  --capacity-models-dir /path/capacity-v2 \
  --allocation-db .cache/runtime/allocation.sqlite3 \
  --route-backend goong --port 8000
npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173
```

API Key/REST trong `.env` ở `GOONG_REST_API_KEY`. Maptiles Key riêng ở
`VITE_GOONG_MAP_KEY`. Nếu Places/Directions bị lỗi, UI báo lỗi thay vì bịa tọa độ
hoặc dùng routing giả dưới nhãn thật. Directions có timeout và tối đa một retry
cho network/timeout/HTTP 429 hoặc 5xx, không retry lỗi quyền hay JSON sai.

## Tái lập benchmark và capacity

```bash
uv run python -m app.backend.api.benchmark \
  --release-dir /path/simulator-v2-180m \
  --capacity-models-dir /path/capacity-v2 \
  --seeds 42,43,44,45,46 --vehicles 100 --whatif \
  --output app/backend/modules/simulation/results/benchmark.json

uv run python -m app.backend.api.capacity_artifact \
  --release-dir /path/simulator-v2-180m \
  --station-id S001 --ports 2 --output /new/path/capacity-v2/S001-plus2
```

Output capacity phải là thư mục mới. Cần train variant riêng cho từng thay đổi.
CLI tái mô phỏng lịch sử từ event fixtures nền gốc, dùng cutoff của model cha,
không train trên kết quả foreground 100 xe hoặc tối ưu từ seed demo. Cổng thêm
chưa có fault trace riêng. Không có training job tự chạy trong HTTP request.

## Chuẩn bị nguồn đối tác

Nhóm hiện **chưa có API/histories đối tác**, nên chưa bật live trên bản demo.
Adapter này nhận schema chuẩn của dự án, không phải adapter đã kiểm thử với một
hãng cụ thể. Đối tác phải tự phân loại trạng thái mơ hồ và thống nhất đầu cắm.

1. Chuẩn bị metadata `DATA_DIR/generated/stations.json` đúng Station contract,
   `source` từng trạm khớp `PARTNER_SOURCE`. Model phải hỗ trợ metadata đó.
2. Cấu hình `DATA_BACKEND=real`, `PARTNER_SOURCE`, `PARTNER_HISTORY_PATH` và
   `PARTNER_INGEST_TOKEN` ít nhất 32 ký tự ngẫu nhiên, lưu ngoài Git.
   `SIMULATION_BACKEND=fake` vì runner mô phỏng không tiêu thụ feed thật.
3. Gửi `POST /api/partner/snapshots` với header `Authorization: Bearer ...`
   và body `{"snapshots":[...]}`. Mỗi snapshot có station_id, ts, ports_free,
   ports_busy, ports_broken, n_ports, scenario="normal". Số cổng là số nguyên,
   tổng khớp metadata, thời gian +07 căn 5 phút và không nằm ở tương lai.
4. Gửi lại cùng snapshot được chấp nhận, thay giá trị cùng key trả 409. Cả batch
   commit hoặc rollback cùng nhau. Snapshot khác source/metadata không được trộn DB.
5. `LIVE_MAX_AGE_SECONDS` mặc định 600. Dữ liệu thiếu/cũ chặn dự báo với 503,
   không tự thay bằng lịch sử hoặc fake predictor. Chưa có dữ liệu để đo accuracy thật.

Đặt chỗ cổng vật lý chưa có: receipt chỉ ghi **nhu cầu dự kiến**. Cần API/ủy quyền
đối tác để xác nhận, hủy, hết hạn booking và đối soát. Không thể xác nhận giữ cổng
chỉ bằng cách ghi SQLite ở ứng dụng.

## Docker

```bash
docker compose -p vev-demo -f deploy/compose.yaml up --build -d --wait
```

Mặc định mock/fake, hai Uvicorn workers, Nginx phục vụ web đã build và proxy API,
SQLite/cache trong volume `state`. UI ở `http://127.0.0.1:8080`.
Không đưa REST key/model/data vào image. Với model mode, cấu hình environment
`DATA_BACKEND=file`, `PREDICTOR_BACKEND=model`, `SIMULATION_BACKEND=stateful`,
`RELEASE_DIR=/absolute/release`, `GENERATED_DATA_DIR=/absolute/release/data`,
`CAPACITY_MODELS_DIR=/absolute/capacity-v2`. Goong bật bằng ROUTE_BACKEND,
PLACES_BACKEND và các key local tương ứng. `--env-file /path/private.env` có thể
cấp biến cho Compose. Maptiles Key là build arg công khai cho frontend, REST key
chỉ cấp runtime cho backend.

Không dùng SQLite trên NFS hoặc nhiều host/replica có file riêng. Chưa tạo cloud
account/domain/TLS/user auth; package mặc định chỉ bind localhost. Trước khi mở
Internet cần reverse proxy/TLS và quyền cho người vận hành, đặc biệt endpoint reset.

## Rollback

Quay lại release V1 và `ALLOCATION_BACKEND=memory`, tắt Places/variant nếu cần.
Giữ DB cũ riêng, không xóa lịch sử để rollback source. Optional contract fields
cho capacity retraining chỉ xuất hiện khi có variant, client phải cập nhật cùng
backend trước khi bật mode đó. Không thay binary trong release đang chạy.

## Persistent runtime snapshots

The release launcher copies its process-owned `generated/` snapshots under
`app/backend/modules/prediction/artifacts/runtime/session-*` by default, outside
OS temporary storage. Use `--runtime-dir /path/persistent-runtime` to select a
writable workspace parent. Keep allocation SQLite under a persistent directory
as well. Process-owned snapshot copies are removed on graceful shutdown; the
trusted release stays unchanged. Do not use system `/tmp` for a long-lived
server's history or allocation database. A missing history now returns the typed
unavailable response rather than an unhandled runtime error. The Driver offers
**Thử kết nối lại**, reloading both clock/capabilities and station metadata while
preserving the user's journey and never automatically submitting a plan.
