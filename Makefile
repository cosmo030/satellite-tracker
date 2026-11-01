# Developer commands. `make check` runs exactly what CI runs.
# Variables from .env (if present) are exported to every command.

-include .env
export

BACKEND := cd backend &&
FRONTEND := cd frontend &&

.PHONY: help install db-up db-down migrate seed run-api run-ingest run-enrich run-web \
	format format-check lint typecheck test test-backend test-frontend build openapi check

help: ## List the available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Install backend and frontend dependencies from the lockfiles
	$(BACKEND) uv sync --locked
	$(FRONTEND) npm ci

db-up: ## Start the local PostgreSQL container
	docker compose up -d --wait db

db-down: ## Stop the local PostgreSQL container (data is kept in a volume)
	docker compose stop db

migrate: ## Apply database migrations to SATTRACK_DATABASE_URL
	$(BACKEND) uv run alembic upgrade head

seed: ## Load synthetic demo satellites (no CelesTrak access needed)
	$(BACKEND) uv run python scripts/seed_dev_data.py

run-api: ## Run the API with auto-reload on http://localhost:8000
	$(BACKEND) uv run uvicorn sattrack.main:create_app --factory --reload --port 8000

run-ingest: ## Run one ingest pass against CelesTrak
	$(BACKEND) uv run python -m sattrack.ingest --once

run-enrich: ## Fetch descriptions and images from Wikimedia (needs SATTRACK_ENRICH_CONTACT)
	$(BACKEND) uv run python -m sattrack.enrich --once

run-web: ## Run the frontend dev server on http://localhost:5173
	$(FRONTEND) npm run dev

format: ## Format all code
	$(BACKEND) uv run ruff format .
	$(BACKEND) uv run ruff check --fix .
	$(FRONTEND) npm run format

format-check: ## Check formatting without changing files
	$(BACKEND) uv run ruff format --check .
	$(FRONTEND) npm run format:check

lint: ## Run linters
	$(BACKEND) uv run ruff check .
	$(FRONTEND) npm run lint

typecheck: ## Run type checkers
	$(BACKEND) uv run mypy src tests
	$(FRONTEND) npm run typecheck

test-backend: ## Backend tests; integration tests need SATTRACK_TEST_DATABASE_URL
	$(BACKEND) uv run pytest --cov --cov-report=term --cov-report=xml

test-frontend: ## Frontend unit tests
	$(FRONTEND) npm run test:coverage

test: test-backend test-frontend ## Run all tests

build: ## Build the production frontend bundle
	$(FRONTEND) npm run build

openapi: ## Regenerate docs/openapi.json from the API code
	$(BACKEND) uv run python scripts/export_openapi.py

check: format-check lint typecheck test build ## Run every check (what CI runs)
