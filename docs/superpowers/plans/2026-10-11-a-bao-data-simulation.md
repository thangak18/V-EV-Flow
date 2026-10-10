# A/Bảo Data and Simulation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce validated corridor data, deterministic scenarios, a stateful charging simulator, and a fair 100-vehicle comparison runner.

**Architecture:** `station_data` owns validated source-labelled fixtures and deterministic event generation. `simulation` owns a discrete 5-minute engine and accepts an `AllocationStrategy` port; it never imports prediction/recommendation internals. Results implement the shared `SimulationRunner` contract.

**Tech Stack:** Python 3.11, NumPy, pandas, PyYAML, Pydantic contracts, pytest, Parquet/pyarrow.

**Spec:** `app/backend/modules/station_data/SPEC.md`, `app/backend/modules/simulation/SPEC.md`, and `docs/ML_AND_ALLOCATION.md`

## Global Constraints

- Start `feat/data-simulator` from the green Phase 0 merge SHA.
- Edit only `app/backend/modules/station_data`, `app/backend/modules/simulation`, their tests/docs, and ignored generated outputs.
- Do not edit shared contracts, OpenAPI, root tooling, API, prediction, recommendation, or frontend.
- Use the shared DTOs and ports exactly; request a separate contract PR if they are insufficient.
- Same scenario/seed must pre-generate identical vehicles, arrivals, durations, and faults for every strategy.
- Generated history is simulated and must never be labelled real.
- Every task uses red-green-refactor and a focused commit.

## File Map

```text
app/backend/modules/station_data/public.py       Stable loader/generator exports
app/backend/modules/station_data/loaders.py      JSON/YAML loading and validation
app/backend/modules/station_data/generator.py    Deterministic events/vehicles
app/backend/modules/station_data/manifests.py    Data version/provenance manifest
app/backend/modules/station_data/fixtures/       Small committed stations/scenarios
app/backend/modules/station_data/generated/      Ignored generated datasets
app/backend/modules/simulation/domain.py         Engine state and event records
app/backend/modules/simulation/engine.py         Stateful 5-minute transitions
app/backend/modules/simulation/baselines.py      nearest/currently_available strategies
app/backend/modules/simulation/runner.py         Fair multi-strategy evaluation
app/backend/modules/simulation/cli.py            Reproducible commands
app/backend/modules/simulation/public.py         SimulationRunner export
```

---

### Task 1: Validate Station and Scenario Inputs

**Files:**
- Create: `app/backend/modules/station_data/__init__.py`
- Create: `app/backend/modules/station_data/loaders.py`
- Create: `app/backend/modules/station_data/public.py`
- Modify: `app/backend/modules/station_data/fixtures/stations.json`
- Modify: `app/backend/modules/station_data/fixtures/scenarios.yaml`
- Create: `app/backend/modules/station_data/tests/test_loaders.py`

**Interfaces:**
- Produces: `load_stations(path: Path) -> tuple[Station, ...]` and `load_scenarios(path: Path) -> dict[Scenario, ScenarioConfig]`.

- [ ] **Step 1: Write failing loader tests**

```python
def test_load_stations_returns_unique_ids(stations_path: Path) -> None:
    stations = load_stations(stations_path)
    assert 10 <= len(stations) <= 20
    assert len({station.station_id for station in stations}) == len(stations)


def test_all_scenarios_use_five_minute_steps(scenarios_path: Path) -> None:
    scenarios = load_scenarios(scenarios_path)
    assert set(scenarios) == {Scenario.NORMAL, Scenario.HOLIDAY_30_4, Scenario.TET}
    assert all(item.step_minutes == 5 for item in scenarios.values())
```

- [ ] **Step 2: Run and confirm failure**

Run: `uv run pytest app/backend/modules/station_data/tests/test_loaders.py -v`

Expected: FAIL because loaders and full fixtures do not exist.

- [ ] **Step 3: Add 10–20 corridor stations**

Use stable IDs `S001` onward, CCS2, valid coordinates, source per station, and explicit assumptions for synthetic capacity/power. Do not represent assumed capacity as observed data.

- [ ] **Step 4: Implement strict loading**

```python
def load_stations(path: Path) -> tuple[Station, ...]:
    rows = json.loads(path.read_text())
    stations = tuple(Station.model_validate(row) for row in rows)
    if len({item.station_id for item in stations}) != len(stations):
        raise ValueError("station_id values must be unique")
    return stations
```

Validate scenario demand multipliers, duration distribution parameters, outage/repair probabilities, compliance rate, seed, start/end, and step size.

- [ ] **Step 5: Run tests**

Run: `uv run pytest app/backend/modules/station_data/tests/test_loaders.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/station_data
git commit -m "feat(data): validate corridor fixtures"
```

### Task 2: Generate Deterministic Background Events and Vehicles

**Files:**
- Create: `app/backend/modules/station_data/generator.py`
- Create: `app/backend/modules/station_data/manifests.py`
- Modify: `app/backend/modules/station_data/public.py`
- Create: `app/backend/modules/station_data/tests/test_generator.py`

**Interfaces:**
- Produces: `generate_fixture_bundle(config: ScenarioConfig, stations: Sequence[Station], vehicle_count: int) -> FixtureBundle`, `write_fixture_bundle(bundle, output_dir) -> DataManifest`, and `load_fixture_bundle(path: Path) -> FixtureBundle`.

- [ ] **Step 1: Write a failing reproducibility test**

```python
def test_same_seed_produces_identical_fixture_bundle(config, stations) -> None:
    first = generate_fixture_bundle(config, stations, vehicle_count=100)
    second = generate_fixture_bundle(config, stations, vehicle_count=100)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/station_data/tests/test_generator.py -v`

Expected: FAIL because generator does not exist.

- [ ] **Step 3: Implement one RNG and pre-generated events**

```python
def generate_fixture_bundle(config, stations, vehicle_count):
    rng = np.random.default_rng(config.seed)
    vehicles = _generate_vehicles(rng, config, vehicle_count)
    arrivals = _generate_background_arrivals(rng, config, stations)
    durations = _generate_service_durations(rng, len(arrivals))
    faults = _generate_faults_and_repairs(rng, config, stations)
    return FixtureBundle(vehicles=vehicles, background_arrivals=arrivals,
                         service_durations=durations, port_events=faults,
                         scenario=config.scenario, seed=config.seed)
```

Generate each random sequence once and store it in the bundle; strategies never call RNG during comparison.

- [ ] **Step 4: Add manifest hashing and source labels**

Manifest includes SHA-256 of config/fixtures, contract/data version, scenario, seed, counts, generated timestamp, and `data_type="simulated"`.

- [ ] **Step 5: Run generator tests**

Run: `uv run pytest app/backend/modules/station_data/tests/test_generator.py -v`

Expected: PASS for same-seed identity, different-seed difference, counts, bounds, and manifest hash stability.

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/station_data
git commit -m "feat(data): generate deterministic simulation fixtures"
```

### Task 3: Model Stateful Charging, Queue, and Port Events

**Files:**
- Create: `app/backend/modules/simulation/__init__.py`
- Create: `app/backend/modules/simulation/domain.py`
- Create: `app/backend/modules/simulation/engine.py`
- Create: `app/backend/modules/simulation/tests/test_engine.py`

**Interfaces:**
- Produces: `SimulationEngine.step(ts: datetime) -> StepSnapshot` and `SimulationEngine.run() -> tuple[StepSnapshot, ...]`.

- [ ] **Step 1: Write failing state-transition tests**

```python
def test_session_remains_busy_until_service_end(engine) -> None:
    engine.arrive(vehicle_id="V001", station_id="S001", service_minutes=15)
    first = engine.step(T0)
    second = engine.step(T0 + timedelta(minutes=5))
    assert first.station("S001").ports_busy == 1
    assert second.station("S001").ports_busy == 1


def test_waiting_vehicle_enters_when_port_is_released(engine) -> None:
    engine.arrive("V001", "S001", service_minutes=5)
    engine.arrive("V002", "S001", service_minutes=10)
    engine.step(T0)
    snapshot = engine.step(T0 + timedelta(minutes=5))
    assert snapshot.active_vehicle_ids == {"V002"}
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/simulation/tests/test_engine.py -v`

Expected: FAIL because engine does not exist.

- [ ] **Step 3: Implement explicit immutable event records and mutable engine state**

Use dataclasses for `ChargingSession`, `QueuedVehicle`, `PortEvent`, and `StationRuntimeState`. Apply events in fixed order per timestamp: repairs, faults, completions, arrivals, queue admission, snapshot.

- [ ] **Step 4: Preserve capacity invariants**

At every step assert `free + busy + broken == n_ports`, never allow negative counts, and prevent a fault from silently dropping an active vehicle; apply the documented requeue/failure policy.

- [ ] **Step 5: Run engine tests**

Run: `uv run pytest app/backend/modules/simulation/tests/test_engine.py -v`

Expected: PASS for session continuity, FIFO queue, faults/repairs, zero capacity, and port conservation.

- [ ] **Step 6: Commit**

```bash
git add app/backend/modules/simulation
git commit -m "feat(sim): add stateful charging engine"
```

### Task 4: Emit Status History and Inference Windows

**Files:**
- Modify: `app/backend/modules/simulation/engine.py`
- Create: `app/backend/modules/simulation/history.py`
- Modify: `app/backend/modules/simulation/public.py`
- Create: `app/backend/modules/simulation/tests/test_history.py`

**Interfaces:**
- Produces: `generate_status_history(bundle: FixtureBundle, stations: Sequence[Station]) -> pd.DataFrame`, `snapshots_to_frame(snapshots: Sequence[StepSnapshot]) -> pd.DataFrame`, `write_status_history(frame: pd.DataFrame, path: Path) -> Path`, and `build_status_window(frame: pd.DataFrame, station_id: str, observed_at: datetime, lag_minutes: tuple[int, ...] = (15, 30, 60)) -> StatusWindow`.

- [ ] **Step 1: Write failing schema/window tests**

Assert unique `(scenario, station_id, ts)`, exact Parquet columns, timezone preservation, and that a window never contains a timestamp after `observed_at`.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/simulation/tests/test_history.py -v`

Expected: FAIL because history functions do not exist.

- [ ] **Step 3: Implement DataFrame conversion and Parquet output**

```python
STATUS_COLUMNS = ["station_id", "ts", "ports_free", "ports_busy", "ports_broken", "scenario"]


def write_status_history(frame: pd.DataFrame, path: Path) -> Path:
    _validate_status_frame(frame)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.sort_values(["scenario", "station_id", "ts"]).to_parquet(path, index=False)
    return path
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest app/backend/modules/simulation/tests/test_history.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/simulation
git commit -m "feat(sim): publish status history and lag windows"
```

### Task 5: Implement the Two Baseline Strategies

**Files:**
- Create: `app/backend/modules/simulation/baselines.py`
- Create: `app/backend/modules/simulation/tests/test_baselines.py`

**Interfaces:**
- Produces: `NearestStrategy.select(context) -> RankedPlan` and `CurrentlyAvailableStrategy.select(context) -> RankedPlan`, both conforming to `AllocationStrategy`.

- [ ] **Step 1: Write failing selection tests**

Cover incompatible connector, unreachable SOC, nearest feasible station, currently free station, and deterministic fallback when none is currently free.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/simulation/tests/test_baselines.py -v`

Expected: FAIL because baseline classes do not exist.

- [ ] **Step 3: Implement shared feasibility filtering and deterministic tie-breaking**

```python
feasible = [candidate for candidate in context.candidates if candidate.compatible and candidate.arrival_soc_pct >= context.min_soc_pct]
ranked = sorted(feasible, key=lambda item: (item.distance_km, item.station_id))
```

`currently_available` first restricts to `ports_free > 0`; if empty, it applies the documented common feasible-distance fallback and records that reason.

- [ ] **Step 4: Run tests**

Run: `uv run pytest app/backend/modules/simulation/tests/test_baselines.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/backend/modules/simulation/baselines.py app/backend/modules/simulation/tests/test_baselines.py
git commit -m "feat(sim): add deterministic baseline strategies"
```

### Task 6: Build the Fair 100-Vehicle Runner

**Files:**
- Create: `app/backend/modules/simulation/metrics.py`
- Create: `app/backend/modules/simulation/runner.py`
- Create: `app/backend/modules/simulation/public.py`
- Create: `app/backend/modules/simulation/tests/test_runner.py`

**Interfaces:**
- Produces: `DefaultSimulationRunner(fixture_loader: Callable[[SimulationRequest], FixtureBundle])`, `DefaultSimulationRunner.run(request, strategy) -> SimulationResult`, and `compare_strategies(request, strategies) -> tuple[SimulationResult, ...]`.

- [ ] **Step 1: Write failing fairness and metric tests**

```python
def test_all_strategies_receive_same_fixture_hash(runner, request, strategies) -> None:
    results = runner.compare(request, strategies)
    assert len({item.fixture_hash for item in results}) == 1


def test_failed_vehicles_remain_in_success_rate_denominator() -> None:
    metrics = calculate_metrics([success(), failure()], vehicle_count=2)
    assert metrics.success_rate == 0.5
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/simulation/tests/test_runner.py -v`

Expected: FAIL because runner/metrics do not exist.

- [ ] **Step 3: Implement isolated replay per strategy**

Deep-copy or reconstruct engine state from the immutable `FixtureBundle` for each run. Never reuse RNG or mutable state between strategies.

- [ ] **Step 4: Implement exact metrics**

Success means a compatible port is immediately available at arrival. Define wait cap in scenario config; count every vehicle in `vehicle_count` and failed count. Report mean detour/wait over the documented population and include units.

- [ ] **Step 5: Test injected AI strategy without importing recommendation**

Use a local fake `AllocationStrategy` and assert it is called for each evaluated vehicle; do not import `app.backend.modules.recommendation`.

- [ ] **Step 6: Run tests**

Run: `uv run pytest app/backend/modules/simulation/tests/test_runner.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/backend/modules/simulation
git commit -m "feat(sim): add fair strategy comparison runner"
```

### Task 7: Add Reproducible CLIs and Module Handoff

**Files:**
- Create: `app/backend/modules/station_data/cli.py`
- Create: `app/backend/modules/simulation/cli.py`
- Modify: `app/backend/modules/station_data/SPEC.md`
- Modify: `app/backend/modules/simulation/SPEC.md`
- Create: `app/backend/modules/simulation/tests/test_cli.py`

**Interfaces:**
- Produces: `python -m app.backend.modules.station_data.cli generate` and `python -m app.backend.modules.simulation.cli compare` commands with scenario/seed/output options.

- [ ] **Step 1: Write failing CLI smoke tests**

Invoke `subprocess.run([sys.executable, "-m", "app.backend.modules.station_data.cli", "generate", "--output", str(tmp_path)], check=True)` and the equivalent explicit simulation command with module `app.backend.modules.simulation.cli` and subcommand `compare`; assert manifest, Parquet history, vehicles JSON, and three strategy results validate against contracts.

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/modules/simulation/tests/test_cli.py -v`

Expected: FAIL because CLIs do not exist.

- [ ] **Step 3: Implement argparse CLIs with explicit defaults**

Defaults are scenario `normal`, seed 42, vehicle count 100, and ignored output directories. Print the manifest path and one JSON summary; return non-zero for invalid configuration.

- [ ] **Step 4: Run the full owner gate**

```bash
uv run pytest app/backend/modules/station_data app/backend/modules/simulation -v
uv run ruff check app/backend/modules/station_data app/backend/modules/simulation
uv run pyright app/backend/modules/station_data app/backend/modules/simulation
```

Expected: PASS.

- [ ] **Step 5: Verify dependency boundaries and working tree**

Run: `make lint && git status --short`

Expected: architecture checks pass; only intended docs/results are present and generated large outputs remain ignored.

- [ ] **Step 6: Commit and open PR**

```bash
git add app/backend/modules/station_data app/backend/modules/simulation
git commit -m "docs(data): finalize simulator handoff"
```

PR evidence includes commands/results, fixture manifest/hash, one three-strategy output, data-source labels, limitations, and confirmation that no shared contract changed.
