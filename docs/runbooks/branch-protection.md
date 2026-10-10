# `main` branch protection runbook

Configure repository settings before the Phase 0 pull request is merged. The
settings below are the source of truth for the required merge gate.

## Required pull-request settings

- Require a pull request; require at least **one approval from a non-author**.
- Dismiss stale approvals when new commits are pushed.
- Require all conversations to be resolved.
- Require branches to be up to date before merging.
- Require these status checks (exact job names):
  - `python-quality`
  - `python-tests`
  - `contract-check`
  - `frontend-quality`
  - `integration-smoke`
  - `security`
- Require linear history and allow **squash merge** only.
- Do not allow force pushes or branch deletion.
- Do not permit routine administrator bypasses; emergency bypasses must be
  recorded in the incident log and followed by a corrective PR.

GitHub's **Require review from Code Owners** remains off while `@thangak18` is
the only verified owner. Turn it on only after a second non-author maintainer
handle is verified and added to the relevant entries in `.github/CODEOWNERS`.

## Security exception process

Security checks have no blanket allow-list. A temporary exception must be
approved in a pull request and include all of the following:

```text
Advisory: GHSA-... / package and version
Owner: @verified-handle
Rationale: why remediation cannot land now
Expiry: YYYY-MM-DD (maximum 30 days)
Mitigation: concrete monitoring or compensating control
```

The exception is removed or renewed with fresh evidence before its expiry;
expired exceptions fail review and cannot be used to bypass `security`.

## Release gate

The release workflow is manual or `demo-v*` tag driven. It packages only the
frontend demo artifact after `make ci` passes, identifies it with
`GITHUB_SHA`, and never reads production credentials or deploys externally.

