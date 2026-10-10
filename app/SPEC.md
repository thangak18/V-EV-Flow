# Application Specification

## Purpose

`app/` contains all runtime source, committed runtime fixtures, and automated tests for V-EV Flow. Root folders contain repository automation, deployment definitions, documentation, and source proposals only.

## Global Invariants

- The product is a modular monolith: one backend application, one frontend build, explicit module boundaries.
- Backend modules communicate through `backend/contracts`; frontend communicates through committed OpenAPI only.
- Concrete storage, prediction, routing, and simulation implementations are selected through dependency injection.
- Mock, simulated, real, and mixed data remain visibly distinguishable.
- Time is timezone-aware; replay uses `observed_at`, not the machine clock.
- Runtime code never embeds secrets or partner data.

## Agent Rules

Read the closest module `SPEC.md` before editing. Stay inside the assigned owner paths. Do not edit contracts, OpenAPI, root tooling, CI, or another module in a feature PR. If an interface is insufficient, propose a contract PR with updated models, examples, generated artifacts, and consumer impact.

Local instructions live in [`app/AGENTS.md`](AGENTS.md), [`app/backend/AGENTS.md`](backend/AGENTS.md), and [`app/frontend/AGENTS.md`](frontend/AGENTS.md). They point back to the root rules, this specification, shared contracts, and the assigned implementation plan. Feature branches must not change `app/backend/contracts`, generated OpenAPI/types, Make targets, lockfiles, CI, or another owner's path; use a separate reviewed contract/tooling PR instead.

Foundation verification uses only `make setup`, `make lint`, `make test`, `make contract-check`, `make smoke`, and `make ci`. The mock vertical slice may be started with `uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000` and `npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173`. OpenAPI is generated from the FastAPI app and frontend types from the committed OpenAPI artifact; never hand-edit generated files.

## Completion Standard

A module is complete only when its public output matches contracts, tests cover success and failure behavior, canonical verification commands pass, docs state actual commands and limitations, and the PR includes reproducible evidence.
