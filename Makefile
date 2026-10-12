.PHONY: setup format lint test build contract-check smoke security ci backend-lint frontend-lint backend-test-suite frontend-test-suite

setup:
	uv sync --frozen
	npm --prefix app/frontend ci
	npm --prefix app/frontend exec playwright install chromium

format:
	uv run ruff format app
	uv run ruff check --fix app
	npm --prefix app/frontend run format

backend-lint:
	uv run ruff format --check app
	uv run ruff check app
	uv run pyright app/backend
	uv run lint-imports

frontend-lint:
	npm --prefix app/frontend run lint
	npm --prefix app/frontend run format:check

lint: backend-lint frontend-lint

backend-test-suite:
	uv run pytest app/backend --cov=app.backend --cov-report=term-missing --cov-fail-under=75

frontend-test-suite:
	npm --prefix app/frontend run test:coverage

test: backend-test-suite frontend-test-suite

build:
	npm --prefix app/frontend run build

contract-check:
	uv run python -m app.backend.api.generate_openapi --check
	npm --prefix app/frontend run lint:openapi
	npm --prefix app/frontend run generate:api
	git diff --exit-code -- app/backend/contracts/openapi.yaml app/frontend/src/types/api.generated.ts

smoke:
	npm --prefix app/frontend run test:e2e

security:
	git ls-files -z | xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline
	uv run pip-audit
	npm --prefix app/frontend audit --audit-level=high

ci: lint test build contract-check smoke security
