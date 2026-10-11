# Frontend agent instructions

Read [root `AGENTS.md`](../../AGENTS.md), [frontend `SPEC.md`](SPEC.md), [`app/SPEC.md`](../SPEC.md), the committed [API contract](../../docs/API_CONTRACT.md), [`app/backend/contracts/SPEC.md`](../backend/contracts/SPEC.md), and the assigned plan [`2026-10-11-d-tu-frontend-map.md`](../../docs/superpowers/plans/2026-10-11-d-tu-frontend-map.md).

Allowed feature paths are `app/frontend/src/`, frontend tests/e2e, and this module's docs. Do not edit backend contracts, generated `src/types/api.generated.ts`, OpenAPI, root tooling, lockfiles, CI, or backend modules on a feature branch. Request contract/tooling changes in a separate reviewed PR.

The mock UI starts with `npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173`. OpenAPI types are generated from `../backend/contracts/openapi.yaml` by `npm --prefix app/frontend run generate:api` as part of `make contract-check`; never hand-edit generated types. Use only `make setup`, `make lint`, `make test`, `make contract-check`, `make smoke`, and `make ci` as canonical checks.
