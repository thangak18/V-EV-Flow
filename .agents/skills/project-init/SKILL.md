---
{"name":"project-init","description":"Onboard a teammate or a fresh checkout to V-EV Flow: locate repository instructions, inspect frozen setup prerequisites and explain the shared issue workflow."}
---

Read `README.md`, `AGENTS.md`, `app/SPEC.md` and the
[harness walkthrough](../../../docs/harness/RUN_AN_ISSUE.md). Run
`python3 .github/scripts/harness.py doctor` and report actual missing tools,
Foundation review status and runtime limits. When setup is requested, use
`make setup` for frozen dependencies and the documented local `.env.example`
copy; never commit local environment files.

Check canonical assets with `python3 .github/scripts/harness.py sync --check`
and `python3 .github/scripts/harness.py self-check`. Do not regenerate files
outside an assigned tooling task. Tool-specific trust, login and model choices
belong to the user; installed files or versions do not prove runtime discovery.

Explain how a human supplies an assigned issue, lane and reviewer, and how
portable snapshots, handoff and revision-bound evidence support resume. Point
to [compatibility](../../../docs/harness/compatibility.md) for real probe
statuses. This onboarding skill does not create a backlog, issues, assignments,
branches, credentials or global configuration. Leave a concise setup result and
the next concrete step; blocked feature prerequisites do not block read-only
onboarding.
