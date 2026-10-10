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
