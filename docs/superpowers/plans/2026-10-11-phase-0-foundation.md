# Phase 0 Foundation Implementation Plan

> **For agentic workers:** Use the repository-owned [harness workflow](../../harness/workflow.md), applicable AGENTS/SPEC and assigned issue AC. Track task checkboxes as implementation notes; no external skill/plugin is required. Evidence and handoff follow the common workflow.

**Historical plan:** Foundation code already exists; do not rerun scaffolding/install snippets against the frozen checkout. Current commands, policy and handoff workflow are authoritative; new dependency changes require tooling review.

> Foundation checklist is historical. The current Makefile and shared harness workflow control checks; do not restore obsolete tooling from code examples below.

**Goal:** Build the shared, tested modular-monolith baseline that must merge before the four owner branches begin.

**Architecture:** One Python 3.11 FastAPI backend and one React/Vite/TypeScript frontend live under `app/`. Strict Pydantic contracts and Python ports isolate modules; FastAPI generates the committed OpenAPI artifact, which generates frontend types. A composition root selects mock/file/real-capable adapters through validated settings.

**Tech Stack:** Python 3.11, uv, FastAPI, Pydantic v2, pydantic-settings, pytest, Ruff, Pyright, import-linter, React, Vite, TypeScript, Vitest, Testing Library, Playwright, openapi-typescript, Spectral, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-11-phase-0-foundation-spec.md` and `docs/superpowers/specs/2026-10-11-parallel-development-design.md`

## Global Constraints

- Start from the approved spec commit on `main`; do not start any A/B/C/D domain branch first.
- Keep all runtime source under `app/`; never recreate root `api/`, `sim/`, `ml/`, `web/`, or `data/`.
- Phase 0 provides only fake/mock behavior; do not implement simulation physics, model training, Goong calls, final ranking, or finished UI.
- Python is 3.11; timestamps are timezone-aware; units remain in field names.
- `app/backend/contracts/openapi.yaml` is generated, committed, and never hand-edited.
- Mock, simulated, real, and mixed data are visibly distinguishable.
- Every task follows red-green-refactor and ends with a focused commit.

## File Map

Create the following focused units:

```text
pyproject.toml                         Python dependencies/tool settings
.python-version                       Python 3.11 selection
Makefile                              Canonical developer/CI commands
.pre-commit-config.yaml               Local formatting and secret checks
.importlinter                         Enforced backend dependency direction
.secrets.baseline                     Reviewed detect-secrets baseline
app/backend/contracts/                DTOs, ports, errors, examples, OpenAPI
app/backend/core/settings.py          Validated environment configuration
app/backend/infrastructure/           Mock repositories/services/state
app/backend/api/main.py               FastAPI factory
app/backend/api/dependencies.py       Only composition root
app/backend/api/routes/               Thin HTTP handlers
app/backend/modules/station_data/fixtures/
                                       Small committed deterministic inputs
app/frontend/                          Vite/React/TypeScript application
app/backend/tests/                     Contract, adapter, API, architecture tests
.github/workflows/ci.yml               Required PR checks
.github/workflows/release.yml          Manual/tag artifact packaging
docs/runbooks/branch-protection.md     Exact GitHub settings
```

---

### Task 1: Bootstrap Reproducible Toolchains and Canonical Commands

**Files:**
- Create: `.python-version`
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `.pre-commit-config.yaml`
- Create: `app/__init__.py`
- Create: `app/backend/__init__.py`
- Create: `app/backend/tests/test_bootstrap.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: approved directory layout.
- Produces: `make setup`, `make format`, `make lint`, `make test`, `make contract-check`, `make smoke`, and `make ci` entry points used by every later task.

- [ ] **Step 1: Add a failing bootstrap test**

```python
# app/backend/tests/test_bootstrap.py
from pathlib import Path


def test_required_repository_commands_are_declared() -> None:
    makefile = Path("Makefile").read_text()
    for target in ("setup:", "format:", "lint:", "test:", "contract-check:", "smoke:", "ci:"):
        assert target in makefile
```

- [ ] **Step 2: Run the test and confirm the missing project configuration fails**

Run: `python -m pytest app/backend/tests/test_bootstrap.py -v`

Expected: FAIL because pytest/project metadata is not installed or `Makefile` is absent.

- [ ] **Step 3: Create the uv project and install the complete known P0 dependency set**

```bash
uv init --bare --python 3.11
uv add fastapi 'uvicorn[standard]' pydantic pydantic-settings httpx numpy pandas pyarrow pyyaml lightgbm scikit-learn joblib
uv add --dev pytest pytest-asyncio pytest-cov ruff pyright import-linter pre-commit detect-secrets pip-audit
```

Set `.python-version` to:

```text
3.11
```

- [ ] **Step 4: Add canonical Make targets**

```make
.PHONY: setup format lint test contract-check smoke security ci

setup:
	uv sync --frozen
	npm --prefix app/frontend ci

format:
	uv run ruff format app
	uv run ruff check --fix app
	npm --prefix app/frontend run format

lint:
	uv run ruff format --check app
	uv run ruff check app
	uv run pyright app/backend
	uv run lint-imports
	npm --prefix app/frontend run lint
	npm --prefix app/frontend run format:check

test:
	uv run pytest app/backend --cov=app.backend --cov-report=term-missing --cov-fail-under=75
	npm --prefix app/frontend run test:coverage

contract-check:
	uv run python -m app.backend.api.generate_openapi --check
	npm --prefix app/frontend run lint:openapi
	npm --prefix app/frontend run generate:api
	git diff --exit-code -- app/backend/contracts/openapi.yaml app/frontend/src/types/api.generated.ts

smoke:
	npm --prefix app/frontend run test:e2e

security:
	uv run detect-secrets scan --baseline .secrets.baseline
	uv run pip-audit
	npm --prefix app/frontend audit --audit-level=high

ci: lint test contract-check smoke security
```

- [ ] **Step 5: Configure Ruff, Pyright, pytest, coverage, and import-linter in `pyproject.toml`**

Use `line-length = 100`, Python target `py311`, and pytest path `app/backend/tests`. Create `.importlinter` with:

```ini
[importlinter]
root_package = app

[importlinter:contract:contracts-independent]
name = Contracts do not depend on application modules
type = forbidden
source_modules =
    app.backend.contracts
forbidden_modules =
    app.backend.api
    app.backend.infrastructure
    app.backend.modules

[importlinter:contract:domain-independent-of-api]
name = Domain modules do not depend on API
type = forbidden
source_modules =
    app.backend.modules
forbidden_modules =
    app.backend.api
```

- [ ] **Step 6: Configure local pre-commit checks**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.1
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: [--baseline, .secrets.baseline]
```

If a listed revision cannot be fetched, select the newest stable revision verified on the execution date and record that resolved revision in the PR description.

- [ ] **Step 7: Generate locks and the initial reviewed secret baseline**

Run: `uv lock && uv run detect-secrets scan > .secrets.baseline`

Expected: `uv.lock` and `.secrets.baseline` exist and contain no real credentials.

- [ ] **Step 8: Run the bootstrap test**

Run: `uv run pytest app/backend/tests/test_bootstrap.py -v`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add .python-version pyproject.toml uv.lock Makefile .pre-commit-config.yaml .importlinter .secrets.baseline .gitignore app/__init__.py app/backend/__init__.py app/backend/tests/test_bootstrap.py
git commit -m "build: bootstrap shared project toolchains"
```

### Task 2: Define Settings and Adapter Selection

**Files:**
- Create: `app/backend/core/__init__.py`
- Create: `app/backend/core/settings.py`
- Create: `app/backend/tests/core/test_settings.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `BackendKind = Literal["mock", "file", "real"]`, `PredictorKind = Literal["fake", "model"]`, `RouteKind = Literal["fake", "goong"]`, and cached `get_settings() -> Settings`.

- [ ] **Step 1: Write failing settings tests**

```python
from pydantic import ValidationError

from app.backend.core.settings import Settings


def test_mock_mode_needs_no_external_secret() -> None:
    settings = Settings(data_backend="mock", predictor_backend="fake", route_backend="fake")
    assert settings.demo_seed == 42


def test_goong_mode_requires_rest_key() -> None:
    try:
        Settings(route_backend="goong", goong_rest_api_key=None)
    except ValidationError:
        return
    raise AssertionError("goong mode accepted a missing key")
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/tests/core/test_settings.py -v`

Expected: FAIL with `ModuleNotFoundError` for `app.backend.core.settings`.

- [ ] **Step 3: Implement strict settings**

```python
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_backend: Literal["mock", "file", "real"] = "mock"
    predictor_backend: Literal["fake", "model"] = "fake"
    route_backend: Literal["fake", "goong"] = "fake"
    data_dir: Path = Path("app/backend/modules/station_data")
    model_dir: Path = Path("app/backend/modules/prediction/artifacts")
    demo_seed: int = 42
    min_arrival_soc_pct: float = 10.0
    goong_rest_api_key: str | None = None

    @model_validator(mode="after")
    def validate_selected_backends(self) -> "Settings":
        if self.route_backend == "goong" and not self.goong_rest_api_key:
            raise ValueError("GOONG_REST_API_KEY is required for ROUTE_BACKEND=goong")
        if self.predictor_backend == "model" and not self.model_dir.exists():
            raise ValueError("MODEL_DIR must exist for PREDICTOR_BACKEND=model")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Add the backend selectors to `.env.example`**

```dotenv
DATA_BACKEND=mock
PREDICTOR_BACKEND=fake
ROUTE_BACKEND=fake
```

- [ ] **Step 5: Run settings tests**

Run: `uv run pytest app/backend/tests/core/test_settings.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/core .env.example
git commit -m "feat: add validated backend settings"
```

### Task 3: Freeze Common Data Contracts and Examples

**Files:**
- Create: `app/backend/contracts/__init__.py`
- Create: `app/backend/contracts/enums.py`
- Create: `app/backend/contracts/common.py`
- Create: `app/backend/contracts/stations.py`
- Create: `app/backend/contracts/examples/stations.response.json`
- Create: `app/backend/modules/station_data/fixtures/stations.json`
- Create: `app/backend/modules/station_data/fixtures/scenarios.yaml`
- Create: `app/backend/tests/contracts/test_station_contracts.py`

**Interfaces:**
- Produces: `Scenario`, `DataType`, `Strategy`, `Coordinate`, `Station`, `StationStatus`, `StationListResponse`.

- [ ] **Step 1: Write failing validation tests**

```python
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.backend.contracts.enums import Scenario
from app.backend.contracts.stations import Station, StationStatus


def test_station_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Station(station_id="S001", name="A", lat=10.7, lng=106.7, n_ports=2,
                power_kw=120, connector_types=["CCS2"], network="demo",
                station_type="highway", source="fixture", assumptions=[], extra_value=1)


def test_status_conserves_ports() -> None:
    with pytest.raises(ValidationError):
        StationStatus(station_id="S001", ts=datetime.fromisoformat("2026-10-13T16:00:00+07:00"),
                      ports_free=1, ports_busy=1, ports_broken=1,
                      n_ports=2, scenario=Scenario.NORMAL)
```

- [ ] **Step 2: Run and verify failure**

Run: `uv run pytest app/backend/tests/contracts/test_station_contracts.py -v`

Expected: FAIL because contract modules do not exist.

- [ ] **Step 3: Implement enums and strict models**

```python
from enum import StrEnum


class Scenario(StrEnum):
    NORMAL = "normal"
    HOLIDAY_30_4 = "holiday_30_4"
    TET = "tet"


class DataType(StrEnum):
    MOCK = "mock"
    SIMULATED = "simulated"
    REAL = "real"
    MIXED = "mixed"


class Strategy(StrEnum):
    NEAREST = "nearest"
    CURRENTLY_AVAILABLE = "currently_available"
    AI_ALLOCATION = "ai_allocation"
```

Use a shared `StrictModel` with `ConfigDict(extra="forbid")`; enforce coordinate bounds, positive capacity/power, timezone-aware timestamps, and `ports_free + ports_busy + ports_broken == n_ports`.

- [ ] **Step 4: Add two deterministic station fixtures and three explicit scenarios**

Use `S001` and `S002`, CCS2, TP.HCM–Vũng Tàu coordinates, `source: "phase0-fixture"`, and assumptions that state capacities are synthetic. Scenario YAML uses seed 42 and step 5 minutes.

- [ ] **Step 5: Validate fixtures through models**

Run: `uv run pytest app/backend/tests/contracts/test_station_contracts.py -v`

Expected: PASS, including loading `stations.json` into `Station` objects.

- [ ] **Step 6: Commit**

```bash
git add app/backend/contracts app/backend/modules/station_data/fixtures app/backend/tests/contracts
git commit -m "feat: define shared station data contracts"
```

### Task 4: Define API DTOs, Errors, and Python Ports

**Files:**
- Create: `app/backend/contracts/prediction.py`
- Create: `app/backend/contracts/recommendation.py`
- Create: `app/backend/contracts/simulation.py`
- Create: `app/backend/contracts/errors.py`
- Create: `app/backend/contracts/ports.py`
- Create: `app/backend/tests/contracts/test_api_contracts.py`
- Create: `app/backend/tests/contracts/test_ports.py`
- Modify: `docs/API_CONTRACT.md`

**Interfaces:**
- Produces: strict DTOs from `docs/API_CONTRACT.md` and runtime-checkable protocols `StationRepository`, `StatusRepository`, `RouteProvider`, `Predictor`, `AllocationStrategy`, `SimulationRunner`.

- [ ] **Step 1: Write failing DTO range and timezone tests**

```python
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.backend.contracts.prediction import PredictRequest, PredictionResult


def test_prediction_probability_is_bounded() -> None:
    with pytest.raises(ValidationError):
        PredictionResult(station_id="S001", eta="2026-10-13T16:40:00+07:00",
                         p_available=1.1, reasons=[], explanation_method="rule",
                         model_version="fake-v1", data_type="mock", contract_version="0.1.0")


def test_predict_request_rejects_naive_time() -> None:
    with pytest.raises(ValidationError):
        PredictRequest(station_id="S001", observed_at=datetime(2026, 10, 13, 16),
                       eta="2026-10-13T16:40:00+07:00", connector_type="CCS2",
                       scenario="normal")
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/tests/contracts/test_api_contracts.py -v`

Expected: FAIL because DTOs do not exist.

- [ ] **Step 3: Implement exact contract shapes**

Implement requests/responses for predict, recommend, pressure, simulate, reset, shared `ErrorResponse(code, message, details)`, and nested vehicle/plan/metrics models. Also define `ScenarioConfig`, `Vehicle`, `StatusWindow`, `RouteRequest`, `RouteResult`, `AllocationContext`, `FeasibleCandidate`, `RankedCandidate`, `RankedPlan`, `FixtureBundle`, and `DataManifest`. Define typed `DomainError` subclasses `StationNotFoundError`, `DataSourceUnavailableError`, `ModelNotReadyError`, `RouteUnavailableError`, and `RequestConflictError`. `SimulationResult` includes `fixture_hash` so comparisons can prove identical inputs; update `docs/API_CONTRACT.md` with that additive field. Use `contract_version="0.1.0"`; preserve existing fields and nullability from `docs/API_CONTRACT.md`.

- [ ] **Step 4: Define ports with concrete signatures**

```python
from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class StationRepository(Protocol):
    def list_stations(self) -> tuple[Station, ...]:
        raise NotImplementedError

    def get_station(self, station_id: str) -> Station:
        raise NotImplementedError


@runtime_checkable
class StatusRepository(Protocol):
    def window(
        self,
        station_id: str,
        observed_at: datetime,
        lags: tuple[int, ...] = (15, 30, 60),
    ) -> StatusWindow:
        raise NotImplementedError


@runtime_checkable
class RouteProvider(Protocol):
    async def get_routes(self, request: RouteRequest) -> tuple[RouteResult, ...]:
        raise NotImplementedError


@runtime_checkable
class Predictor(Protocol):
    def predict(self, request: PredictRequest) -> PredictionResult:
        raise NotImplementedError


@runtime_checkable
class AllocationStrategy(Protocol):
    def select(self, context: AllocationContext) -> RankedPlan:
        raise NotImplementedError


@runtime_checkable
class SimulationRunner(Protocol):
    def run(self, request: SimulationRequest, strategy: AllocationStrategy) -> SimulationResult:
        raise NotImplementedError
```

Keep every signature expressed only in shared contract DTOs; `RouteProvider.get_routes()` alone is async because it performs external I/O.

- [ ] **Step 5: Add structural conformance tests with tiny fakes**

Assert `isinstance(FakePredictor(), Predictor)` using `@runtime_checkable` and verify method results validate through Pydantic.

- [ ] **Step 6: Run contract tests**

Run: `uv run pytest app/backend/tests/contracts -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/backend/contracts app/backend/tests/contracts docs/API_CONTRACT.md
git commit -m "feat: define API contracts and service ports"
```

### Task 5: Implement Mock Adapters and Conformance Tests

**Files:**
- Create: `app/backend/infrastructure/__init__.py`
- Create: `app/backend/infrastructure/repositories/mock.py`
- Create: `app/backend/infrastructure/services/fakes.py`
- Create: `app/backend/infrastructure/state/in_memory.py`
- Create: `app/backend/tests/conformance/repository_contract.py`
- Create: `app/backend/tests/infrastructure/test_mock_adapters.py`

**Interfaces:**
- Consumes: shared ports and committed fixtures.
- Produces: `MockStationRepository`, `MockStatusRepository`, `FakeRouteProvider`, `FakePredictor`, `FakeAllocationStrategy`, `FakeSimulationRunner`, `InMemoryAllocationStore`.

- [ ] **Step 1: Write a reusable repository conformance suite**

```python
class StationRepositoryContract:
    def make_repository(self):
        raise NotImplementedError

    def test_list_returns_valid_unique_station_ids(self) -> None:
        stations = self.make_repository().list_stations()
        assert stations
        assert len({item.station_id for item in stations}) == len(stations)
```

- [ ] **Step 2: Add failing mock adapter tests**

Subclass the contract, return `MockStationRepository`, and assert fake predictor always returns a deterministic probability in `[0, 1]` with `data_type="mock"`.

- [ ] **Step 3: Verify failure**

Run: `uv run pytest app/backend/tests/infrastructure/test_mock_adapters.py -v`

Expected: FAIL because adapters do not exist.

- [ ] **Step 4: Implement fixture-backed/fake adapters**

```python
class FakePredictor:
    def predict(self, request: PredictRequest) -> PredictionResult:
        return PredictionResult(
            station_id=request.station_id,
            eta=request.eta,
            p_available=0.75,
            reasons=["Phase 0 deterministic mock prediction"],
            explanation_method="rule",
            model_version="fake-v1",
            data_type=DataType.MOCK,
            contract_version="0.1.0",
        )
```

Use IDs and distances from fixtures for route/recommend/simulation fakes; never use random values.

- [ ] **Step 5: Run conformance and adapter tests**

Run: `uv run pytest app/backend/tests/conformance app/backend/tests/infrastructure -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/backend/infrastructure app/backend/tests/conformance app/backend/tests/infrastructure
git commit -m "feat: add deterministic mock adapters"
```

### Task 6: Build the FastAPI Composition Root and Mock Endpoints

**Files:**
- Create: `app/backend/api/__init__.py`
- Create: `app/backend/api/dependencies.py`
- Create: `app/backend/api/main.py`
- Create: `app/backend/api/routes/stations.py`
- Create: `app/backend/api/routes/prediction.py`
- Create: `app/backend/api/routes/recommendation.py`
- Create: `app/backend/api/routes/operator.py`
- Create: `app/backend/api/errors.py`
- Create: `app/backend/tests/api/test_mock_api.py`

**Interfaces:**
- Produces: `create_app(settings: Settings | None = None) -> FastAPI` and all documented `/api` operations using mocks.

- [ ] **Step 1: Write failing HTTP contract tests**

```python
from fastapi.testclient import TestClient

from app.backend.api.main import create_app


def test_station_endpoint_labels_mock_data() -> None:
    response = TestClient(create_app()).get("/api/stations")
    assert response.status_code == 200
    assert response.json()["data_type"] == "mock"


def test_unknown_station_is_404() -> None:
    response = TestClient(create_app()).post("/api/predict", json={
        "station_id": "UNKNOWN", "observed_at": "2026-10-13T16:00:00+07:00",
        "eta": "2026-10-13T16:40:00+07:00", "connector_type": "CCS2",
        "scenario": "normal"
    })
    assert response.status_code == 404
    assert response.json()["code"] == "STATION_NOT_FOUND"
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/tests/api/test_mock_api.py -v`

Expected: FAIL because `create_app` does not exist.

- [ ] **Step 3: Implement the composition root**

Create dependencies once in an `AppContainer` dataclass. Select only mock/fake implementations in Phase 0. Raise a typed startup configuration error for unavailable `file`, `real`, `model`, or `goong` selections.

- [ ] **Step 4: Implement thin route handlers and error mapping**

Each route declares `response_model`, stable `operation_id`, documented error responses, and delegates to the injected fake. Implement `/stations`, `/predict`, `/recommend`, `/pressure`, `/simulate`, and `/reset`; expose `/whatif` as a declared 503 `FEATURE_NOT_READY` response until P1. Add `/health` for process liveness and `/ready` for selected dependency readiness.

- [ ] **Step 5: Run API tests**

Run: `uv run pytest app/backend/tests/api/test_mock_api.py -v`

Expected: PASS for success, 404, 409, 422, 503, reset, and source-label cases.

- [ ] **Step 6: Commit**

```bash
git add app/backend/api app/backend/tests/api
git commit -m "feat: expose contract-compliant mock API"
```

### Task 7: Generate and Validate the OpenAPI Contract

**Files:**
- Create: `app/backend/contracts/generate_openapi.py`
- Create: `app/backend/contracts/openapi.yaml`
- Create: `app/backend/contracts/examples/predict.request.json`
- Create: `app/backend/contracts/examples/predict.response.json`
- Create: `app/backend/contracts/examples/recommend.request.json`
- Create: `app/backend/contracts/examples/recommend.response.json`
- Create: `app/backend/tests/contracts/test_openapi.py`

**Interfaces:**
- Produces: deterministic `generate_document() -> str` and CLI `--check` behavior; committed OpenAPI 3.1 artifact.

- [ ] **Step 1: Write failing deterministic-generation tests**

```python
from pathlib import Path

from app.backend.api.generate_openapi import generate_document


def test_committed_openapi_matches_generated_document() -> None:
    assert Path("app/backend/contracts/openapi.yaml").read_text() == generate_document()
```

- [ ] **Step 2: Verify failure**

Run: `uv run pytest app/backend/tests/contracts/test_openapi.py -v`

Expected: FAIL because generator/artifact do not exist.

- [ ] **Step 3: Implement sorted deterministic YAML generation**

Call `create_app().openapi()`, recursively sort object keys, serialize with `yaml.safe_dump(document, sort_keys=False, allow_unicode=True)`, and end with one newline. `--check` compares bytes and exits non-zero without rewriting; the default writes the artifact.

- [ ] **Step 4: Generate the artifact and add contract examples**

Run: `uv run python -m app.backend.api.generate_openapi`

Expected: `openapi.yaml` contains all operation IDs and declared error models.

- [ ] **Step 5: Test every JSON example through its Pydantic model**

Add parametrized tests that load each example and call the matching `.model_validate()`.

- [ ] **Step 6: Run contract tests**

Run: `uv run pytest app/backend/tests/contracts -v`

Expected: PASS and `uv run python -m app.backend.api.generate_openapi --check` exits 0.

- [ ] **Step 7: Commit**

```bash
git add app/backend/contracts app/backend/tests/contracts
git commit -m "feat: publish deterministic OpenAPI contract"
```

### Task 8: Scaffold the Typed Frontend and API Client Boundary

**Files:**
- Create: `app/frontend/package.json`
- Create: `app/frontend/package-lock.json`
- Create: `app/frontend/tsconfig.json`
- Create: `app/frontend/vite.config.ts`
- Create: `app/frontend/eslint.config.js`
- Create: `app/frontend/.prettierrc.json`
- Create: `app/frontend/src/types/api.generated.ts`
- Create: `app/frontend/src/services/api.ts`
- Create: `app/frontend/src/services/api.test.ts`
- Create: `app/frontend/src/test/setup.ts`

**Interfaces:**
- Consumes: committed OpenAPI.
- Produces: `ApiClient` with typed `listStations()`, `predict()`, `recommend()`, `pressure()`, `simulate()`, and `reset()` methods.

- [ ] **Step 1: Initialize React/Vite TypeScript and install quality/test tools**

```bash
npm create vite@latest app/frontend -- --template react-ts
npm --prefix app/frontend install
npm --prefix app/frontend install -D vitest @vitest/coverage-v8 @testing-library/react @testing-library/jest-dom jsdom prettier openapi-typescript @stoplight/spectral-cli @playwright/test
```

- [ ] **Step 2: Add a failing typed API service test**

```typescript
import { expect, test, vi } from "vitest";
import { ApiClient } from "./api";

test("listStations returns the typed payload", async () => {
  const fetcher = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ stations: [], data_type: "mock", source_notes: [] }),
  });
  const client = new ApiClient("http://test/api", fetcher as typeof fetch);
  expect((await client.listStations()).data_type).toBe("mock");
});
```

- [ ] **Step 3: Generate TypeScript types from OpenAPI**

Add scripts:

```json
{
  "generate:api": "openapi-typescript ../backend/contracts/openapi.yaml -o src/types/api.generated.ts",
  "lint:openapi": "spectral lint ../backend/contracts/openapi.yaml",
  "test:coverage": "vitest run --coverage",
  "format": "prettier --write src",
  "format:check": "prettier --check src",
  "test:e2e": "playwright test"
}
```

Run: `npm --prefix app/frontend run generate:api`

- [ ] **Step 4: Implement `ApiClient` using generated operation shapes**

Use one private `request<T>()` that throws `ApiError(status, body)` on non-2xx. Do not call `fetch` from React components.

- [ ] **Step 5: Run service tests and production build**

Run: `npm --prefix app/frontend run test:coverage && npm --prefix app/frontend run build`

Expected: PASS and `app/frontend/dist` is created but ignored.

- [ ] **Step 6: Commit**

```bash
git add app/frontend
git commit -m "feat: scaffold typed frontend API boundary"
```

### Task 9: Complete the Mock Vertical Slice

**Files:**
- Modify: `app/frontend/src/App.tsx`
- Create: `app/frontend/src/components/MockStationList.tsx`
- Create: `app/frontend/src/components/MockStationList.test.tsx`
- Modify: `app/frontend/src/index.css`
- Create: `app/frontend/e2e/mock-stations.spec.ts`
- Create: `app/frontend/playwright.config.ts`

**Interfaces:**
- Consumes: `ApiClient.listStations()`.
- Produces: visible fixture station list and `Mock data` badge; no finished Driver/Operator flows.

- [ ] **Step 1: Write a failing component test**

```typescript
test("renders a visible mock label and fixture station", async () => {
  render(<MockStationList client={fakeClientReturningS001} />);
  expect(await screen.findByText("S001")).toBeInTheDocument();
  expect(screen.getByText("Mock data")).toBeInTheDocument();
});
```

- [ ] **Step 2: Verify failure**

Run: `npm --prefix app/frontend test -- --run MockStationList`

Expected: FAIL because component does not exist.

- [ ] **Step 3: Implement loading, success, empty, and error states**

Use `useEffect` with an abort controller, one request on mount, semantic status text, and a retry button. Keep styling minimal and accessible.

- [ ] **Step 4: Add Playwright smoke test**

Start `uv run uvicorn app.backend.api.main:create_app --factory --port 8000` and Vite through Playwright `webServer`; assert `S001` and `Mock data` are visible.

- [ ] **Step 5: Run frontend unit and E2E tests**

Run: `npm --prefix app/frontend run test:coverage && npm --prefix app/frontend run test:e2e`

Expected: PASS without Goong keys or model artifacts.

- [ ] **Step 6: Commit**

```bash
git add app/frontend
git commit -m "feat: add mock fixture vertical slice"
```

### Task 10: Add Architecture, CI, Security, and Release Gates

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `.github/pull_request_template.md`
- Create: `.github/CODEOWNERS`
- Create: `docs/runbooks/branch-protection.md`
- Create: `app/backend/tests/architecture/test_boundaries.py`

**Interfaces:**
- Produces: required checks named exactly `python-quality`, `python-tests`, `contract-check`, `frontend-quality`, `integration-smoke`, `security`.

- [ ] **Step 1: Add a failing architecture boundary test**

```python
from pathlib import Path


def test_contracts_do_not_import_application_modules() -> None:
    forbidden = ("app.backend.api", "app.backend.infrastructure", "app.backend.modules")
    for path in Path("app/backend/contracts").glob("*.py"):
        text = path.read_text()
        assert not any(name in text for name in forbidden), path
```

- [ ] **Step 2: Configure six explicit CI jobs**

Each job uses `actions/checkout@v4`, Python 3.11, `astral-sh/setup-uv`, Node LTS where needed, frozen installs, least-privilege `contents: read`, and concurrency cancellation. Map jobs to canonical commands; `contract-check` additionally runs an OpenAPI breaking-change action against `origin/main`.

- [ ] **Step 3: Add security gates**

Run detect-secrets, pip-audit, and npm high-level audit. Document a time-bounded exception format in the runbook; an exception includes advisory, owner, rationale, expiry date, and mitigation.

- [ ] **Step 4: Add PR policy and ownership**

Use `@thangak18` as the verified bootstrap owner for `/app/backend/contracts/`, `/.github/`, `/pyproject.toml`, `/uv.lock`, and `/Makefile`. The PR template requires owner, scope, contract impact, commands/results, data origin, limitations, rollback, and screenshots for UI. Keep GitHub's “Require review from Code Owners” switch off until at least two non-author maintainer handles are verified, so the sole bootstrap owner cannot deadlock their own PR.

- [ ] **Step 5: Add manual/tag release workflow**

Trigger on `workflow_dispatch` and `demo-v*` tags, run `make ci`, build the frontend artifact, and upload it with the commit SHA. Do not deploy or access production secrets.

- [ ] **Step 6: Document exact branch protection settings**

Require the six check names, one non-author approval, stale approval dismissal, conversation resolution, up-to-date branch, linear history, squash merge, no force push/deletion, and no routine admin bypass. Document the separate condition for enabling required code-owner review after a second maintainer handle is verified.

- [ ] **Step 7: Run architecture and workflow syntax checks**

Run: `uv run pytest app/backend/tests/architecture -v && make lint`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add .github docs/runbooks app/backend/tests/architecture
git commit -m "ci: enforce repository quality gates"
```

### Task 11: Verify a Fresh Phase 0 Handoff

**Files:**
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `app/SPEC.md`
- Create: `app/AGENTS.md`
- Create: `app/backend/AGENTS.md`
- Create: `app/frontend/AGENTS.md`
- Create: `docs/runbooks/phase-0-handoff.md`

**Interfaces:**
- Produces: exact agent reading order, verified commands, and the recorded foundation merge SHA procedure.

- [ ] **Step 1: Add scoped agent instructions**

Each local `AGENTS.md` points to root `AGENTS.md`, the nearest `SPEC.md`, contracts, and the assigned plan. It lists allowed paths and explicitly forbids feature-branch contract/tooling edits.

- [ ] **Step 2: Assert the obsolete root layout stays absent**

Run: `test ! -e api && test ! -e sim && test ! -e ml && test ! -e web && test ! -e data`

Expected: exit 0; all runtime work remains under `app/`.

- [ ] **Step 3: Replace planned-command wording with verified commands**

Document Makefile canonical targets (including build and harness checks added by tooling), plus mock backend/frontend start commands actually verified. Record exact results/SHA; historical expected outcomes are not evidence.

- [ ] **Step 4: Run the complete gate from a clean checkout or disposable worktree**

```bash
make setup
make ci
git status --short
```

Expected: every command exits 0 and `git status --short` prints nothing.

- [ ] **Step 5: Record the handoff rule**

The runbook instructs the integrator to merge the reviewed PR, record `git rev-parse HEAD`, enable branch protection, then create all four branches from that exact SHA.

- [ ] **Step 6: Commit**

```bash
git add README.md CONTRIBUTING.md app/AGENTS.md app/backend/AGENTS.md app/frontend/AGENTS.md app/SPEC.md docs/runbooks/phase-0-handoff.md
git commit -m "docs: finalize phase zero handoff"
```

- [ ] **Step 7: Open the Foundation PR**

Include all `make ci` output, OpenAPI/type generation proof, the mock UI screenshot, known limitations, and the branch-protection checklist. Do not create the four owner branches until this PR is green, approved, and merged.
