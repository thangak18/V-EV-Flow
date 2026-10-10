# Task 6 report — FastAPI composition root and mock endpoints

Implemented the Phase 0 FastAPI factory and composition root in `app/backend/api`.
The application assembles deterministic mock station, prediction, routing, allocation,
simulation, and in-memory request dependencies once at startup. Unsupported `file`,
`real`, `model`, and `goong` selections raise a typed startup configuration error.

Implemented contract routes under `/api`: stations, predict, recommend, pressure,
simulate, reset, health, ready, plus the declared P1 what-if 503 response. Domain
errors map to stable `{code, message, details}` payloads and recommendation retries
are idempotent by request ID.

Verification:

- `uv run pytest -q` — 28 passed
- `uv run ruff check app/backend/api app/backend/tests/api` — clean
- `uv run pyright app/backend/api` — 0 errors

Round 1 follow-up moved recommendation orchestration, idempotency caching, candidate
construction, and ranking behind the composition-root `RecommendationFacade`; the
HTTP handler now delegates only. It also declares OpenAPI domain-error responses and
extends API coverage for idempotency conflicts, reset, backend selection, and error
metadata.

Follow-up verification:

- `uv run pytest -q` — 31 passed
- `uv run ruff check app/backend/api app/backend/tests/api` — clean
- `uv run pyright app/backend/api app/backend/tests/api` — 0 errors
