# V-EV Flow Implementation Plan Index

## Mandatory Execution Order

1. Execute [Phase 0 Foundation](2026-10-11-phase-0-foundation.md) on a dedicated foundation branch.
2. Independently review and accept the historical Foundation snapshot recorded in [runbook](../../runbooks/phase-0-handoff.md); the record includes independent human acceptance. Integrate reviewed tooling prerequisites.
3. Create owner branches from the accepted Foundation origin in the [handoff runbook](../../runbooks/phase-0-handoff.md), then merge integration prerequisites from `main`.
4. Execute the four owner lanes concurrently, one issue/writer per lane:
   - Bảo on `feat/data-simulator`: [Data and Simulation](2026-10-11-a-bao-data-simulation.md)
   - Thắng on `feat/ml-predict`: [ML Prediction](2026-10-11-b-thang-ml-prediction.md)
   - Kiên on `feat/recommend-api`: [Backend Recommendation](2026-10-11-c-kien-backend-recommendation.md)
   - Tú on `feat/web-map`: [Frontend and Map](2026-10-11-d-tu-frontend-map.md)
5. After all four PRs are green, execute [Integration, Demo, and Release](2026-10-11-integration-demo-release.md).

No feature owner may skip the Foundation gate or create a private replacement for contracts, fixtures, OpenAPI, CI, or canonical commands.

## Agent Handoff

Each worker receives exactly one plan plus the specs linked from its header. The worker follows applicable AGENTS/SPEC, CONTRIBUTING and the assigned plan, tracks checkboxes as implementation notes, verifies behavior with relevant tests, and stops for a separate contract/tooling PR rather than editing protected files. No personal plugin is required.

Kiên is integration owner. A↔B review data/labels/evaluation; C↔D review OpenAPI/UI behavior. Required PR evidence and verification commands are part of each plan, not optional handoff notes.

Dependency additions (including frontend router/map SDK) require separate tooling issues/PRs before feature work consumes them. CONTRIBUTING.md and applicable AGENTS define owner boundaries; Makefile and CI define current checks. Historical plan shell snippets do not override these rules.
