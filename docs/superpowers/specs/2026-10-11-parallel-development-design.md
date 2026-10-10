# V-EV Flow Parallel Development Design

**Date:** 2026-10-11

**Status:** Approved design; implementation has not started

**Sources of truth:** `V-EV Flow – Proposal.md`, `V-EV Flow — Kế hoạch làm việc nhóm 4 người (đến 15 10).md`, and the current repository documents

## Goal

Prepare one shared Phase 0 baseline on `main` so Bảo (A), Thắng (B), Kiên (C), and Tú (D) can implement P0 concurrently from the same commit. The baseline must provide a runnable mock vertical slice, frozen cross-module contracts, deterministic fixtures, CI, and protected-branch rules. It must not implement the four owners' domain algorithms.

## Architectural Decision

Use a modular monolith. The backend is one Python application and deployment unit, but station data, simulation, prediction, recommendation, infrastructure, and HTTP delivery are explicit modules. The frontend is built separately and consumes only the public HTTP contract. Internal modules communicate through typed contracts and injected ports, never through another module's private implementation.

Microservices are rejected for the hackathon because independent deployment, network failure handling, and observability would consume the five-day schedule. An unstructured monolith is also rejected because it would allow four agents to create circular dependencies and incompatible data shapes.

## Target Repository Layout

```text
.
├── .github/                     # CI/release workflows and PR policy
├── app/
│   ├── SPEC.md                  # whole-application invariants
│   ├── backend/
│   │   ├── SPEC.md
│   │   ├── contracts/           # DTOs, enums, errors, ports, OpenAPI artifact
│   │   ├── core/                # settings and bootstrap primitives only
│   │   ├── modules/
│   │   │   ├── station_data/    # A — Bảo
│   │   │   ├── simulation/      # A — Bảo
│   │   │   ├── prediction/      # B — Thắng
│   │   │   └── recommendation/  # C — Kiên
│   │   ├── infrastructure/      # C — Kiên; persistence and routing adapters
│   │   ├── api/                 # C — Kiên; FastAPI and composition root
│   │   └── tests/
│   └── frontend/                # D — Tú
├── deploy/                      # demo images/Compose and runbook
├── docs/                        # architecture, plans, contracts, runbooks
├── scripts/                     # repository automation only
├── pyproject.toml
├── uv.lock
└── Makefile
```

The current root `api/`, `sim/`, `ml/`, `web/`, and `data/` directories are initial placeholders, not a second runtime layout. Phase 0 moves their useful guidance into the matching `app/` specs and removes the empty duplicate structure. Proposal documents remain at the repository root.

## Ownership and Module Boundaries

| Owner | Owned modules | Required public output |
| --- | --- | --- |
| A — Bảo | `station_data`, `simulation` | Validated fixtures, deterministic simulator, 100-vehicle runner, `SimulationRunner` implementation |
| B — Thắng | `prediction` | Feature/label pipeline, temporal evaluation, calibrated model, `Predictor` implementation and model manifest |
| C — Kiên | `recommendation`, `infrastructure`, `api` | Injected adapters, recommendation/allocation behavior, FastAPI endpoints, integration composition |
| D — Tú | `frontend` | Driver and Operator UI using generated HTTP types and one API service boundary |

Each owner may choose internal algorithms and file decomposition. They may not change public DTOs, OpenAPI, shared tooling, or another owner's module in their feature PR. A cross-module change starts as a separate contract PR and updates examples and contract tests before consumers.

## Contracts and OpenAPI

Backend domain and persistence contracts live in `app/backend/contracts` as Pydantic models, enums, domain errors, and Python protocols. Models reject unknown fields, use names containing units, require timezone-aware timestamps, and preserve the existing scenario and data-origin enums.

The committed HTTP contract is `app/backend/contracts/openapi.yaml`. FastAPI/Pydantic generate it deterministically; it is never hand-edited. Producers update route/model definitions in a contract PR and regenerate the artifact. Consumers treat the committed artifact as authoritative.

Contract CI must:

1. Generate OpenAPI and fail when the working tree differs from the committed artifact.
2. Lint OpenAPI and validate every request, response, and error example.
3. Diff the proposed artifact against `main` and reject an unapproved breaking change.
4. Generate frontend types into `app/frontend/src/types/api.generated.ts` and fail on drift.
5. Run the mock server and contract smoke tests without external credentials.

Every operation has a stable `operationId`, explicit success and error responses, realistic examples, `data_type`, and applicable contract/data/model versions. FastAPI validation may retain its standard 422 body; business failures use the shared `{code, message, details}` shape. Mock, simulated, and real values are never presented under the same label.

## Ports, Adapters, and Dependency Injection

Shared ports include `StationRepository`, `StatusRepository`, `RouteProvider`, `Predictor`, `AllocationStrategy`, and `SimulationRunner`. Business services depend on these interfaces. The API composition root is the only place that selects concrete implementations.

```env
DATA_BACKEND=mock
PREDICTOR_BACKEND=fake
ROUTE_BACKEND=fake
```

Phase 0 implements mock and local-file data adapters plus fake predictor/routing adapters. Later real Tasco/VETC, trained-model, and Goong adapters implement the same ports. Selecting an unavailable real adapter fails during startup with a clear configuration error; the system must not silently fall back and mislabel output.

## Phase 0 Vertical Slice

Phase 0 is one reviewed PR merged before feature branches are created. It supplies Python and Node manifests/lockfiles, canonical Make targets, settings validation, contracts, small committed fixtures, fake adapters, mock FastAPI endpoints, a minimal React shell, contract and smoke tests, CI, and repository policies.

The slice proves: a fixture station is loaded through an injected repository, returned by mock API, consumed by the typed frontend service, and rendered with a visible `mock` label. It does not implement simulation physics, model training, Goong routing, ranking, allocation, or finished UI.

After Phase 0 is green, create these branches from the exact merge commit:

- `feat/data-simulator` — Bảo
- `feat/ml-predict` — Thắng
- `feat/recommend-api` — Kiên
- `feat/web-map` — Tú

This is a hard branch gate. The four owners and their agents may review specs and prepare questions before Phase 0, but domain implementation branches must be created from the green Phase 0 merge commit. A dedicated foundation agent may implement Phase 0; Kiên integrates it and at least one other member reviews it. Feature work based on the pre-foundation scaffold is discarded or rebased before review.

## Testing Strategy

- Unit tests live with or directly under each backend module; frontend uses colocated component/service tests.
- Reusable adapter conformance tests must pass for mock, file, and future real implementations.
- Contract tests validate Pydantic models, examples, OpenAPI, and generated TypeScript types.
- Architecture tests reject forbidden cross-module imports.
- Integration tests assemble services with fakes and verify backend selection through configuration.
- One end-to-end smoke path covers fixture → API → frontend; external services are not required in PR CI.
- ML tests cover temporal leakage and artifact metadata. Simulator tests cover seed reproducibility, conserved port state, and equal fixtures across strategies.
- Coverage starts at 75% overall; critical contracts, recommendation rules, and adapter selection require direct tests regardless of the aggregate number.

## CI, Review, and Release Gates

Required PR jobs are `python-quality`, `python-tests`, `contract-check`, `frontend-quality`, `integration-smoke`, and `security`. They use frozen lockfiles and run on every PR to `main`. Release automation runs only manually or for `demo-v*` tags and packages an already-green commit.

`main` disallows direct and force pushes, requires an up-to-date branch, all checks, at least one non-author approval, stale-approval dismissal, resolved conversations, and squash merge. Shared contract, workflow, and root-tooling changes require their code-owner review once verified GitHub handles are configured. Routine administrator bypass is disabled.

Every PR states owner, scope, affected module, contract impact, commands executed, evidence, data origin, limitations, and rollback. No PR may hard-code winning metrics, commit credentials/partner data/model binaries, or claim simulated results are real.

## Agent-Facing Specifications

Every implementation agent reads the root `AGENTS.md`, `app/SPEC.md`, its nearest module `SPEC.md`, the shared contract spec, and its assigned implementation plan. A module spec defines objective, owned paths, inputs, outputs, public API, invariants, allowed dependencies, forbidden imports, P0/P1/non-goals, failure behavior, tests, verification commands, PR evidence, and Definition of Done.

If instructions conflict, the agent stops and raises a contract issue rather than selecting a new schema. Specs constrain compatibility and outcomes; they do not prescribe an internal algorithm where the proposal leaves room for experimentation.

## Integration Order and Success Criteria

Daily integration order is contracts/fixtures, A and B outputs, C adapters/API, then D UI. A uses a fake allocation strategy; B uses committed fixtures; C uses fake predictor and simulation runner; D uses the committed OpenAPI mock. No owner waits for another branch to begin.

The design succeeds when a fresh clone can run setup, quality checks, tests, contract checks, and the mock vertical slice using documented commands; each owner can work only in owned paths; CI detects contract or architecture drift; and all P0 modules can later be swapped from fakes to real implementations through dependency injection without changing public API consumers.

## Explicit Non-goals

Phase 0 does not add a database server, microservices, production deployment, model training, complete simulation, final recommendation logic, or finished maps. P1 time-shift, what-if, and SHAP remain conditional on a working P0. Charge-to advice, community reporting, full operations dashboard, and real VETC integration remain deferred.
