# Backend demo runbook

## Verified scope

Use `feat/recommend-api`. The backend requires Python 3.11+, `uv`, Node/npm, and ports 8000 (API) and 5173 (Vite). Check `python --version`, `uv --version`, `node --version`, and `npm --version`, then install frozen dependencies with `make setup`.

Mock results are demonstration data, not live charger availability. Generated file data is simulated. No real model or real simulator runner is wired in this revision.

## Configuration

Copy `.env.example` to `.env`; never commit it. `DATA_BACKEND` is `mock` or `file` (`real` is unavailable), `PREDICTOR_BACKEND=fake` is supported (`model` is gated), and `ROUTE_BACKEND` is `fake` or `goong`. `GOONG_REST_API_KEY` is required only for Goong and is server-side only.

`DATA_DIR`, `MODEL_DIR`, `DEMO_SEED`, `MIN_ARRIVAL_SOC_PCT`, `CORS_ORIGINS`, `GOONG_CACHE_DIR`, `GOONG_CACHE_TTL_SECONDS`, `VIRTUAL_LOAD_RECEIPT_TTL_SECONDS`, `ASSUMED_CHARGE_DURATION_MINUTES`, `EXPECTED_VIRTUAL_LOAD`, and `FAKE_PREDICTION_HORIZON_MINUTES` are read by Settings. The fake horizon is a positive five-minute multiple and must be at least 30 minutes for the pressure proxy. Receipt state is process-local.

## Offline mock demo

Set `DATA_BACKEND=mock`, `PREDICTOR_BACKEND=fake`, and `ROUTE_BACKEND=fake`, then run:

```bash
uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
curl -i http://127.0.0.1:8000/api/health
curl -i http://127.0.0.1:8000/api/ready
curl -i http://127.0.0.1:8000/api/stations
curl --get http://127.0.0.1:8000/api/pressure --data-urlencode scenario=normal --data-urlencode time='2026-10-13T16:00:00+07:00'
```

OpenAPI is at `http://127.0.0.1:8000/openapi.json`. Stop with Ctrl-C. Restarting loses allocation state.

## Requests and reset

Prediction timestamps must use +07:00 five-minute buckets, and ETA must be a positive supported five-minute horizon.

```bash
curl -i http://127.0.0.1:8000/api/predict -H 'content-type: application/json' -d '{"station_id":"S001","observed_at":"2026-10-13T16:00:00+07:00","eta":"2026-10-13T16:30:00+07:00","connector_type":"CCS2","scenario":"normal"}'
curl -i http://127.0.0.1:8000/api/recommend -H 'content-type: application/json' -d '{"request_id":"demo-001","origin":{"lat":10.78,"lng":106.70},"destination":{"lat":10.35,"lng":107.08},"observed_at":"2026-10-13T16:00:00+07:00","depart_time":"2026-10-13T16:00:00+07:00","scenario":"normal","vehicle":{"soc_pct":20,"battery_kwh":60,"consumption_kwh_per_km":0.18,"connector_type":"CCS2"}}'
curl -i http://127.0.0.1:8000/api/reset -H 'content-type: application/json' -d '{}'
```

Retry the identical recommendation with the same request ID to replay its receipt; reuse with changed payload returns 409. Reset clears Driver receipts and virtual-load buckets, not files, caches, models, or simulator state. `pressure_score = 1 - p_available` at the fixed 30-minute horizon; it is an availability-risk proxy, not occupancy.

## File, Goong, and deferred modes

File mode requires `DATA_DIR/generated/stations.json` and `DATA_DIR/generated/station_status.parquet` with scenario rows and canonical schema. Missing/corrupt inputs fail without fallback. Goong uses a server-side REST key and `GOONG_CACHE_DIR` with configured TTL (default 3600 seconds); no-route is distinct from provider outage. `PREDICTOR_BACKEND=model` remains gated until trusted artifacts, public Predictor binding, scenario horizons, status windows, and provenance are approved. `/simulate` currently delegates `FakeSimulationRunner`; its mock metrics are not a real AI comparison. Post-C9 integration must provide Bảo's public runner and `availability(station_id, observed_at, eta)` without mixing Driver allocation state into background replay.
