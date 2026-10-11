# `app/` agent instructions

Read [root instructions](../AGENTS.md), [application SPEC](SPEC.md), the shared [data contract](../docs/DATA_CONTRACT.md) and [API contract](../docs/API_CONTRACT.md), then the assigned [implementation plan](../docs/superpowers/plans/README.md). Before editing backend/frontend paths, read their `AGENTS.md` and nearest `SPEC.md`.

Runtime source, fixtures, and product tests stay here. [Harness policy](../docs/harness/policy.json) defines the exact owner allowlist and protected paths. Feature owners change their assigned code/tests/docs plus their own `docs/harness/handoffs/<issue>.md`. Shared contracts, generated artifacts, dependencies, root tooling, CI and another owner's module require a separate contract/tooling PR.

Follow the [shared workflow](../docs/harness/workflow.md) and Makefile checks. Do not describe planned behavior or unexecuted checks as completed. Each change must map to issue acceptance criteria and retain limitations/data provenance.
