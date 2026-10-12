# Repository Guidelines

V-EV Flow is a specification-first modular monolith with a Phase 0 mock vertical slice and frozen dependencies. Runtime source, fixtures, and product tests belong under `app/`; automation belongs under `.github/`, deployment under `deploy/`, and durable specifications under `docs/`.

## Read before editing

Read `README.md`, `app/SPEC.md`, every `AGENTS.md` applying to the paths you will change, the nearest module `SPEC.md`, and the assigned owner plan. Starting at the root does not guarantee that subtree instructions have been loaded. Shared interfaces are `app/backend/contracts`, generated OpenAPI/types, `docs/DATA_CONTRACT.md`, and `docs/API_CONTRACT.md`.

## Build and verification

Copy `.env.example` to `.env` locally; never commit `.env`. Install frozen dependencies with `make setup`. Makefile defines checks: `lint`, `test`, `build`, `contract-check`, `smoke`, `security`, and aggregate `ci`. Use focused module tests during development and a fresh `make ci` before a completed handoff. Record executed commands, results, tested HEAD/base and logs; use `NOT RUN` or `BLOCKED` for checks without successful execution. A completed handoff requires fresh `make ci` exit 0 on a clean revision; a partial checkpoint must be labeled partial.

## Style and boundaries

Python 3.11+: four spaces, type hints, `snake_case` functions/modules, `PascalCase` classes. Frontend: two spaces, `PascalCase` components, `useCamelCase` hooks. Modules import shared contracts rather than another module's internals. Do not hand-edit generated OpenAPI or TypeScript types. Test meaningful success/failure behavior, adapter conformance, seeds, temporal splits, API failures, and UI loading/error/empty states; preserve the 75% aggregate coverage gate.

## Collaboration and review

Keep four owner branches: `feat/data-simulator`, `feat/ml-predict`, `feat/recommend-api`, `feat/web-map`, originating at the accepted Foundation snapshot in `docs/runbooks/phase-0-handoff.md`. Coordinate one writer per owner branch. Tooling and contract changes use separate `codex/` branches and reviewed PRs. Integrate prerequisites from `main` by merge; do not force-push or reset another person's work.

Use concise imperative commit subjects and small PRs. Include owner, AC evidence, scope, contract impact, data origin, limitations, rollback, and screenshots for UI. Contract changes update models, examples, generated artifacts, tests, and docs in one separate reviewed PR. Humans assign issues, start sessions, independently review, and decide merge; never fabricate approval. Never commit credentials, partner data, generated histories, caches, model binaries, or local test logs.
