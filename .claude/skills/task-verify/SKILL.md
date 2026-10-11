---
{
  "name": "task-verify",
  "description": "Verify the current assigned V-EV Flow issue with checks selected from touched packages, focused acceptance tests and revision-bound evidence; run full CI for final handoff."
}
---

<!-- GENERATED from .agents/skills/task-verify/SKILL.md by harness.py sync; edit the canonical source. -->

Read the [workflow](../../../docs/harness/workflow.md) and current issue/handoff.
Use `python3 .github/scripts/harness.py verify --issue N` for intermediate
verification. It selects fixed Make gates from touched paths and consumer
impact; it never executes commands embedded in the issue. These scoped results
do not satisfy the final full-CI gate.

Map every AC to executed behavioral assertions and artifacts. Use the common
`run --issue N --check <check-id> --ac AC-01` runner for explicit AC evidence;
focused test IDs also take the documented `--path`. A listed AC, registry entry
or successful package check alone does not prove an acceptance assertion.

Fix failures under the workflow's repair limit. Preserve `FAIL`, `BLOCKED` and
`NOT RUN` with their reasons, actual command/exit, HEAD/base and artifact hashes.
Do not reuse stale evidence after issue, revision, base or dependency changes.
For UI changes, include the relevant loading/error/empty behavior and a
screenshot or trace when it helps prove the AC.

Commit code and checkpoint before final verification, then use
`python3 .github/scripts/harness.py verify --issue N --full` on the clean
revision. This records fresh `make ci`; required hosted checks and independent
human review still apply. Report the exact revision and remaining blockers.
Optional QA roles run only when requested or justified by the plan, with one
subagent concurrently by default; role availability is not a prerequisite for
the canonical checks.
