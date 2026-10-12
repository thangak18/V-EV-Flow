# GitHub Automation Specification

## Pull Request CI

Every PR to `main` runs required jobs named `python-quality`, `python-tests`, `contract-check`, `frontend-quality`, `integration-smoke`, `security` (exact list defined in `.github/workflows/ci.yml`). Jobs install from frozen lockfiles, use no production credentials, cancel superseded runs, and expose actionable failures.

`contract-check` checks generated OpenAPI with `--check`, lints/diffs it, validates examples, regenerates frontend types, and rejects drift or an unapproved breaking change. `python-quality` includes architecture-boundary enforcement. `integration-smoke` runs only fake/mock adapters. Security checks reject committed secrets and high/critical dependency findings under the documented exception process.

## Main Protection Policy

Observed survey on 11/10/2026: `main` was unprotected and rulesets API unavailable under current plan. Pilot applies the manual merge checklist in `docs/runbooks/branch-protection.md`; policy settings below are not a claim of enforcement.

No direct or force push; PRs require current branch, all checks, at least one non-author approval, stale approval dismissal, resolved conversations, linear history, and squash merge. Routine administrator bypass is disabled. Contract, workflow, and root-tooling changes require code-owner review after verified team GitHub handles are configured.

## PR Evidence and Release

The PR template requires scope, owner, contract impact, test commands/results, data origin, screenshots for UI, limitations, and rollback. Release runs manually or from `demo-v*` tags and packages only a commit already green on `main`; it never embeds repository secrets in artifacts.
