# Canonical agent assets

Edit shared skills and roles here. The [workflow](../docs/harness/workflow.md)
and [policy](../docs/harness/policy.json) remain authoritative for issue work,
scope, branches and gates; assets route to them.

| Source | Consumption |
| --- | --- |
| `skills/<name>/SKILL.md` | Codex reads directly; generated into `.claude/skills/` |
| `skills/<name>/agents/openai.yaml` | Codex invocation policy; explicit-only maps to Claude metadata |
| `agents/<name>.md` | Generated into `.claude/agents/*.md` and `.codex/agents/*.toml` |
| `hooks.json` | Generated into `.claude/settings.json` hooks and `.codex/hooks.json` |

Canonical frontmatter uses a JSON object between `---` delimiters (valid YAML).
Skills use standard Agent Skills fields; roles have `name`, `description` and
provider settings. Role instructions are shared, model selection inherits the
session, and review roles are read-only. A generated role file does not prove
that a particular runtime can invoke that role.

After an authorized tooling change, run
`python3 .github/scripts/harness.py sync`, then
`python3 .github/scripts/harness.py sync --check` and the canonical checks.
Commit source and generated assets together. Do not hand-edit generated skills,
agents or hook definitions; the generator preserves unrelated Claude settings.
Generation and drift checking live in `.github/scripts/harness_assets.py`.

`project-init` handles onboarding. `task-start`, `task-verify` and `task-ship`
provide discoverable stages of the shared issue workflow. Start/ship require a
specific assigned issue and the human's request for that action. `vev-issue`
remains an explicit-only entry point for the whole workflow. None of these
assets assigns work, creates owner branches, merges PRs or closes issues.

Hooks provide session context and a supplementary heuristic guard. Missing or
untrusted hooks do not prevent the core CLI/workflow from running. See the
[human walkthrough](../docs/harness/RUN_AN_ISSUE.md),
[compatibility record](../docs/harness/compatibility.md) and
[LMAO adaptation](../docs/harness/lmao-reference.md).
