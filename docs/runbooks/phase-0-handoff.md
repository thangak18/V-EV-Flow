# Phase 0 foundation handoff

Foundation origin is immutable and defined in [harness policy](../harness/policy.json). Owner branches may open only after independent human acceptance; a successful CI run does not create review evidence.

## Foundation record — 11/10/2026

- Snapshot: `27d421265fe57736d3070c241544e3756772e52b` (historical `main` HEAD at survey).
- Historical CI: [run 38104753710](https://github.com/thangak18/V-EV-Flow/actions/runs/38104753710), success on that SHA with the original six jobs.
- Independent human acceptance: **PASS**, reviewer @thangak18 (non-author; snapshot author/committer TKin), 11/10/2026. [Explicit decision](https://github.com/thangak18/V-EV-Flow/issues/3#issuecomment-6109920471), recorded by Codex on behalf of the human reviewer after confirmation.
- [Technical review](https://github.com/thangak18/V-EV-Flow/issues/3#issuecomment-6109894510): fresh clean-checkout `make setup` and `make ci` PASS on the immutable snapshot; 58 backend tests, 12 frontend tests and 1 E2E. Acceptance includes the disclosed mock/scaffold limitations; it does not certify production algorithms or live-data accuracy.
- Foundation PR/merge approval history: not found in survey; do not fabricate an approved Foundation PR.
- GitHub enforcement survey: branch `protected: false`; rulesets API 403 requiring plan/public-repo change. Manual merge gate applies until protection is actually available.
- Verification of later tooling/feature revisions remains separate and must attach its own exact-head/base evidence. Foundation acceptance does not approve those PRs.

A non-author reviewer must inspect this snapshot, run/view fresh gate evidence and explicitly accept it. Integrator then updates Foundation review status/reviewer/evidence in policy through a tooling PR. This approval is not something an agent can supply for the human.

## Reading and ownership

Read [README](../../README.md), applicable AGENTS, nearest SPEC, [data contract](../DATA_CONTRACT.md), [API contract](../API_CONTRACT.md), assigned [owner plan](../superpowers/plans/README.md), [harness workflow](../harness/workflow.md), and [merge gate](branch-protection.md).

Exact owner paths, branch names, Foundation origin and gates have one authority: [policy](../harness/policy.json). Bảo owns station data/simulation, Thắng prediction, Kiên recommendation/scoped infrastructure/API, Tú frontend. Feature lanes cannot change shared models/generated artifacts, dependencies/tooling/CI or other owners' paths. Contract/tooling prerequisites use separate PRs.

One issue and one writer per lane; issue assignee/integrator coordinate across machines. The initial owner branch originates at accepted Foundation SHA; integration base advances as tooling/contract prerequisites merge. Update by merging `main`, never force-push or discard other work.

## Fresh-checkout verification

```bash
make setup
make ci
git status --short
```

Setup installs frozen Python/npm locks and Chromium. Aggregate checks come from Makefile, including build and harness checks. All commands must exit 0 and final status be empty for complete handoff. Existing warning summaries are historical observations, not an allowance for failures. Attach full result/log to exact tested SHA/base; record BLOCKED/NOT RUN when not executed.

The mock vertical slice starts with:

```bash
uv run uvicorn app.backend.api.main:create_app --factory --host 127.0.0.1 --port 8000
npm --prefix app/frontend run dev -- --host 127.0.0.1 --port 5173
```

Check `/api/health`, capture frontend `/`. Stop those development servers before verification smoke; smoke cannot reuse servers from a different checkout.

## Generated contracts

Only in a reviewed contract PR, regenerate from Pydantic/FastAPI:

```bash
uv run python -m app.backend.api.generate_openapi
npm --prefix app/frontend run generate:api
make contract-check
```

The first command writes OpenAPI; `make contract-check` invokes it with `--check` to detect drift, lints and checks frontend generation. Do not hand-edit either artifact. Include models/examples/generated artifacts/tests/docs and consumer impact together.

## Integrator opening checklist

1. Get independent Foundation snapshot acceptance and record real reviewer/evidence/date in policy.
2. Verify harness bootstrap/tooling PR checks/review, merge manually; no self-approved completion.
3. Create four owner branches at policy Foundation origin, then merge accepted prerequisites from `main`. Record both origin and integration base.
4. Assign one issue/writer per lane, confirm scopes/dependencies and reviewer.
5. For each PR, apply [manual merge checklist](branch-protection.md); update enforcement record only after actual GitHub settings are verified.
