# Backend demo runbook

Run every command from the repository root. This guide describes the C7/C8
composition on `feat/recommend-api`, not a live charger service. See
[verification evidence](backend-verification-evidence.md) for tested revision,
commands, actual results and remaining handoff gates.

## 1. Prerequisites and frozen setup

- Python 3.11+; CI uses 3.11. `uv` manages `.venv` from committed `uv.lock`.
- Node 22/npm for frontend, generated-type checks and full CI. There is no
  repository-pinned minimum uv version; use an installed uv supporting this lockfile.
- `make`, `curl`, writable temporary/cache directories, free ports 8000 (API)
  and 5173 (frontend/E2E). Chromium is installed by `make setup`; unsupported
  Linux distributions may require Playwright system dependencies.
- First setup/download and security audits need network. After installation,
  mock/fake runtime needs neither network nor a Goong key, generated histories
  or trained artifacts. Real pyarrow remains an installed dependency: file
  adapters are imported by composition even in mock mode; do not stub it.

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
python --version
uv --version
node --version
npm --version
test -f .env || cp .env.example .env
make setup
uv run python --version
uv run python -c 'import pyarrow; print(pyarrow.__version__)'
```

Do not overwrite an existing `.env`, commit it, or print credentials in evidence.
System `python` can differ from `uv run python`; record the latter for tests.
Relative paths are resolved from the current working directory. Stop old API
processes before running CI: E2E needs port 8000.

## 2. Configuration and supported adapter matrix

Settings reads root `.env`; exported environment overrides it. Use these explicit
server environment values for the reproducible examples below:

| Setting | Default / rule |
| --- | --- |
| `DATA_BACKEND` | `mock`; `file` supported, `real` fails startup |
| `PREDICTOR_BACKEND` | `fake`; `model` is not bound in composition |
| `ROUTE_BACKEND` | `fake`; `goong` requires a server-side REST key |
| `DATA_DIR` | `app/backend/modules/station_data`; parent of `fixtures/` or `generated/` |
| `MODEL_DIR` | `app/backend/modules/prediction/artifacts`; existing path alone does not enable model mode |
| `DEMO_SEED` | 42; fixtures and simulation request also have explicit seeds |
| `MIN_ARRIVAL_SOC_PCT` | 10; shared C3/C4 demo threshold, not a safety guarantee |
| `FAKE_PREDICTION_HORIZON_MINUTES` | 60; five-minute multiple, at least 30 for pressure |
| `ASSUMED_CHARGE_DURATION_MINUTES` | 60; positive finite, at most 1440 |
| `EXPECTED_VIRTUAL_LOAD` | 1.0; finite nonnegative compliance/demand assumption |
| `VIRTUAL_LOAD_RECEIPT_TTL_SECONDS` | 1800; positive processing-time retention |
| `GOONG_CACHE_DIR` / `GOONG_CACHE_TTL_SECONDS` | `.cache/goong-routes` / 3600; positive TTL |
| `CORS_ORIGINS` | comma-separated `http://localhost:5173,http://127.0.0.1:5173` |

`DEMO_MODE` is not a current Settings field. Frontend map key
`VITE_GOONG_MAP_KEY` is distinct from backend `GOONG_REST_API_KEY`.

## 3. Start offline mock mode

In terminal A, from the root:

```bash
env DATA_BACKEND=mock PREDICTOR_BACKEND=fake ROUTE_BACKEND=fake \
  DATA_DIR=app/backend/modules/station_data \
  FAKE_PREDICTION_HORIZON_MINUTES=60 MIN_ARRIVAL_SOC_PCT=10 \
  ASSUMED_CHARGE_DURATION_MINUTES=60 EXPECTED_VIRTUAL_LOAD=1 \
  VIRTUAL_LOAD_RECEIPT_TTL_SECONDS=1800 \
  uv run uvicorn app.backend.api.main:create_app --factory \
    --host 127.0.0.1 --port 8000 --workers 1
```

Expect successful startup and Uvicorn listening on 8000. Use **one worker**:
receipts and expected demand are process-local, and multiple workers would
allocate/reset independently. Do not use reload while demonstrating retries.
Ctrl-C stops the server; restart loses Driver state.

In terminal B:

```bash
export API=http://127.0.0.1:8000/api
export DEMO_TMP="$(mktemp -d /tmp/v-ev-backend-demo.XXXXXX)"
curl -i "$API/health"
curl -i "$API/ready"
curl -fsS "$API/stations" > "$DEMO_TMP/stations.json"
uv run python -m json.tool "$DEMO_TMP/stations.json"
curl -fsS http://127.0.0.1:8000/openapi.json > "$DEMO_TMP/openapi.json"
```

Health means the HTTP process responds. Readiness returns the composed adapter
selection and `ready=true`; it is **not** a live Goong/model probe, nor a scan of
every status row. Swagger UI: `http://127.0.0.1:8000/docs`.

Station responses expose IDs, `lat/lng`, `connector_types`, `n_ports`, power,
`source`, `assumptions`, envelope `data_type` and `source_notes`. The verified
fixture contains 14 stations including `S001` with CCS2. Metadata contains
source/assumption labels; mock occupancy and predictions are not live data.

## 4. Prediction, recommendation, pressure and simulation

These timestamps replay a **fixed synthetic time**, October 13, 2026, not the
machine clock. `normal`, `holiday_30_4` and `tet` are scenario labels. Prediction
uses aligned +07:00 observations/ETAs and a positive supported five-minute
horizon. Recommendation departure can be unaligned, but must use +07:00 and
not precede the aligned observation.

```bash
cat > "$DEMO_TMP/predict.json" <<'JSON'
{"station_id":"S001","observed_at":"2026-10-13T16:00:00+07:00","eta":"2026-10-13T16:30:00+07:00","connector_type":"CCS2","scenario":"normal"}
JSON
curl -i "$API/predict" -H 'Content-Type: application/json' \
  --data-binary @"$DEMO_TMP/predict.json"

cat > "$DEMO_TMP/recommend.json" <<'JSON'
{
  "request_id":"demo-001",
  "origin":{"lat":10.78,"lng":106.70},
  "destination":{"lat":10.35,"lng":107.08},
  "observed_at":"2026-10-13T16:00:00+07:00",
  "depart_time":"2026-10-13T16:00:00+07:00",
  "scenario":"normal",
  "vehicle":{"soc_pct":20,"battery_kwh":60,"consumption_kwh_per_km":0.18,"connector_type":"CCS2"}
}
JSON
curl -i "$API/recommend" -H 'Content-Type: application/json' \
  --data-binary @"$DEMO_TMP/recommend.json"
curl --get -i "$API/pressure" --data-urlencode scenario=normal \
  --data-urlencode time='2026-10-13T16:00:00+07:00'

cat > "$DEMO_TMP/simulate.json" <<'JSON'
{"scenario":"tet","seed":42,"vehicle_count":100,"strategy":"ai_allocation"}
JSON
curl -i "$API/simulate" -H 'Content-Type: application/json' \
  --data-binary @"$DEMO_TMP/simulate.json"
curl -i "$API/whatif" -H 'Content-Type: application/json' \
  -d '{"scenario":"tet","seed":42,"vehicle_count":100,"strategy":"ai_allocation","change":{"kind":"add_ports","station_id":"S001","ports":2}}'
```

Interpretation:

- Fake prediction: `p_available=0.75`, `model_version="fake-v1"`,
  `data_type="mock"`, `explanation_method="rule"`; no trained-model inference.
  `/predict` checks station/time/schema and exact membership in the station's
  `connector_types` before inference: an unsupported type returns 422 and an
  unknown station remains 404. A supported but currently occupied connector is
  not rejected merely for occupancy. Fake prediction still does not read status
  history or establish model-level mixed-connector eligibility. C3 separately
  handles recommendation compatibility/capacity/SOC.
- Recommendation performs C3/C4/C5/C6, not a Phase 0 canned plan. Each plan
  includes routed distance/detour, arrival SOC and a conservative **prediction
  bucket ETA**, not an exact physical arrival. Primary/backup may be null.
  Backup is reachable via the primary without charging there; its probability
  is recomputed for that fallback ETA.
- `allocation_method="heuristic_ranking"`; congestion changes score, not
  `p_available`. With both plans, `plan_p=1-(1-p_primary)*(1-p_backup)` and
  `plan_p_assumption="independent_stations"`; correlated outages make this
  assumption imperfect. Primary-only uses its probability; no-plan uses null.
- After reset, verified mock fixture selects S001 at 16:05 and S003 backup at
  16:20 for this payload; both probabilities 0.75, `plan_p=0.9375`. Do not
  guarantee these stations with other sources/settings/load. SOC 0 returns a
  valid HTTP 200 no-plan with reasons; no-plan also has an idempotency receipt.
- Pressure is the fixed **30-minute** `1-p_available` availability-risk proxy,
  not live occupancy, virtual demand or a ranking score. URL-encode `+07:00`.
- `/simulate` currently calls **FakeSimulationRunner** in every supported data
  mode. The example returns `fake-sim-v1`, success 0.9, detour 2.5, wait 4,
  failed 10/100 and a deterministic hash of fake fixture descriptors. It is
  not Bảo's measured simulation or evidence AI beats a baseline. Strategy enum
  values are `nearest`, `currently_available`, `ai_allocation`.
- `/whatif` declares no request body in current OpenAPI; the illustrative P1
  body is ignored. It intentionally returns 503 `FEATURE_NOT_READY`.

## 5. Exact retry, conflict, reset and ID reuse

Run within the 1800-second receipt TTL, using the same server and unchanged
`recommend.json`. This reset also removes any earlier demonstration allocation.

```bash
curl -fsS "$API/reset" -H 'Content-Type: application/json' -d '{}'
curl -fsS "$API/recommend" -H 'Content-Type: application/json' \
  --data-binary @"$DEMO_TMP/recommend.json" > "$DEMO_TMP/first.json"
curl -fsS "$API/recommend" -H 'Content-Type: application/json' \
  --data-binary @"$DEMO_TMP/recommend.json" > "$DEMO_TMP/retry.json"
cmp "$DEMO_TMP/first.json" "$DEMO_TMP/retry.json"
uv run python - "$DEMO_TMP" <<'PY'
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
payload = json.loads((root / "recommend.json").read_text())
payload["scenario"] = "tet"
(root / "conflict.json").write_text(json.dumps(payload))
PY
curl -sS -o "$DEMO_TMP/conflict-response.json" -w '%{http_code}\n' \
  "$API/recommend" -H 'Content-Type: application/json' \
  --data-binary @"$DEMO_TMP/conflict.json"
cat "$DEMO_TMP/conflict-response.json"
curl -fsS "$API/reset" -H 'Content-Type: application/json' -d '{}'
curl -sS -o "$DEMO_TMP/reused.json" -w '%{http_code}\n' \
  "$API/recommend" -H 'Content-Type: application/json' \
  --data-binary @"$DEMO_TMP/conflict.json"
```

Expected: `cmp` exit 0, conflict HTTP 409 `REQUEST_CONFLICT`, reset
`{"reset":true,"contract_version":"0.1.0"}`, reused ID HTTP 200. IDs conflict
globally across scenarios. Do not generate a new request ID for a network retry.
At TTL expiry the original receipt and its contribution are removed; replay is
no longer promised. TTL uses processing time, not the fixed observation.
Retries do not extend TTL; lookup/reserve/snapshot lazily prune expired receipts.
Demand is recorded immediately for future charging buckets, but its retention
is independent of arrival/session time. With default TTL 30 minutes and assumed
charge duration 60 minutes, a plan arriving 40 minutes after commit can lose all
its demand before arrival. This is the consistent short-demo MVP policy, not a
physical booking or a guarantee of long-running balancing. Reset removes every
receipt/contribution regardless of age. Post-C9 work may separate idempotency
retention from demand lifetime; no default or storage semantics changed here.

Response equality alone does not establish correct counters. Run the public
store inspection test (no debug endpoint added):

```bash
uv run pytest app/backend/tests/api/test_real_routes.py \
  -v -k http_retry_conflict_and_reset
uv run pytest app/backend/modules/recommendation/tests/test_allocation.py \
  app/backend/tests/infrastructure/test_virtual_load.py -v
```

The HTTP integration test checks first load 1, retry 1, conflict 1, reset 0,
then one new Tết allocation. C6 tests additionally exercise 50 duplicates,
50 unique IDs, load-aware serialized decisions, expiry, cancellation and reset
races. Only primary is reserved over `[eta, eta + assumed duration)`;
backup is not allocated. Reset clears receipts/buckets and the legacy request
cache, **not** generated data, models, Goong cache, or simulation fixtures.

## 6. Generate and verify file mode

Use real frozen pyarrow. Generate into a separate local root so an existing
dataset and the default-path negative tests remain untouched. No copy/symlink
is necessary: **DATA_DIR is the parent of `generated/`, not `generated/` itself**.

```bash
export FILE_DEMO_ROOT="$(mktemp -d /tmp/v-ev-file-demo.XXXXXX)"
uv run python -m app.backend.modules.station_data.cli generate \
  --scenario all --seed 42 --history-days 1 \
  --history-end '2026-10-13T23:55:00+07:00' --vehicles 100 \
  --output "$FILE_DEMO_ROOT/generated"
uv run python -m app.backend.modules.simulation.cli history \
  --input "$FILE_DEMO_ROOT/generated"
ls "$FILE_DEMO_ROOT/generated"
```

Generation writes `stations.json`, each scenario's `fixture_bundle.json` and
`manifest.json`, plus top-level `manifest.json`. `history` creates
`station_status.parquet` and adds row count/SHA-256 to the top manifest. Seed,
data version, source label, fixture hashes, counts, window config and creation
timestamps are recorded. All three scenarios intentionally replay the same
October 13 calendar window with different demand assumptions; this is not
holiday measurement. One day is enough for this 16:00 demo; omit
`--history-days 1` for the configured 14-day history (larger/slower, not required
for this smoke). Requests must stay in the generated window with required lags.

```bash
GENERATED_DIR="$FILE_DEMO_ROOT/generated" uv run python - <<'PY'
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import pyarrow.parquet as pq
from app.backend.contracts.enums import Scenario
from app.backend.infrastructure.repositories.files import FileStationRepository, ParquetStatusRepository
root = Path(os.environ["GENERATED_DIR"])
manifest = json.loads((root / "manifest.json").read_text())
assert manifest["seed"] == 42 and manifest["data_type"] == "simulated"
assert set(manifest["scenarios"]) == {scenario.value for scenario in Scenario}
path = root / "station_status.parquet"
assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["status_history"]["sha256"]
frame = pq.read_table(path).to_pandas()
assert set(frame.columns) == {"station_id", "ts", "ports_free", "ports_busy", "ports_broken", "scenario"}
assert not frame.duplicated(["scenario", "station_id", "ts"]).any()
stations = FileStationRepository(root / "stations.json")
observed = datetime.fromisoformat("2026-10-13T16:00:00+07:00")
for scenario in Scenario:
    repository = ParquetStatusRepository(path, stations, scenario)
    for station in stations.list_stations():
        window = repository.window(station.station_id, observed, lags=(0, 15, 30, 60))
        assert len(window.statuses) == 4
        assert all(status.scenario == scenario for status in window.statuses)
        assert all(status.ports_free + status.ports_busy + status.ports_broken == station.n_ports
                   for status in window.statuses)
print(pq.read_schema(path))
print(frame.groupby("scenario").size().to_dict())
print(manifest["status_history"])
PY
```

Verified output: 14 stations, 12,096 rows, 4,032 per scenario, timezone-aware
`timestamp[us, tz=+07:00]`, integer counts and text station/scenario columns.
Exact `(0,15,30,60)` snapshots exist for all stations/scenarios at 16:00. The
reader enforces canonical schema, uniqueness, timestamp grid and conservation;
missing required snapshots fail instead of interpolating or mixing scenarios.

For reproducibility, run the same two generation commands into another fresh
output directory and compare scenario `fixture_hash` plus actual Parquet SHA-256
against both manifests. This was executed in the evidence record. Creation
timestamps vary; do not compare manifest bytes. Hashes detect corruption, not
authenticity or accuracy; byte-level Parquet hashes can differ across library
versions, so retain frozen dependencies. Never commit generated histories.

Stop mock API first, then start file API from terminal A with the exported root:

If generation ran in terminal B, run `printf '%s\n' "$FILE_DEMO_ROOT"` there
and set `export FILE_DEMO_ROOT=/the/printed/path` in terminal A. Environment
variables do not transfer between terminals automatically.

```bash
env DATA_BACKEND=file DATA_DIR="$FILE_DEMO_ROOT" \
  PREDICTOR_BACKEND=fake ROUTE_BACKEND=fake \
  FAKE_PREDICTION_HORIZON_MINUTES=60 MIN_ARRIVAL_SOC_PCT=10 \
  ASSUMED_CHARGE_DURATION_MINUTES=60 EXPECTED_VIRTUAL_LOAD=1 \
  VIRTUAL_LOAD_RECEIPT_TTL_SECONDS=1800 \
  uv run uvicorn app.backend.api.main:create_app --factory \
    --host 127.0.0.1 --port 8000 --workers 1
```

Run sections 3–5 HTTP commands again. `/stations` is `simulated`; `/predict`
and `/pressure` remain `mock` because FakePredictor does not read Parquet;
successful recommendation is `mixed` (simulated status/metadata + mock prediction).
No-plan may report `simulated` with `model_version="not_used"`. `/simulate`
remains fake. Missing/corrupt files fail composition/read without mock fallback.
Startup does not validate every row or every scenario timestamp.

Optional **real baseline CLI**, separate from HTTP wiring:

```bash
uv run python -m app.backend.modules.simulation.cli compare \
  --input "$FILE_DEMO_ROOT/generated" --scenario all --vehicles 100 \
  --output "$FILE_DEMO_ROOT/comparison"
```

This runs Bảo's actual `nearest` and `currently_available` baselines and writes
`compare_results.json` with fixture hashes. No AI strategy was injected in this
command. Do not copy its metrics into the fake HTTP response or claim an AI win.

## 7. Goong and model readiness

For Goong, set `ROUTE_BACKEND=goong` and supply an authorized
`GOONG_REST_API_KEY` via local environment or `.env`; never frontend code, Git,
screenshots or logs. Use the same start command with routing changed. Missing
key fails Settings/startup. The app creates one `httpx.AsyncClient` and closes
it through lifespan; caller-injected clients remain caller-owned.

Goong Directions V2 requires network when a cache entry is absent/expired.
HTTPX timeout defaults to 10 seconds (pool), with connect 2 seconds and
read/write 5 seconds; these are phase timeouts, not a total wall-clock budget.
`RouteCache` keys origin/destination, exact departure time,
car mode and schema/provider version; entries record collection/expiry and
source. Cache hits are prior routing results, **not** current charger occupancy
or a guarantee of current ETA. Nonempty routes are cached with TTL (default one
hour); valid empty routes mean no route and are not cached. Outages, malformed
responses and provider error envelopes raise `ROUTE_UNAVAILABLE` (503), not
silent fake fallback. Real routing alone does not make fake predictions real.
Live Goong is **NOT RUN** without an authorized key; adapter/cache failures are
covered offline with HTTP transport fakes.

`PREDICTOR_BACKEND=model` is intentionally unavailable in API composition.
Missing MODEL_DIR fails settings; even an existing directory fails with
`StartupConfigurationError`. It does not enable LightGBM automatically. Later
binding requires Thắng's public Predictor loader, trusted versioned artifacts,
scenario-specific status repositories/provenance, exact current+lag history,
and artifact horizon metadata synchronized with C5/API capabilities. See
prediction `SPEC.md`/`HANDOFF.md`; do not claim this runbook deployed a model.

## 8. Errors and troubleshooting

```bash
curl -i "$API/predict" -H 'Content-Type: application/json' \
  -d '{"station_id":"UNKNOWN","observed_at":"2026-10-13T16:00:00+07:00","eta":"2026-10-13T16:30:00+07:00","connector_type":"CCS2","scenario":"normal"}'
curl -i "$API/predict" -H 'Content-Type: application/json' \
  -d '{"station_id":"S001","observed_at":"2026-10-13T16:00:00+07:00","eta":"2026-10-13T17:05:00+07:00","connector_type":"CCS2","scenario":"normal"}'
curl -i "$API/predict" -H 'Content-Type: application/json' \
  -d '{"station_id":"S001","observed_at":"2026-10-13T16:00:00+07:00","eta":"2026-10-13T16:30:00+07:00","connector_type":"UNSUPPORTED-CONNECTOR","scenario":"normal"}'
curl -i "$API/recommend" -H 'Content-Type: application/json' -d '{}'
```

Expected: 404 `STATION_NOT_FOUND`, 422 unsupported 65-minute horizon with a
60-minute setting, 422 unsupported station connector, 422 missing request fields. Non-+07 offsets, naive times,
unaligned observations/ETAs, negative/out-of-range SOC and invalid enum/schema
also return 422. Semantic validators may return `{"detail":"..."}`; Pydantic
request errors have a `detail` list, not the domain error envelope.

| Symptom | Action / meaning |
| --- | --- |
| 409 `REQUEST_CONFLICT` | Use original payload for retry; new intent gets a new ID, or reset demo |
| 503 `DATA_SOURCE_UNAVAILABLE` | Check generated path/schema, scenario/current snapshot and exact lags; don't substitute mock data |
| 503 `ROUTE_UNAVAILABLE` | Check network/key/provider/cache; no fallback is implicit |
| 503 `MODEL_NOT_READY` | Reserved domain mapping; model selection currently fails startup instead |
| 503 `FEATURE_NOT_READY` | `/whatif` P1 is deliberately unavailable |
| HTTP 200 null plans | Valid no-plan, not an infrastructure outage; read reasons/SOC/horizon |
| Connection refused / port in use | Check process logs, free 8000, use one API instance |
| Parquet import fails | Rerun `uv sync --frozen`/`make setup`; do not use an import stub |
| File API ready but later recommendation fails | Ready is composition-only; inspect requested status window |
| Full CI E2E cannot start | Stop manual API/Vite servers first; check Chromium dependencies |

## 9. Verification and post-C9 handoff

The final offline routing probe observed 38 RouteProvider invocations for the
14-station demo: one direct, 14 origin-to-station, 10 onward and 13
primary-to-backup calls. Warm identical-departure input after store reset still
invoked the provider 38 times but required zero MockTransport fetches; an exact
idempotent retry required zero provider calls. Four distinct concurrent requests
were serialized by C6 and performed 151 provider calls/54 cold-cohort fetches.
These are offline measurements with synthetic transport delay, not live-Goong
latency/quota evidence. See the verification record for timings and methodology.
Keep the decision lock and route/selection semantics; evaluate any route-call
optimization separately with regression coverage. Exact departure timestamps
participate in cache keys, so different departures need not reuse warm entries.

```bash
uv run pytest app/backend/modules/recommendation app/backend/tests/infrastructure app/backend/tests/api -v
uv run ruff check app/backend/modules/recommendation app/backend/infrastructure app/backend/api
uv run pyright app/backend/modules/recommendation app/backend/infrastructure app/backend/api
make backend-lint
make backend-test-suite
make contract-check
make lint
make ci
git diff --check
git status --short
```

Record exact revision, dirty/clean state, environment, exit codes and counts;
see the evidence document for the current execution. Never hand-edit generated
OpenAPI/types or change frozen dependencies to hide a gate failure. Formal
handoff needs fresh `make ci` on the final **clean revision**, independent human
review and integration decision. Local working-tree evidence is not approval.

Post-C9: bind Bảo's public `DefaultSimulationRunner` with validated immutable
fixture bundles, per-strategy fresh state and explicit `availability(station_id,
observed_at, eta)` from Thắng's Predictor. Supply Kiên's pure AllocationStrategy
verified scenario/station/ETA travel/capacity/load metadata, not guessed values.
Choose `strategy_for` per requested enum; missing AI strategy must fail rather
than silently use a baseline. Keep simulation allocation isolated from Driver.
Tú should consume committed generated types, show actual provenance/no-plan and
pressure-proxy labels, preserve IDs only for retries and handle 409/422/503.
No real/model/simulator API binding or what-if implementation is part of C9.
