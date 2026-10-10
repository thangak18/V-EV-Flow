# `app/` agent instructions

Read in this order: [root `AGENTS.md`](../AGENTS.md), [`app/SPEC.md`](SPEC.md), the shared [data contract](../docs/DATA_CONTRACT.md) and [API contract](../docs/API_CONTRACT.md), then the assigned plan in [`docs/superpowers/plans/`](../docs/superpowers/plans/).

Runtime source, committed fixtures, and tests stay under `app/`. A feature owner may edit only the path assigned by the plan and its colocated tests/docs. Do not edit `app/backend/contracts/`, generated `app/backend/contracts/openapi.yaml`, generated `app/frontend/src/types/api.generated.ts`, Make targets, lockfiles, CI, or another owner's module/tooling on a feature branch. Propose those changes in a separate reviewed contract/tooling PR.

Use only the verified gates `make setup`, `make lint`, `make test`, `make contract-check`, `make smoke`, and `make ci`; record exact output in the PR. Follow the nearest backend/frontend instructions for mock start commands and OpenAPI generation.
