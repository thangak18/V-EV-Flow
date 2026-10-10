# Task 2 report: validated settings and adapter selection

## Files

- Added `app/backend/core/__init__.py` with settings exports.
- Added `app/backend/core/settings.py` with typed backend selectors, environment-backed settings, cross-field validation, and cached `get_settings()`.
- Added `app/backend/tests/core/test_settings.py` covering mock defaults, Goong key validation, and cache identity.
- Added backend selector defaults to `.env.example`.

## Verification

- `uv run pytest app/backend/tests/core/test_settings.py -v` — failed during collection with `ModuleNotFoundError: No module named 'app'` in this worktree environment.
- `PYTHONPATH=. uv run pytest app/backend/tests/core/test_settings.py -v` — 3 passed.
- `PYTHONPATH=. uv run ruff check app/backend/core app/backend/tests/core/test_settings.py` — All checks passed.
- `PYTHONPATH=. uv run pyright app/backend/core app/backend/tests/core/test_settings.py` — 0 errors, 0 warnings, 0 informations.
- `PYTHONPATH=. uv run pytest app/backend/tests -q` — 4 passed.

## Self-review

- Selector fields use the required literal values and defaults.
- Goong routing requires a non-empty REST key; model prediction requires an existing model directory.
- Settings are loaded from `.env` with unknown variables ignored and are cached through `get_settings()`.
- No contract, API, infrastructure, CI, or later-task files were changed.

## Concerns

- The brief's exact pytest command does not place the repository root on `sys.path` in this environment; all focused and full-suite checks pass with `PYTHONPATH=.`.
