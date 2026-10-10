# Repository Guidelines

## Project Structure & Module Organization

V-EV Flow is a specification-first scaffold with a Phase 0 mock vertical slice and frozen dependency manifests. All runtime source belongs under `app/`:

- `app/backend/contracts/`: shared DTOs, ports, errors, and generated OpenAPI.
- `app/backend/modules/`: station data/simulation (Bảo), prediction (Thắng), and recommendation (Kiên).
- `app/backend/infrastructure/` and `app/backend/api/`: replaceable adapters, FastAPI, and dependency composition (Kiên).
- `app/frontend/`: React + Vite Driver and Operator interfaces (Tú).
- `.github/`, `deploy/`, and `docs/`: automation, demo packaging, specifications, and plans.

Read `README.md`, `app/SPEC.md`, the nearest module `SPEC.md`, and the relevant implementation plan. Treat `app/backend/contracts`, generated OpenAPI, `docs/DATA_CONTRACT.md`, and `docs/API_CONTRACT.md` as shared interfaces.

## Build, Test, and Development Commands

Prepare local configuration with:

```bash
cp .env.example .env
```

Never commit the resulting `.env`. Canonical checks are `make setup`, `make lint`, `make test`, `make contract-check`, `make smoke`, and `make ci`; `make setup` also installs Chromium for Playwright. Handoff requires a fresh `make ci` exit 0 with clean status.

## Coding Style & Naming Conventions

Use Python 3.11+ in the backend: four-space indentation, type hints, `snake_case` functions/modules, and `PascalCase` classes. Frontend uses two-space indentation, `PascalCase` components, and `useCamelCase` hooks. Modules import shared contracts, not another module's internals. Do not hand-edit generated OpenAPI or TypeScript types.

## Testing Guidelines

Phase 0 provides contract, architecture, unit, integration, and smoke tests with a 75% aggregate coverage gate. Test adapter conformance, simulator seeds, temporal ML splits, API failures, and frontend loading/error/empty states. PRs record exact commands and results.

## Commit & Pull Request Guidelines

Use concise, imperative commit subjects. Only create `feat/data-simulator`, `feat/ml-predict`, `feat/recommend-api`, and `feat/web-map` from the green Phase 0 merge commit.

Keep PRs small. Include owner, scope, contract impact, verification, data origin, limitations, rollback, and UI screenshots. Contract changes use a separate PR and update models, examples, OpenAPI, generated frontend types, tests, and docs together. Never commit partner data, API keys, generated histories, caches, or model binaries.
