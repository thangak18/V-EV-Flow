# Task 10 Report: CI, Release, and Architecture Gates

Implemented the required CI/release checks, PR policy, ownership policy,
branch-protection runbook, and architecture boundary guard.

## Fix round 1

- Replaced the invalid generic oasdiff action with
  `oasdiff/oasdiff-action/breaking@v0.0.18`. Its published action manifest
  accepts `base`, `revision`, and `fail-on-diff`; CI now materializes
  `origin/main`'s committed OpenAPI file as the baseline and compares it with
  the generated current artifact.
- Installed Playwright Chromium and OS dependencies before release invokes
  `make ci`, so the release workflow executes the required browser smoke test.
- Moved the API-dependent OpenAPI generator from `contracts` to
  `app.backend.api.generate_openapi`; updated the Make target, CI command, and
  OpenAPI test import. Contracts no longer depend on application modules.
- Replaced the substring boundary test with an AST/rglob import resolver. It
  detects direct imports, `importlib.import_module` (including aliases and
  literal concatenation), and `__import__` calls.

Verification:

```text
uv run pytest app/backend/tests/architecture app/backend/tests/contracts/test_openapi.py -v  # 11 passed
uv run python -m app.backend.api.generate_openapi --check                                  # passed
make contract-check                                                                         # passed
npm --prefix app/frontend run test:e2e                                                      # 1 passed
uv run detect-secrets scan --baseline .secrets.baseline                                     # passed
uv run pip-audit                                                                            # no known vulnerabilities
npm --prefix app/frontend audit --audit-level=high                                          # 0 vulnerabilities
```

`make lint` remains blocked by pre-existing repository formatting drift in
`app/backend/contracts/prediction.py` and
`app/backend/tests/contracts/test_api_contracts.py`; `uv run lint-imports`
also reports that `app.backend.modules` does not exist because that directory
has no `__init__.py`. These files are outside Task 10 scope and were not
modified in this task. Consequently, the aggregate `make ci` command stops at
its `make lint` prerequisite with the same pre-existing formatting failure.

## Fix Round 2: First OpenAPI Artifact

- Added `.github/scripts/prepare-openapi-baseline.sh`. It materializes
  `origin/main`'s OpenAPI file and sets `present=true` when a baseline exists.
  When `main` predates the artifact, it removes any stale output, sets
  `present=false`, and emits an explicit first-artifact notice.
- `contract-check` runs oasdiff only when that output is `true`; generation,
  linting, frontend type generation, and drift detection remain unconditional.
- Added isolated Git-repository tests covering both the established-baseline
  and first-artifact branches, and documented the limited exception in the
  branch-protection runbook.

Verification:

```text
uv run pytest app/backend/tests/ci/test_openapi_baseline.py \
  app/backend/tests/architecture app/backend/tests/contracts/test_openapi.py -q  # 14 passed
uv run ruff format --check app/backend/tests/ci/test_openapi_baseline.py         # passed
uv run ruff check app/backend/tests/ci/test_openapi_baseline.py                  # passed
```

## Fix Round 3: Validate the Base Revision

- The baseline helper now verifies `BASE_REF^{commit}` with `git cat-file -e`
  before inspecting the artifact path. An invalid or unfetched `origin/main`
  reference is an explicit failure, not a first-artifact exception.
- A missing artifact is accepted only after that commit check succeeds; an
  unexpected `git show` failure still stops the script under `set -e`.
- Added a regression test for an unknown base ref alongside the established
  baseline and absent-artifact cases.

Verification:

```text
uv run pytest app/backend/tests/ci/test_openapi_baseline.py -v  # 3 passed
```
