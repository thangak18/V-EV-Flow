.PHONY: setup format lint test contract-check smoke security ci

setup:
	uv sync --frozen
	npm --prefix app/frontend ci

format:
	uv run ruff format app
	uv run ruff check --fix app
	npm --prefix app/frontend run format

lint:
	uv run ruff format --check app
	uv run ruff check app
	uv run pyright app/backend
	uv run lint-imports
	npm --prefix app/frontend run lint
	npm --prefix app/frontend run format:check

test:
	uv run pytest app/backend/tests --cov=app.backend --cov-report=term-missing --cov-fail-under=75
	npm --prefix app/frontend run test:coverage

contract-check:
	uv run python -m app.backend.contracts.generate_openapi --check
	npm --prefix app/frontend run lint:openapi
	npm --prefix app/frontend run generate:api
	git diff --exit-code -- app/backend/contracts/openapi.yaml app/frontend/src/types/api.generated.ts

smoke:
	npm --prefix app/frontend run test:e2e

security:
	uv run detect-secrets scan --baseline .secrets.baseline
	uv run pip-audit
	npm --prefix app/frontend audit --audit-level=high

ci: lint test contract-check smoke security
