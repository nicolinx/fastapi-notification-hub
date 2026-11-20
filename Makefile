.DEFAULT_GOAL := help
.PHONY: help install env dev test cov lint format format-check typecheck check clean up down logs ps migrate migration migrate-down psql api-key

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies into .venv (like `pub get`)
	uv sync

env: ## Create .env from .env.example if it does not exist
	@test -f .env && echo ".env already exists" || (cp .env.example .env && echo "Created .env")

dev: ## Run the API with auto-reload on http://localhost:8000
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

worker: ## Run the Celery worker
	uv run celery -A src.workers.celery_app worker --loglevel=info --pool=solo

test: ## Run the test suite
	uv run pytest

cov: ## Run tests with a coverage report
	uv run pytest --cov=src --cov-report=term-missing tests/

lint: ## Check code for lint problems
	uv run ruff check .

format: ## Auto-format code and fix simple lint issues
	uv run ruff format .
	uv run ruff check --fix .

format-check: ## Check formatting without changing files
	uv run ruff format --check .

typecheck: ## Run the strict mypy type checker
	uv run mypy src tests

check: lint format-check typecheck test ## Run everything CI will run

up: ## Start only Postgres and Redis (for running the API locally with make dev)
	docker compose up -d --wait postgres redis

down: ## Stop the containers (data is kept in volumes)
	docker compose down

build: ## Build the application image
	docker compose build

stack: ## Build and start the whole stack (postgres, redis, migrate, app, worker)
	docker compose up -d --build

logs: ## Follow container logs
	docker compose logs -f

ps: ## Show container status and health
	docker compose ps

migrate: ## Apply all pending database migrations
	uv run alembic upgrade head

api-key: ## Create an API key: make api-key name=demo
	@test -n "$(name)" || (echo 'Usage: make api-key name=demo' && exit 1)
	uv run python -m src.scripts.create_api_key "$(name)"

migration: ## Generate a migration from model changes: make migration m="add x"
	@test -n "$(m)" || (echo 'Usage: make migration m="describe the change"' && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

migrate-down: ## Roll back the last migration
	uv run alembic downgrade -1

psql: ## Open a psql shell in the Postgres container
	docker compose exec postgres psql -U postgres -d notification_hub

clean: ## Remove caches and build artifacts (keeps .venv and .env)
	find . -name __pycache__ -not -path "./.venv/*" -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
