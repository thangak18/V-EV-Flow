# Backend agent instructions

Read [root `AGENTS.md`](../../AGENTS.md), [backend `SPEC.md`](SPEC.md), [`app/SPEC.md`](../SPEC.md), [`app/backend/contracts/SPEC.md`](contracts/SPEC.md), [data contract](../../docs/DATA_CONTRACT.md), [API contract](../../docs/API_CONTRACT.md), and the assigned plan: [`2026-10-11-a-bao-data-simulation.md`](../../docs/superpowers/plans/2026-10-11-a-bao-data-simulation.md), [`2026-10-11-b-thang-ml-prediction.md`](../../docs/superpowers/plans/2026-10-11-b-thang-ml-prediction.md), or [`2026-10-11-c-kien-backend-recommendation.md`](../../docs/superpowers/plans/2026-10-11-c-kien-backend-recommendation.md).

Allowed feature paths are the assigned module, its tests, and its module `SPEC.md`. `app/backend/contracts/`, `app/backend/api/`, generated OpenAPI, root tooling, lockfiles, CI, and other modules are shared or owned paths: do not edit them on a feature branch. Raise a separate contract/tooling PR with consumer impact and regenerated artifacts when an interface must change.

The Phase 0 mock API starts with `uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000`; verify `GET /api/health`. Use only `make setup`, `make lint`, `make test`, `make contract-check`, `make smoke`, and `make ci` as canonical checks. Generate OpenAPI through `make contract-check`; never hand-edit `contracts/openapi.yaml`.
