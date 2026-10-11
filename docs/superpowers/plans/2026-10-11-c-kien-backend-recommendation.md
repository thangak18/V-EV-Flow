# C/Kiên Backend Recommendation Implementation Plan

> **For agentic workers:** Use the repository-owned [harness workflow](../../harness/workflow.md), applicable AGENTS/SPEC and assigned issue AC. Track task checkboxes as implementation notes; no external skill/plugin is required. Evidence and handoff follow the common workflow.

**Goal:** Replace Phase 0 fakes with file/Goong adapters, feasible recommendation and backup selection, virtual-load allocation, and integrated FastAPI endpoints.

**Architecture:** Recommendation is pure application logic over injected `StationRepository`, `StatusRepository`, `RouteProvider`, `Predictor`, allocation store, and settings. Infrastructure owns file/provider/state adapters. FastAPI remains thin and the composition root is the only code that selects implementations.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2 contracts, httpx, pandas/pyarrow, asyncio locks, pytest.

**Spec:** `app/backend/modules/recommendation/SPEC.md`, `app/backend/infrastructure/SPEC.md`, `app/backend/api/SPEC.md`, and `docs/API_CONTRACT.md`

## Global Constraints

- Start `feat/recommend-api` from the green Phase 0 merge SHA.
- Edit only recommendation, infrastructure, API, their tests/docs, and bounded route cache output.
- Do not edit station data, simulation, prediction, frontend, shared contracts, OpenAPI, or root tooling in this feature PR.
- Consume Bảo's `SimulationRunner` and Thắng's `Predictor` only through public exports; keep Phase 0 fakes until integration.
- Filter compatibility/SOC before ranking; never present ranking score as probability.
- Backup is evaluated on origin → primary → backup and must be reachable without charging at primary.
- Retry with same `request_id`/payload is idempotent; conflicting reuse returns 409.
- Every task uses red-green-refactor and a focused commit.

## File Map

```text
app/backend/infrastructure/repositories/files.py     JSON/Parquet repositories
app/backend/infrastructure/routing/goong.py          RouteProvider implementation
app/backend/infrastructure/routing/cache.py          TTL file cache
app/backend/infrastructure/state/virtual_load.py     Locked idempotent allocation
app/backend/modules/recommendation/soc.py            Energy/SOC feasibility
app/backend/modules/recommendation/ranking.py        Configurable heuristic score
app/backend/modules/recommendation/service.py        Primary/backup orchestration
app/backend/modules/recommendation/allocation.py     AllocationStrategy adapter
app/backend/modules/recommendation/public.py         Stable exports
app/backend/api/dependencies.py                      Concrete composition only
app/backend/api/routes/                              HTTP mapping only
```

---

### Task 1: Add JSON/Parquet Repository Adapters

**Files:**
- Create: `app/backend/infrastructure/repositories/files.py`
- Create: `app/backend/tests/infrastructure/test_file_repositories.py`
- Modify: `app/backend/tests/conformance/repository_contract.py`

**Interfaces:**
- Produces: `FileStationRepository.list_stations() -> tuple[Station, ...]` and `ParquetStatusRepository.window(station_id, observed_at, lags) -> StatusWindow`.

- [ ] **Step 1: Extend the reusable conformance suite with exact behavior**

```python
def test_unknown_station_has_typed_not_found_error(self) -> None:
    repository = self.make_repository()
    with pytest.raises(StationNotFoundError):
        repository.get_station("UNKNOWN")
```

Add stable ordering, source labels, timezone, lag-window, and no-future-row checks.

- [ ] **Step 2: Add failing file adapter tests**

Run the contract suite against temporary JSON/Parquet files and assert invalid capacity/schema fails during adapter construction.

- [ ] **Step 3: Verify failure**

Run: `uv run pytest app/backend/tests/infrastructure/test_file_repositories.py -v`

Expected: FAIL because file adapters do not exist.

- [ ] **Step 4: Implement eager metadata validation and bounded status reads**

Load stations once. For status, filter by station/scenario and `[observed_at - 60m, observed_at]`; do not load future rows or all 180 days into API memory.

- [ ] **Step 5: Run adapter conformance tests**

Run: `uv run pytest app/backend/tests/conformance app/backend/tests/infrastructure/test_file_repositories.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/infrastructure/repositories app/backend/tests/conformance app/backend/tests/infrastructure/test_file_repositories.py
git commit -m "feat(api): add file data repositories"
```

### Task 2: Implement Fake and Goong Route Providers with TTL Cache

**Files:**
- Create: `app/backend/infrastructure/routing/cache.py`
- Create: `app/backend/infrastructure/routing/goong.py`
- Create: `app/backend/tests/infrastructure/test_route_provider.py`
- Create: `app/backend/tests/infrastructure/test_route_cache.py`

**Interfaces:**
- Produces: `RouteCache.get(key, now)`, `RouteCache.put(key, result, collected_at, expires_at)`, and `GoongRouteProvider.get_routes(request) -> tuple[RouteResult, ...]`.

- [ ] **Step 1: Write failing cache tests**

Test key sensitivity to origin/destination/station/time/provider parameters, hit before expiry, miss after expiry, corrupted entry removal, and no API key in cache files.

- [ ] **Step 2: Write failing provider tests with `httpx.MockTransport`**

Cover successful normalization, timeout, provider 4xx/5xx, malformed JSON, empty route, and fallback source note.

- [ ] **Step 3: Verify failure**

Run: `uv run pytest app/backend/tests/infrastructure/test_route_cache.py app/backend/tests/infrastructure/test_route_provider.py -v`

Expected: FAIL because cache/provider do not exist.

- [ ] **Step 4: Implement deterministic cache serialization**

Use SHA-256 of canonical JSON inputs as filename; store route result, collection time, expiry, provider, and request parameters. Write atomically and guard concurrent file writes.

- [ ] **Step 5: Implement bounded Goong calls**

Use an injected `httpx.AsyncClient`, explicit connect/read timeout, configured endpoint/key, and typed `RouteUnavailableError`. Log request IDs and status only; never log the API key.

- [ ] **Step 6: Run tests**

Run: `uv run pytest app/backend/tests/infrastructure/test_route_cache.py app/backend/tests/infrastructure/test_route_provider.py -v`

Expected: PASS without network access.

- [ ] **Step 7: Commit**

```bash
git add app/backend/infrastructure/routing app/backend/tests/infrastructure/test_route_cache.py app/backend/tests/infrastructure/test_route_provider.py
git commit -m "feat(api): add cached route provider"
```

### Task 3: Implement SOC and Compatibility Feasibility

**Files:**
- Create: `app/backend/modules/recommendation/__init__.py`
- Create: `app/backend/modules/recommendation/soc.py`
- Create: `app/backend/modules/recommendation/tests/test_soc.py`

**Interfaces:**
- Produces: `arrival_soc_pct(vehicle, distance_km) -> float` and `filter_feasible(vehicle, candidates, min_soc_pct) -> tuple[FeasibleCandidate, ...]`.

- [ ] **Step 1: Write failing formula and boundary tests**

```python
def test_arrival_soc_formula() -> None:
    vehicle = Vehicle(soc_pct=20, battery_kwh=60,
                      consumption_kwh_per_km=0.18, connector_type="CCS2")
    assert arrival_soc_pct(vehicle, 15) == pytest.approx(15.5)


def test_candidate_at_threshold_is_feasible(candidate, vehicle) -> None:
    assert filter_feasible(vehicle, [candidate.with_arrival_soc(10)], 10)
```

Test incompatible connector, negative distance, zero battery, below threshold, and zero working capacity.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/recommendation/tests/test_soc.py -v`

Expected: FAIL because SOC module does not exist.

- [ ] **Step 3: Implement the documented formula and reasons**

```python
def arrival_soc_pct(vehicle: Vehicle, distance_km: float) -> float:
    if distance_km < 0 or vehicle.battery_kwh <= 0:
        raise ValueError("distance and battery capacity must be valid")
    return vehicle.soc_pct - 100 * distance_km * vehicle.consumption_kwh_per_km / vehicle.battery_kwh
```

Return structured rejection reasons for diagnostics; do not rank rejected candidates.

- [ ] **Step 4: Run tests**

Run: `uv run pytest app/backend/modules/recommendation/tests/test_soc.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/recommendation
git commit -m "feat(recommend): filter stations by SOC and connector"
```

### Task 4: Implement Configurable Ranking Without Probability Mutation

**Files:**
- Create: `app/backend/modules/recommendation/ranking.py`
- Create: `app/backend/modules/recommendation/tests/test_ranking.py`

**Interfaces:**
- Produces: `rank_candidates(candidates, config, virtual_loads) -> tuple[RankedCandidate, ...]` and `RankingConfig`.

- [ ] **Step 1: Write failing ranking tests**

Test higher probability preference, travel-time penalty, SOC-risk penalty, virtual-load penalty, stable station-ID tie-break, configurable weights, and unchanged `p_available`.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/recommendation/tests/test_ranking.py -v`

Expected: FAIL because ranking module does not exist.

- [ ] **Step 3: Implement normalized score**

```python
score = (
    config.weight_probability * candidate.p_available
    - config.weight_travel * normalized_travel_time
    - config.weight_soc_risk * normalized_soc_risk
    - config.weight_virtual_load * normalized_virtual_load
)
```

Normalize with bounded denominators; reject capacity zero before scoring. Store score separately from model probability and record component values for rule reasons.

- [ ] **Step 4: Run tests**

Run: `uv run pytest app/backend/modules/recommendation/tests/test_ranking.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/recommendation/ranking.py app/backend/modules/recommendation/tests/test_ranking.py
git commit -m "feat(recommend): rank feasible stations"
```

### Task 5: Select Primary and Reachable Backup

**Files:**
- Create: `app/backend/modules/recommendation/service.py`
- Create: `app/backend/modules/recommendation/tests/test_service.py`

**Interfaces:**
- Produces: `async RecommendationService.recommend(request: RecommendRequest) -> RecommendResponse` before allocation persistence.

- [ ] **Step 1: Write failing orchestration tests**

Cover no station, one primary/no backup, primary plus reachable backup, backup unreachable from primary, different backup ETA/probability, and independence formula.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/recommendation/tests/test_service.py -v`

Expected: FAIL because service does not exist.

- [ ] **Step 3: Implement injected orchestration**

Load stations, await route requests, filter feasibility, call predictor per candidate ETA, rank, select primary, then await/evaluate primary → remaining station routes using arrival SOC at primary without charging.

- [ ] **Step 4: Compute plan probability explicitly**

For two stations use `1 - (1 - p_primary) * (1 - p_backup)` and set `plan_p_assumption="independent_stations"`; for one station use primary probability; for no primary return null plan and reasons.

- [ ] **Step 5: Run tests**

Run: `uv run pytest app/backend/modules/recommendation/tests/test_service.py -v`

Expected: PASS with only fakes injected.

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/recommendation/service.py app/backend/modules/recommendation/tests/test_service.py
git commit -m "feat(recommend): select primary and backup plans"
```

### Task 6: Add Locked Idempotent Virtual Allocation

**Files:**
- Create: `app/backend/infrastructure/state/virtual_load.py`
- Create: `app/backend/modules/recommendation/allocation.py`
- Create: `app/backend/tests/infrastructure/test_virtual_load.py`
- Create: `app/backend/modules/recommendation/tests/test_allocation.py`

**Interfaces:**
- Produces: async `VirtualLoadStore.reserve(request_id, payload_hash, reservation)`, async `snapshot(at)`, async `reset()`, and pure `RecommendationAllocationStrategy.select(context) -> RankedPlan`.

- [ ] **Step 1: Write failing idempotency/concurrency tests**

Test same ID/same payload returns existing reservation, same ID/different payload raises `RequestConflictError`, primary buckets span ETA to assumed charge end, backup is not reserved, TTL expiry removes load, reset clears state, and concurrent reservations do not lose increments.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/tests/infrastructure/test_virtual_load.py app/backend/modules/recommendation/tests/test_allocation.py -v`

Expected: FAIL because store/allocation adapter do not exist.

- [ ] **Step 3: Implement canonical payload hashing and lock**

Use sorted JSON from the validated request, SHA-256, one `asyncio.Lock`, immutable reservation records, and bucket keys `(station_id, bucket_start)`. Prune expired records inside the lock.

- [ ] **Step 4: Integrate reservation after plan selection**

Reserve only when a primary exists and the request has not already been processed. Preserve raw `p_available`; pass virtual load only to ranking.

- [ ] **Step 5: Run tests**

Run: `uv run pytest app/backend/tests/infrastructure/test_virtual_load.py app/backend/modules/recommendation/tests/test_allocation.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/infrastructure/state app/backend/modules/recommendation/allocation.py app/backend/tests/infrastructure/test_virtual_load.py app/backend/modules/recommendation/tests/test_allocation.py
git commit -m "feat(recommend): add idempotent virtual allocation"
```

### Task 7: Wire Real and Fake Implementations in the Composition Root

**Files:**
- Modify: `app/backend/api/dependencies.py`
- Create: `app/backend/tests/api/test_dependency_selection.py`

**Interfaces:**
- Consumes: Phase 0 fake Predictor/SimulationRunner plus C-owned file repositories, route providers, and recommendation service.
- Produces: application container selected solely from settings, with public injection points that integration can replace with B's Predictor and A's SimulationRunner.

- [ ] **Step 1: Write failing selection tests**

Test `mock/fake/fake`, `file/fake/fake`, and configured `file/fake/goong` combinations with an injected mock HTTP transport. Assert unavailable real/model dependencies fail startup with named errors and no silent fallback; A/B implementations are wired only by the integration plan.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/tests/api/test_dependency_selection.py -v`

Expected: FAIL because composition root still supports Phase 0 mocks only.

- [ ] **Step 3: Implement explicit factories**

Create `_build_station_repository`, `_build_status_repository`, `_build_predictor`, `_build_route_provider`, and `_build_simulation_runner` using selectors already frozen by Phase 0 settings. Predictor and simulation factories retain Phase 0 fakes and explicit not-ready behavior for unavailable real selections. Keep external client lifecycle in FastAPI lifespan and expose narrow factory replacement points for the integration branch.

- [ ] **Step 4: Run selection tests**

Run: `uv run pytest app/backend/tests/api/test_dependency_selection.py -v`

Expected: PASS with fake tests and temp artifacts; no real network call.

- [ ] **Step 5: Commit**

```bash
git add app/backend/api/dependencies.py app/backend/tests/api/test_dependency_selection.py
git commit -m "feat(api): compose replaceable backend adapters"
```

### Task 8: Replace Mock API Behavior and Complete Operator Endpoints

**Files:**
- Modify: `app/backend/api/routes/stations.py`
- Modify: `app/backend/api/routes/prediction.py`
- Modify: `app/backend/api/routes/recommendation.py`
- Modify: `app/backend/api/routes/operator.py`
- Modify: `app/backend/api/errors.py`
- Create: `app/backend/tests/api/test_real_routes.py`

**Interfaces:**
- Produces: contract-compliant `/stations`, `/predict`, `/recommend`, `/pressure`, `/simulate`, `/reset`; `/whatif` remains P1.

- [ ] **Step 1: Write failing integrated route tests with fakes**

Cover successful typed responses, no-plan, unknown station 404, request conflict 409, model/route unavailable 503, default FastAPI 422, reset, retry idempotency, source/version labels, and isolated simulation state.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/tests/api/test_real_routes.py -v`

Expected: FAIL because routes still return Phase 0 fixed data.

- [ ] **Step 3: Delegate routes to injected services**

Handlers contain only validation, dependency acquisition, service call, response model, and typed error mapping. Pressure uses `1 - p_available` with the documented fixed horizon and labels it as a proxy.

- [ ] **Step 4: Connect `/simulate` through the injected runner**

Pass strategy enum and immutable fixtures; do not share Driver virtual-load state. Return actual runner metrics rather than hard-coded comparisons.

- [ ] **Step 5: Regenerate OpenAPI in a separate contract PR if and only if route signatures changed**

For the expected implementation, signatures remain unchanged and `make contract-check` must produce no diff. Any required signature change stops this branch until the contract PR merges and this branch merges the updated `main`.

- [ ] **Step 6: Run API tests and contract check**

Run: `uv run pytest app/backend/tests/api -v && make contract-check`

Expected: PASS and no generated diff.

- [ ] **Step 7: Commit**

```bash
git add app/backend/api app/backend/tests/api
git commit -m "feat(api): integrate recommendation and simulation APIs"
```

### Task 9: Final Backend Handoff and PR Evidence

**Files:**
- Modify: `app/backend/modules/recommendation/SPEC.md`
- Modify: `app/backend/infrastructure/SPEC.md`
- Modify: `app/backend/api/SPEC.md`
- Create: `docs/runbooks/backend-demo.md`

**Interfaces:**
- Produces: verified backend start/reset/demo commands and integration requirements for A/B/D.

- [ ] **Step 1: Add verified runbook commands**

Document mock/file modes, required env keys for Goong/model, curl examples from committed contract examples, reset behavior, one-worker limitation, cache source/TTL, and expected error codes.

- [ ] **Step 2: Run the owner gate**

```bash
uv run pytest app/backend/modules/recommendation app/backend/tests/infrastructure app/backend/tests/api -v
uv run ruff check app/backend/modules/recommendation app/backend/infrastructure app/backend/api
uv run pyright app/backend/modules/recommendation app/backend/infrastructure app/backend/api
make contract-check
make lint
```

Expected: PASS with fake/no-network mode and no generated contract diff.

- [ ] **Step 3: Verify retry/reset manually through TestClient or curl**

Send identical `/recommend` twice and confirm one reservation; send conflicting payload with same ID and confirm 409; call `/reset` and confirm load is empty.

- [ ] **Step 4: Commit and open PR**

```bash
git add app/backend/modules/recommendation/SPEC.md app/backend/infrastructure/SPEC.md app/backend/api/SPEC.md docs/runbooks/backend-demo.md
git commit -m "docs(api): finalize backend integration handoff"
```

PR evidence includes tests, no-contract-diff proof, request/response samples, idempotency/reset proof, Goong failure behavior, cache notes, mock/simulated labels, and limitations.
