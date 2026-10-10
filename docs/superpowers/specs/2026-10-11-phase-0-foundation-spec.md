# Phase 0 Foundation Specification

## Purpose

Phase 0 converts the documentation-only repository into a safe, runnable baseline. It is implemented once, reviewed, and merged into `main` before Bảo, Thắng, Kiên, or Tú creates a domain feature branch. The module specs may be read immediately; their implementation is gated on this merge.

## Ownership and Review

A dedicated foundation agent may implement the work. Kiên acts as integrator because C owns the composition root. At least one non-author teammate reviews the PR. No owner implements domain algorithms in this PR, and no feature branch is based on the old scaffold.

## Required Deliverables

- Confirm the obsolete root module placeholders remain absent and build only in the approved `app/backend` and `app/frontend` modular-monolith layout.
- Add scoped `AGENTS.md` instructions that point agents to the existing module `SPEC.md` files without duplicating them.
- Add Python 3.11 project metadata, frozen dependency lock, Node package/lock files, formatter/linter/test configuration, and canonical Make targets.
- Implement strict shared Pydantic DTOs, enums, errors, and ports matching the approved data/API contracts.
- Add deterministic, small, source-labelled JSON fixtures suitable for CI.
- Add settings and dependency injection with mock repositories, fake predictor, fake route provider, fake simulation runner, and in-memory allocation store.
- Add mock FastAPI endpoints and deterministically generated `app/backend/contracts/openapi.yaml`.
- Generate frontend HTTP types from OpenAPI and render one fixture station with a visible `mock` label in a minimal React shell.
- Add contract, adapter, architecture, backend, frontend, and end-to-end smoke tests.
- Add required CI/release workflow definitions, PR template, ownership policy, and documented `main` protection settings.
- Update root and module documentation so only verified commands are described as runnable.

## Required Commands

The implementation defines stable commands equivalent to `make setup`, `make format`, `make lint`, `make test`, `make contract-check`, `make smoke`, and `make ci`. Exact underlying tool invocations live in repository configuration; all developer and CI paths call the same commands.

## Explicit Exclusions

Do not add simulation physics, model training, real prediction, Goong calls, final ranking/allocation, pressure calculations, complete Driver/Operator UI, database server, or production deployment. The mock slice proves wiring and compatibility only.

## Exit Criteria and Branch Gate

Phase 0 is complete when a fresh clone can install from frozen locks, run all canonical checks without secrets, regenerate OpenAPI/frontend types with no diff, start the mock backend/frontend, and pass the fixture-to-UI smoke path. All required GitHub checks are green, the PR is approved, and the merge commit is recorded in the team handoff.

Only then are the four branches created from that exact commit:

- `feat/data-simulator` — Bảo
- `feat/ml-predict` — Thắng
- `feat/recommend-api` — Kiên
- `feat/web-map` — Tú

If Phase 0 later requires a contract correction, it is merged as a shared contract PR first; each feature branch rebases before consuming the new interface.
