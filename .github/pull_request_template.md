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
- [ ] New commits or base/dependency changes received fresh verification

Self-reported evidence is supplemented by independently executed CI. Logs/traces
have 14-day retention; keep the result summary and tested SHA in this PR.

## Data origin

Describe fixture, synthetic, or approved external data used (and confirm no secrets or partner data are committed):

## Limitations and rollback

- Known limitations:
- Rollback plan:

## UI evidence

For UI changes, attach screenshots or a short recording. Write “Not applicable” otherwise.

## Independent review and manual merge

- [ ] AC behavior, verification, scope, reliability, maintainability and handoff reviewed
- [ ] No required check is FAIL, BLOCKED or NOT RUN on the final revision
- [ ] Non-author approval and resolved conversations checked by integrator
- [ ] Integrator inspected latest head/base and every check in `docs/harness/policy.json`

Only the integrator confirms merged/closed. Bootstrap is a documented exception:
the first harness PR has no trusted base validator and needs explicit manual
policy/scope review; it does not establish Foundation approval or pilot PASS.
