---
{
  "name": "task-start",
  "description": "Start or resume a specific human-assigned V-EV Flow issue, validate its snapshot and prerequisites, and prepare a scoped plan and portable checkpoint."
}
---

<!-- GENERATED from .agents/skills/task-start/SKILL.md by harness.py sync; edit the canonical source. -->

Proceed only when the human requests starting or resuming a specific assigned
issue. Do not select a task, claim it or create a branch. Read `AGENTS.md`, the
[workflow](../../../docs/harness/workflow.md), applicable subtree instructions,
nearest SPEC/contracts and owner plan. The existing checkout must use the lane
and origin defined by policy.

Run `python3 .github/scripts/harness.py doctor`, then
`python3 .github/scripts/harness.py start --issue N --tool <codex-or-claude> --surface <actual-surface>`.
Use the actual issue number or URL in place of `N`; use the workflow's base and
bootstrap options when applicable. Follow reported blockers; a local snapshot
does not prove GitHub readiness. Resume compares the current issue/hash,
branch, HEAD, diff, base and dependencies with the tracked handoff before edits.

Prepare a short plan: allowed files, AC-to-check/artifact mapping, data origin,
contract impact, unresolved decisions and next step. Use
`python3 .github/scripts/harness.py handoff --issue N` for an initial template,
then maintain that issue's checkpoint according to the workflow. Do not post a
GitHub comment unless the human asked for it. An optional hook canary diagnoses
one PreToolUse observation; unavailable hooks do not block the core workflow.
