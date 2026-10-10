# Phase 0 foundation handoff

This runbook is the handoff gate between the reviewed foundation and the four owner branches. Keep the foundation merge commit immutable: every owner branch must start from the exact SHA recorded below.

## Reading order

1. [`README.md`](../../README.md) for project status and verified commands.
2. [`AGENTS.md`](../../AGENTS.md), then [`app/AGENTS.md`](../../app/AGENTS.md).
3. The nearest [`SPEC.md`](../../app/SPEC.md), [`app/backend/SPEC.md`](../../app/backend/SPEC.md), or [`app/frontend/SPEC.md`](../../app/frontend/SPEC.md).
4. [`docs/DATA_CONTRACT.md`](../DATA_CONTRACT.md), [`docs/API_CONTRACT.md`](../API_CONTRACT.md), and the assigned plan in [`docs/superpowers/plans/`](../superpowers/plans/).
5. This runbook and the [branch-protection checklist](branch-protection.md).

## Scope and ownership

The foundation owns shared contracts, generated OpenAPI/types, dependency injection, mock adapters, CI, and canonical commands. After handoff, owners work only in these paths:

| Owner | Branch | Feature path | Plan |
| --- | --- | --- | --- |
| Bảo | `feat/data-simulator` | `app/backend/modules/station_data`, `app/backend/modules/simulation` | [A](../superpowers/plans/2026-10-11-a-bao-data-simulation.md) |
| Thắng | `feat/ml-predict` | `app/backend/modules/prediction` | [B](../superpowers/plans/2026-10-11-b-thang-ml-prediction.md) |
| Kiên | `feat/recommend-api` | `app/backend/modules/recommendation`, `app/backend/infrastructure/**`, `app/backend/api/dependencies.py`, and the scoped route files/tests listed in plan C | [C](../superpowers/plans/2026-10-11-c-kien-backend-recommendation.md) |
| Tú | `feat/web-map` | `app/frontend/src` and frontend tests/e2e | [D](../superpowers/plans/2026-10-11-d-tu-frontend-map.md) |

Feature branches must not edit `app/backend/contracts`, `app/backend/contracts/openapi.yaml`, `app/frontend/src/types/api.generated.ts`, Make targets, lockfiles, CI, or another owner's path. Kiên's route/dependency edits are limited to the files explicitly listed in plan C. Submit a separate reviewed contract/tooling PR when an interface must change.

## Fresh-checkout verification

From a clean checkout or disposable worktree, run exactly:

```bash
make setup
make ci
git status --short
```

`make setup` installs the frozen Python/frontend dependencies and the Chromium browser used by Playwright smoke tests. `make ci` runs `make lint`, `make test`, `make contract-check`, `make smoke`, and security checks. The handoff gate is exit code 0 for every command and no output from `git status --short`; the current checkout meets that gate. Redocly emits seven non-fatal contract warnings; attach the complete green output to the Foundation PR.

The repository must also retain no obsolete runtime roots:

```bash
test ! -e api && test ! -e sim && test ! -e ml && test ! -e web && test ! -e data
```

The mock vertical slice is available for a smoke screenshot with:

```bash
uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000
npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173
```

Check `GET http://127.0.0.1:8000/api/health` and capture the frontend at `http://127.0.0.1:5173/`. These are the only documented mock start commands.

## OpenAPI and generated types

Pydantic/FastAPI contracts are the source. Run `make contract-check` to generate and validate `app/backend/contracts/openapi.yaml`, lint it, generate `app/frontend/src/types/api.generated.ts`, and fail if generated output is dirty. Never hand-edit either generated artifact. A contract PR includes the model/route change, examples, generated artifacts, tests, and consumer impact in one reviewable change.

## Integrator handoff

1. Review the Foundation PR with the complete `make ci` output, OpenAPI/type-generation proof, mock UI screenshot, known limitations, and branch-protection checklist.
2. Merge that reviewed PR into `main` only after all checks are green and approval is recorded.
3. Immediately record the foundation merge SHA:

   ```bash
   git rev-parse HEAD
   ```

   Save the resulting full SHA in the Foundation PR and this handoff record.
4. Enable branch protection on `main` using [`branch-protection.md`](branch-protection.md), requiring the CI checks and review policy.
5. Create all four owner branches from that exact SHA, not from a moving `main` or an unreviewed local commit:

   ```bash
   git switch -c feat/data-simulator <foundation-merge-sha>
   git switch -c feat/ml-predict <foundation-merge-sha>
   git switch -c feat/recommend-api <foundation-merge-sha>
   git switch -c feat/web-map <foundation-merge-sha>
   ```

Do not create or distribute those branches until the Foundation PR is green, approved, and merged. Record the SHA, branch-protection result, and each branch creation in the integration log.
