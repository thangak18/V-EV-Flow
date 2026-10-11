# Task 5 report — deterministic mock adapters

Implemented fixture-backed station/status repositories, deterministic route,
prediction, allocation, and simulation fakes, plus an in-memory allocation
store. Added reusable station repository conformance coverage and adapter tests.

Verification:

- `uv run pytest -q` — 24 passed
- `uv run pytest app/backend/tests/conformance app/backend/tests/infrastructure -v` — 5 passed
- `uv run ruff check app/backend/infrastructure app/backend/tests/conformance app/backend/tests/infrastructure` — passed
- `uv run pyright app/backend/infrastructure app/backend/tests/conformance app/backend/tests/infrastructure` — 0 errors, 0 warnings
