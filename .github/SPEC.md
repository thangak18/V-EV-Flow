# GitHub Automation Specification

## Pull Request CI

Every PR to `main` runs required jobs named `python-quality`, `python-tests`, `contract-check`, `frontend-quality`, `integration-smoke`, `security`, and `harness-check` (exact list owned by `docs/harness/policy.json`). Jobs install from frozen lockfiles, use no production credentials (the scope job uses a read-only GitHub token), cancel superseded runs, and expose actionable failures.

`contract-check` checks generated OpenAPI with `--check`, lints/diffs it, validates examples, regenerates frontend types, and rejects drift or an unapproved breaking change. `python-quality` includes architecture-boundary enforcement. `integration-smoke` runs only fake/mock adapters. Security checks reject committed secrets and high/critical dependency findings under the documented exception process.

## Main Protection Policy

Observed survey on 11/10/2026: `main` was unprotected and rulesets API unavailable under current plan. Pilot applies the manual merge checklist in `docs/runbooks/branch-protection.md`; policy settings below are not a claim of enforcement.

No direct or force push; PRs require current branch, all checks, at least one non-author approval, stale approval dismissal, resolved conversations, linear history, and squash merge. Routine administrator bypass is disabled. Contract, workflow, and root-tooling changes require code-owner review after verified team GitHub handles are configured.

## PR Evidence and Release

The PR template requires scope, owner, contract impact, test commands/results, data origin, screenshots for UI, limitations, and rollback. Release runs manually or from `demo-v*` tags and packages only a commit already green on `main`; it never embeds repository secrets in artifacts.

Harness CI validates scope with policy/validator from the trusted PR base. Feature changes cannot authorize their own protected-file edits. When the first `codex/harness-bootstrap` PR has no trusted base validator, the CLI reports `result: BLOCKED` (exit 2), technical `checks: PASS`, and blocked scope/Foundation/manual acceptance with `review_ready: false` and exact head/base. Only that complete expected bootstrap result after technical self-checks is classified as a green technical job; CI emits a warning and step summary with the unresolved human checklist. Other failed/blocked/unexpected results fail the job. A push self-check is technical verification and does not approve PR scope. Execution artifacts identify revision and retain logs/traces for 14 days.

Bootstrap landing requires a linked manual scope/policy acceptance record and
non-author human PR approval for the exact current head/base. Foundation snapshot
acceptance is a separate record and gate before opening feature lanes; it may
remain BLOCKED while tooling lands. Bootstrap acceptance cannot supply it.
New commits or a changed base invalidate old acceptance/approval. The observed
unprotected repository cannot enforce those human merge decisions through CI;
the integrator applies the [manual runbook](../docs/runbooks/branch-protection.md).

Local evidence v2 uses a runner-generated checkout-local HMAC seal over execution
metadata and validates log hashes. It detects metadata edits after recording;
the checkout/key remain writable by the operator, so local results are still
self-reported. Independent hosted CI and human AC review remain required. Current
legacy unsealed evidence must be rerun; stale history is retained without using
it for readiness. No local seal certifies human approval or defeats a checkout
owner who can rewrite the runner/key.

Canonical agent assets live under `.agents/`; `.github/scripts/harness_assets.py`
renders tool-specific skills, roles and hooks through `harness.py sync`.
`harness-check` rejects generated drift. Scoped `verify` gates provide
intermediate evidence and do not replace aggregate `make ci` or hosted required
jobs. Session hooks and the heuristic PreToolUse guard are supplementary;
untrusted/unavailable hooks retain the same core scope/evidence/CI gates.
Agent review and QA reports are advisory and cannot supply human approval,
merge or issue closure.
