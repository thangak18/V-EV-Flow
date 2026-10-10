# V-EV Flow Implementation Plan Index

## Mandatory Execution Order

1. Execute [Phase 0 Foundation](2026-10-11-phase-0-foundation.md) on a dedicated foundation branch.
2. Merge the green, reviewed Foundation PR and record its merge SHA.
3. Create all four owner branches from that exact SHA.
4. Execute the four owner plans in parallel:
   - Bảo on `feat/data-simulator`: [Data and Simulation](2026-10-11-a-bao-data-simulation.md)
   - Thắng on `feat/ml-predict`: [ML Prediction](2026-10-11-b-thang-ml-prediction.md)
   - Kiên on `feat/recommend-api`: [Backend Recommendation](2026-10-11-c-kien-backend-recommendation.md)
   - Tú on `feat/web-map`: [Frontend and Map](2026-10-11-d-tu-frontend-map.md)
5. After all four PRs are green, execute [Integration, Demo, and Release](2026-10-11-integration-demo-release.md).

No feature owner may skip the Foundation gate or create a private replacement for contracts, fixtures, OpenAPI, CI, or canonical commands.

## Agent Handoff

Each worker receives exactly one plan plus the specs linked from its header. The worker must use `superpowers:subagent-driven-development` or `superpowers:executing-plans`, track every checkbox, follow red-green-refactor, and stop for a separate contract PR rather than editing protected shared files.

Kiên is integration owner. A↔B review data/labels/evaluation; C↔D review OpenAPI/UI behavior. Required PR evidence and verification commands are part of each plan, not optional handoff notes.
