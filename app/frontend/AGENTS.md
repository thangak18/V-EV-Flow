# Frontend agent instructions

Read [root instructions](../../AGENTS.md), [app instructions](../AGENTS.md), [frontend SPEC](SPEC.md), [API contract](../../docs/API_CONTRACT.md), [contracts SPEC](../backend/contracts/SPEC.md), and [frontend plan](../../docs/superpowers/plans/2026-10-11-d-tu-frontend-map.md). [CONTRIBUTING](../../CONTRIBUTING.md) and the frontend plan define ownership and PR requirements.

Feature code/tests/e2e and module docs use committed API types. Backend code/contracts, generated `src/types/api.generated.ts`, dependency manifests/lockfiles, root tooling, CI and build/test configuration require separate reviewed contract/tooling changes. A missing package is a tooling prerequisite; do not install it on `feat/web-map`.

Start the mock UI with `npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173`. Canonical checks come from Makefile and include TypeScript/production build. Use loading/error/empty tests and screenshots when UI behavior changes. Verification smoke requires its own servers; port conflicts are blockers.

In an authorized contract PR, `npm --prefix app/frontend run generate:api` generates types from committed OpenAPI. `make contract-check` detects drift. Never hand-edit generated types.
