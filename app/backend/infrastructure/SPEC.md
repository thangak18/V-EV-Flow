# Infrastructure Adapters Specification — C/Kiên

## Objective

Implement replaceable adapters for persistence and routing without leaking provider/file formats into domain modules.

## Adapter Set

Phase 0 provides mock repositories backed by small committed JSON fixtures, fake route/predictor/simulation adapters, and an in-memory virtual-load store. Kiên's P0 feature branch extends the data adapters to generated JSON/Parquet files and adds Goong routing with bounded cache. At integration, Thắng's public `Predictor` and Bảo's public `SimulationRunner` replace their fakes through the composition root; those implementations remain owned by their domain modules. A future Tasco/VETC adapter implements existing repository ports rather than changing consumers.

## Dependency Injection

The API composition root selects adapters from validated settings. Tests inject adapters directly. An unavailable selected backend fails startup; fallback must be explicit in the response source notes and logs.

## Conformance and Failure Behavior

All implementations of a port run the same reusable conformance suite. Route calls have timeout, normalized provider errors, deterministic fake responses, cache keys including route-relevant inputs, and recorded collection/expiry times. No adapter logs credentials or commits raw sensitive partner responses.

## Done Criteria

Mock and file adapters return equivalent DTO shapes, switching requires configuration only, provider failures map to typed domain failures, caches are reproducible for the fixed demo route, and integration tests do not require network access.

## Goong No-Route Policy

A successful HTTP response with an explicit empty `routes` list and no error envelope returns `()` through the unchanged RouteProvider port. If a `status` is present it must be `OK`; error fields, unknown/unsuccessful statuses, missing route lists, malformed alternatives/JSON, HTTP errors, timeouts, and connection failures remain `RouteUnavailableError`. This permits recommendation to exclude a missing station/fallback edge without hiding infrastructure failures or enabling fake routing.

No-route results are not cached. The existing nonempty-route cache format, validation, TTL, and atomic writes remain unchanged, so a later request may recover a route. Unknown provider status formats are not guessed to mean no-route and require separately verified adapter support.

## C6 Expected-Demand Store

`state/virtual_load.py` adds an async process-local `VirtualLoadStore` alongside the unchanged Phase 0 `InMemoryAllocationStore` facade. It implements the recommendation consumer's internal read/receipt port, without modifying shared contracts. Scenario-specific five-minute counters, globally conflicting request IDs, defensive JSON receipts and configurable processing-clock TTL are protected by a state lock. Receipt expiry reverses its own primary-only contributions. A separate shared decision lock orders complete Driver decisions and independent reset; always acquire decision before state. See recommendation SPEC for constructor/wiring, validation, retention and one-worker limitations. API dependency selection and reset endpoint integration remain C7–C8, not C6.

## C7/C8 Runtime Wiring

Mock adapters label mock data. File-backed station/status inputs are simulated unless an approved adapter establishes another source. File status repositories are scenario-scoped over the canonical Parquet dataset; missing or corrupt files fail without fallback. Goong uses an app-owned async client, `RouteCache`, configured TTL, and no live network in offline tests; no-route remains distinct from provider outage. One application-scoped `VirtualLoadStore` keeps scenario-isolated five-minute expected primary load and receipts until TTL or reset. It is process-local and supports one worker only.

## C9 Adapter and Operator Handoff

| Settings selection | Actual implementation / availability |
| --- | --- |
| `DATA_BACKEND=mock` | MockStationRepository at `DATA_DIR/fixtures/stations.json`; MockStatusRepository scoped to each Scenario, synthetic all-free counts |
| `DATA_BACKEND=file` | FileStationRepository at `DATA_DIR/generated/stations.json`; one ParquetStatusRepository per Scenario at `DATA_DIR/generated/station_status.parquet` |
| `DATA_BACKEND=real` | StartupConfigurationError; no approved partner adapter |
| `PREDICTOR_BACKEND=fake` | One FakePredictor per Scenario; deterministic 0.75, fake-v1, mock; no Parquet/ML access |
| `PREDICTOR_BACKEND=model` | Gated; missing MODEL_DIR fails Settings, existing directory still fails composition |
| `ROUTE_BACKEND=fake` | Offline FakeRouteProvider: straight-line distance and assumed 40 km/h; source mock |
| `ROUTE_BACKEND=goong` | GoongRouteProvider + RouteCache + async HTTP client; authorized REST key/network required on cache miss |
| Simulation | FakeSimulationRunner + FakeAllocationStrategy, regardless of data mode; real public runner binding is deferred |

The supported offline combinations are mock/fake/fake and file/fake/fake with valid files. Goong routing can replace fake routing with its prerequisites; it does not activate a model or make simulator output measured. No unavailable selection silently falls back. Settings is the only environment reader; consumers receive ports and scenario maps from API composition.

### File bridge, validation and provenance

Run station_data `cli generate --scenario all --seed 42 --history-days 1 --history-end '2026-10-13T23:55:00+07:00' --vehicles 100 --output "$ROOT/generated"`, then simulation `cli history --input "$ROOT/generated"`, using `uv run python -m app.backend.modules.<module>.cli`. `DATA_DIR="$ROOT"` points at their output without copying. The complete executable/schema-check procedure is in the backend demo runbook. Generated bundles and histories are local/ignored, not committed partner data.

Metadata is a nonempty unique-ID Station JSON array, eagerly validated and indexed. Parquet has exactly `station_id, ts, ports_free, ports_busy, ports_broken, scenario`: text IDs/scenarios, aware +07 timestamps, integer nonnegative counts. Each repository scopes reads by scenario/station/time using predicate pushdown; it validates selected rows, unique keys, five-minute alignment and counts summing to station capacity. `window(..., lags=(0,15,30,60))` returns exact requested snapshots or raises DataSourceUnavailableError; no interpolation, extrapolation, implicit lag-0 default or cross-scenario mixing. Construction checks file/schema, not every future window; missing scenarios may be detected on read. C5 currently asks only for lag 0; ML consumers need the full supported history explicitly.

Top-level manifest records seed, data_version, source data_type, generated_at, station count, each scenario's config/counts/fixture_hash and the status file SHA-256/rows after history generation. Fixed seed/options/window reproduce fixture hashes and Parquet rows; manifest timestamps vary. The runbook's smoke uses all three scenario demand profiles on one common calendar day, not actual Tết/holiday measurements. Mock sources are demonstration values; generated status is simulated; real is reserved for explicitly established real provenance; mixed represents combined source types. `/stations` file envelope is simulated, FakePredictor outputs mock, and successful file/fake recommendations combine them as mixed. A real route is not evidence of real charger availability. Source and capacity assumptions remain visible on each Station.

### Routing lifecycle and cache

Goong composition constructs one httpx.AsyncClient if none is injected; `AppContainer.close()` closes only that owned client during application lifespan shutdown. Caller-injected clients remain caller-owned. The adapter uses Directions V2 with car mode; configurable timeout defaults to 10 seconds, connect 2, read/write 5. Missing key is a startup error. Timeout/HTTP/malformed/provider failures become RouteUnavailableError; valid no-route is the existing empty-tuple policy. Real credentialed traffic is separate from offline HTTP-transport conformance tests.

RouteCache defaults to `.cache/goong-routes`, TTL 3600 seconds. Keys hash origin/destination, exact departure timestamp, car mode and schema/provider version. Entries preserve validated alternatives, collection/expiry times and source, use atomic disk writes, bounded cleanup and expiry/invalid-entry misses. Concurrent cache misses for the same key are serialized by adapter locks. Only nonempty successful routes are cached; empty no-route is not. Cache write failure does not discard a successful routing result. Neither cache nor a route source is a live occupancy feed. REST key stays server-side; no cache/credentials are committed. Reset does not delete this cache.

### Allocation storage lifecycle

One VirtualLoadStore per app implements immutable JSON receipts and scenario/station/+07 five-minute expected demand. IDs conflict globally, only primary intervals are reserved, and snapshots are defensive immutable mappings. Default assumption is load 1 and duration 60 minutes (max 24 hours), not a physical port booking. TTL is 1800 processing-clock seconds; reads/writes prune expired receipts and remove their own contributions, independently of charging-duration assumptions. Per-receipt decimal accounting prevents subtractive drift. Reset waits for the shared decision lock then clears all receipts/buckets under the state lock; decision→state is the only nested lock order. Cancellation before commit writes nothing. State is lost on restart and unsupported across multiple workers. The legacy InMemoryAllocationStore remains only for facade compatibility and is also cleared by API reset; HTTP recommendation uses the real coordinator/store.

No Redis, persistent/distributed state, real charger booking or model/simulator API integration is introduced by C9. See `docs/runbooks/backend-verification-evidence.md` for verified combinations, tests and limitations.
