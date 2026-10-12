# Backend agent instructions

Read [root instructions](../../AGENTS.md), [app instructions](../AGENTS.md), [backend SPEC](SPEC.md), [contracts SPEC](contracts/SPEC.md), and the assigned [owner plan](../../docs/superpowers/plans/README.md). [CONTRIBUTING](../../CONTRIBUTING.md) and module specs define ownership; Makefile defines verification commands.

Use contracts/ports across module boundaries. Kiên owns infrastructure, dependency composition, API routes and their tests. Shared models, OpenAPI/types, root tooling, lockfiles and other owners' code require a separate contract/tooling PR.

Start the mock API with `uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000`; check `/api/health`. Canonical checks come from Makefile. Colocated backend tests must be included in `make test`.

In an authorized contract PR, generate OpenAPI with `uv run python -m app.backend.api.generate_openapi`, then types with `npm --prefix app/frontend run generate:api`. `make contract-check` checks OpenAPI with `--check`, lints it and checks generated type drift; it does not update the OpenAPI artifact. Never hand-edit generated files.
