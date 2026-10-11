Harness-Issue: REPLACE_WITH_ISSUE_NUMBER

## Owner and scope

- Owner:
- Scope (what changed and why):
- Owner lane / integration base SHA:
- Handoff: `docs/harness/handoffs/<issue>.md`
- [ ] One writer on this owner lane; changes match issue scope

## Contract impact

- [ ] No contract impact
- [ ] Contracts/OpenAPI changed (linked contract PR and regenerated artifacts):

## Verification

Commands run and results:

```text
make ci
```

| AC ID / gate | Exact command | PASS / FAIL / BLOCKED / NOT RUN | Tested SHA | Evidence link |
| --- | --- | --- | --- | --- |
| AC-01 | | NOT RUN | | |
| Full gate | make ci | NOT RUN | | |

- Tool / version / surface:
- Clean `git status --short` at tested SHA:
- CI run / SHA (include PR head and merge-test identity if different):
- Final PR head SHA / current integration base SHA:
- Local evidence version / runner seal validation result (`schema_version: 2`):
- [ ] New commits or base/dependency changes received fresh verification

Local evidence remains self-reported. The runner's checkout-local HMAC seal
detects metadata edits, but the operator can rewrite the checkout/key. Current
unsealed legacy records require rerunning checks. Independently executed CI and
human AC review supplement local evidence; local `ready` does not establish
`review_ready`. Logs/traces have 14-day retention; keep the result summary and
exact tested head/base in this PR. Never include the local evidence key.

## Data origin

Describe fixture, synthetic, or approved external data used (and confirm no secrets or partner data are committed):

## Limitations and rollback

- Known limitations:
- Rollback plan:

## UI evidence

For UI changes, attach screenshots or a short recording. Write “Not applicable” otherwise.

## Independent review and manual merge

- [ ] AC behavior, verification, scope, reliability, maintainability and handoff reviewed
- [ ] No required technical check is FAIL, BLOCKED or NOT RUN on the final revision
- [ ] Non-author human PR approval on exact current head/base and resolved conversations checked by integrator
- [ ] Integrator inspected latest head/base and every check in `docs/harness/policy.json`
- Human reviewer / PR approval URL / approved head SHA / recorded base SHA:
- Manual scope/policy acceptance record URL / reviewer / accepted head and base (required for first bootstrap):
- Separate Foundation snapshot acceptance record URL / immutable Foundation SHA (or BLOCKED):
- [ ] Old approval/manual acceptance re-requested after any new commit or base change

Only the integrator confirms merged/closed. Bootstrap is a documented exception:
the first harness PR has no trusted base validator. Its technical job can be
green while automated scope, Foundation acceptance and manual acceptance remain
BLOCKED and `review_ready: false`. Before landing, link a non-author human's
manual scope/policy acceptance for the exact head/base and non-author PR approval;
all technical gates must pass. Record Foundation status separately: it may remain
BLOCKED for tooling landing, but independent snapshot acceptance is required
before opening feature lanes. Green CI, a checkbox or an agent verdict cannot
supply human acceptance records.
Do not relabel the blocked automated scope as PASS. No bootstrap approval
establishes Foundation approval or pilot PASS.
