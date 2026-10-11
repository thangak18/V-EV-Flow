# `main` merge gate and protection runbook

## Observed enforcement

On 11/10/2026 survey, GitHub branch API returned `protected: false`; rulesets API returned 403 requiring a plan change or public repository. Required settings below are policy, not a claim that GitHub currently enforces them. Do not change repository visibility or subscription automatically. Pilot uses the manual checklist until an authorized maintainer can enable protection.

The source of exact required check names is [harness policy](../harness/policy.json); Makefile/workflows define execution. Keep that authority synchronized in tooling review.

## Manual merge checklist — pilot

Integrator records in the PR on its latest head and integration base:

- Fresh local `make ci` exit 0 at exact clean HEAD; all required GitHub jobs green for that revision/base.
- Scope validated against trusted base policy; AC mapped to current evidence, no stale/missing logs; source/limitations/rollback/handoff complete.
- At least one non-author human PR approval on exact latest head/base, linked with reviewer handle and review URL; stale approvals re-requested after new commits or base changes.
- All conversations resolved; branch contains current prerequisites/base; no conflicting owner lane work.
- Squash merge manually. Never force-push, bypass checks or invent independent review. Confirm merge before declaring merged/closing issue.

A script reports local readiness; it cannot approve a PR or certify that hosted protections are enabled.

## First harness bootstrap: explicit manual acceptance

When the PR base has no trusted harness validator, `codex/harness-bootstrap`
cannot receive automated policy/scope approval from its own new validator.
After technical self-checks pass, `ci` reports `result: BLOCKED` with exit 2,
`checks: PASS`, `mode: bootstrap`, blocked `scope`, `foundation_review` and
`manual_acceptance`, `review_ready: false`, and exact PR head/base. The workflow
recognizes only this complete expected result as a green technical job and adds
a warning/checklist to the step summary. Other blocked/failing/unexpected
results fail CI. A green bootstrap job leaves the human gate unresolved.

Before landing, the integrator links these separate human records on the PR:

- A non-author human PR approval for the exact current head and integration base.
- Manual scope/policy acceptance naming reviewer, head, base and reviewed diff:
  protected paths, initial owner policy, validator/workflow behavior, AC evidence,
  limitations and rollback. Keep the machine scope artifact BLOCKED; this record
  supplies human acceptance rather than retroactive automated PASS.

Foundation acceptance may remain BLOCKED while bootstrap tooling lands after
manual scope/policy acceptance, non-author human PR approval and all technical
gates. Before opening feature lanes, obtain separate independent Foundation
snapshot acceptance naming its immutable policy SHA and evidence/review link.
Bootstrap scope acceptance or approval of another head cannot substitute for
that Foundation gate.

New commits or a changed base invalidate prior approval/manual acceptance; obtain
fresh records and checks for the final revision. Do not fabricate acceptance in
policy, infer it from CI/agent output or merge bootstrap while its manual
scope/policy acceptance, non-author PR approval or technical gates are missing.
The repository is currently unprotected, so CI cannot enforce that the human
integrator follows this checklist. This PR remains unmerged until the human
decides and confirms landing.

Local evidence v2 has a checkout-local HMAC seal to detect metadata edits and
log hashes to detect changed output. The same operator can modify the runner,
checkout and key, so its trust is **self-reported**. Independent hosted execution
and human AC review are still required; local `ready` does not supply PR approval
or `review_ready`. Current legacy unsealed evidence must be rerun; stale history
is preserved without counting toward readiness.

## Required GitHub settings when available

Require PR, one non-author approval, stale dismissal, resolved conversations, branches up to date and every policy required job. Require linear history, allow squash merge only, disable force pushes/deletion and routine admin bypass. Verify changes using GitHub API/UI and attach actual evidence before marking protection active.

Code-owner review can be enforced only after relevant verified handles include a non-author maintainer. The existing `@thangak18` entry is not proof that an independent reviewer is available. Configure handles through a reviewed tooling PR.

## Security exception process

The sole baseline false-positive added by harness bootstrap is the exact hash of
Foundation's public Git commit SHA in `docs/harness/policy.json`. It is marked
`is_secret: false` in `.secrets.baseline`; no path or detector is excluded.
New or changed values remain scanned, and the injected-secret regression must fail
as expected. This is not an advisory/dependency exception.

No blanket allowlist. Temporary exception is approved in PR with advisory/package/version, real owner handle, rationale, expiry (maximum 30 days), mitigation and evidence. Remove or renew with fresh evidence before expiry; do not use it to bypass `security`.

## Contract and release checks

`contract-check` checks generated OpenAPI, lints it and checks frontend types drift. CI also compares breaking changes with committed base using oasdiff. Initial artifact introduction may skip only breaking comparison when no historical schema exists; subsequent changes use normal comparison.

Manual/`demo-v*` release packages a green `main` SHA, labels artifact with SHA, excludes credentials and requires manual publication approval. Logs/traces retention is 14 days; PR summary remains durable.
