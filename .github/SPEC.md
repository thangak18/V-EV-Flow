# GitHub Automation Specification

## Pull Request CI

Every PR to `main` runs required jobs named `python-quality`, `python-tests`, `contract-check`, `frontend-quality`, `integration-smoke`, and `security`. Jobs install from frozen lockfiles, use no real credentials, cancel superseded runs, and expose actionable failures.

`contract-check` regenerates/lints/diffs OpenAPI, validates examples, regenerates frontend types, and rejects drift or an unapproved breaking change. `python-quality` includes architecture-boundary enforcement. `integration-smoke` runs only fake/mock adapters. Security checks reject committed secrets and high/critical dependency findings under the documented exception process.

## Main Protection

No direct or force push; PRs require current branch, all checks, at least one non-author approval, stale approval dismissal, resolved conversations, linear history, and squash merge. Routine administrator bypass is disabled. Contract, workflow, and root-tooling changes require code-owner review after verified team GitHub handles are configured.

## PR Evidence and Release

The PR template requires scope, owner, contract impact, test commands/results, data origin, screenshots for UI, limitations, and rollback. Release runs manually or from `demo-v*` tags and packages only a commit already green on `main`; it never embeds repository secrets in artifacts.
