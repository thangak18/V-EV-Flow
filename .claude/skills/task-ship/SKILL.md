---
{
  "name": "task-ship",
  "description": "Prepare a draft PR and review evidence for a specific assigned V-EV Flow issue after the human requests shipping, preserving full CI and manual review/merge gates."
}
---

<!-- GENERATED from .agents/skills/task-ship/SKILL.md by harness.py sync; edit the canonical source. -->

Proceed only when the human asks to ship or prepare a PR for the specific
assigned issue. Read the [workflow](../../../docs/harness/workflow.md), issue,
handoff and PR template. Verify scope and finish the implementation and AC
evidence before presenting a concrete result.

Use the canonical `.agents/agents/code-reviewer.md` prompt for a read-only
review against the actual issue and base. If the runtime cannot invoke the
named role, give the same prompt to a read-only subagent or human reviewer.
Record unavailable review as `NOT RUN`; do not fabricate a verdict. Fix actual
blocking findings and rerun affected checks. An agent's review findings or
`APPROVE` never count as the required non-author human approval.

Stage only issue files and commit code plus the checkpoint. Run
`python3 .github/scripts/harness.py verify --issue N --full` on the clean
revision, then `python3 .github/scripts/harness.py ready --issue N`. Keep the
final evidence outside tracked logs so recording PASS does not create a new
untested revision. If the result is partial or blocked, report that checkpoint
and the next step rather than calling it review-ready.

Under the human's shipping request, push the policy branch and create or update
a draft PR using `.github/pull_request_template.md`: owner/scope, contract and
data impact, AC evidence, exact HEAD/base and commands/results, hosted CI links,
screenshots when relevant, limitations and rollback. Use a body file for
multiline PR text. Additional GitHub comments/labels require the human's
authorization. The human independently reviews and the integrator decides
merge; do not merge, approve, close issues or start another task automatically.
