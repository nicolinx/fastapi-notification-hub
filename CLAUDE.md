# CLAUDE.md - FastAPI Notification Hub

## Project Context & Primary Goals
* **Exploratory Learning:** This project serves as a hands-on learning environment for mastering FastAPI, asynchronous Python development, background workers (Celery), and distributed systems patterns.
* **Portfolio & Recruiter Showcase:** Built with clean architecture, strict typing, and production-ready practices to demonstrate backend engineering skills (high throughput, fault tolerance, non-blocking IO) for recruiter evaluation and LinkedIn/GitHub technical posts.
* **Iterative MVP Approach:** Development follows a progressive roadmap—starting with a functional MVP core (Phase 1) before incrementally layering advanced features (Rate Limiting, WebSockets, Metrics).

## Learning Mode (How Claude Should Work With Me)
* I am a mobile engineer, new to backend. My main stack is **Flutter & Dart**. Explain Python/FastAPI concepts by mapping them to Dart/Flutter where useful:
  * Pydantic `BaseModel` ≈ Dart model class with `fromJson`/`toJson` (`json_serializable`/`freezed`), but validation runs automatically.
  * Python type hints ≈ Dart static types (but not enforced at runtime, so rely on `mypy`/Pydantic).
  * `async`/`await` ≈ Dart `Future`/`async`/`await`; the asyncio event loop ≈ Dart's single-threaded event loop.
  * Celery worker ≈ a Dart `Isolate` / `compute()` / WorkManager, except it runs as a separate process.
  * FastAPI `Depends()` ≈ Riverpod providers / `get_it` dependency injection.
  * SQLAlchemy models + Alembic migrations ≈ Drift/Floor tables + schema migrations.
  * Routes/services/schemas layering ≈ Flutter's UI / domain / data layers (route = view, service = repository/use case).
  * `pytest` ≈ `flutter_test`/`package:test`; `pydantic-settings` ≈ `--dart-define`/`flutter_dotenv`.
  * `ruff` ≈ `dart analyze` + `dart format`; `uv`/`pyproject.toml` ≈ `pub`/`pubspec.yaml`.
  * Call out where Python differs from Dart (dynamic typing, indentation, no null safety, mutable defaults, GIL).
* **Walkthrough-first workflow (the way I learn):** I write the code myself. For each roadmap step, do NOT implement it in the project files. Instead, write a step-by-step walkthrough in `walkthrough-step-N.local.md` at the repo root (gitignored via `*.local.*`) that I follow and type by hand.
  * Split the step into small sub-steps. Each sub-step has: the file path, a short *why* it exists, the code to type (inline, not in a separate answer key), and a quick check command.
  * **Explanations live inside the code, as Indonesian comments prefixed with `#>`** (use `--` in SQL). I skip these while typing. Keep the real English code comments as normal `#` comments, because those are typed. Put each explanation on the line(s) above the code it explains. Do not add a separate "Penjelasan" section after the code block.
  * Keep it simple. **No Dart/Flutter analogies in walkthroughs.** (Analogies are still fine when I ask a question in chat.) Put a one-line "Cara baca" note at the top of each walkthrough explaining the `#>` convention.
  * Start each walkthrough with a "Step 0" for prerequisites (services up, migrations applied, seed data) and end with a troubleshooting table and a definition of done.
  * Edit project source files only when I explicitly ask (e.g. fix a bug, review my code, apply a refactor). Do not commit unless told.
  * When I finish typing, review my code on request and point out issues instead of silently rewriting it.
* Work in small steps. Explain *why* before showing code.
* Prefer the simplest thing that works. Flag when something is over-engineering for the current phase.
* Directory tree and commands below are **planned**. Verify a file exists before assuming it does.

## Product Overview

FastAPI Notification Hub is a high-throughput, real-time multi-tenant notification and event-broadcasting system built with Python and FastAPI. It offloads expensive payload processing and dynamic dispatching (Push Notifications, Email, WebSockets) to an asynchronous worker queue, guaranteeing sub-second HTTP responses even during mass broadcasting spikes.

## Architectural Principles & Mental Model

* **Layered Clean Architecture:** Decouple delivery layers (FastAPI routes) from core business logic (services), validation schemas (Pydantic), and database/queue infrastructure.

* **Non-Blocking Execution:** Keep the API web server execution path strictly non-blocking. Offload compute-heavy parsing, database synchronization, and external API calls (FCM, SMTP) to asynchronous background workers (Celery).

* **Fail-Safe & Idempotent Operations:** Design all notification dispatches to be idempotent using unique transaction keys to prevent duplicate execution under network retries.

## Tech Stack

* **Language:** Python 3.11+

* **Framework:** FastAPI

* **Validation & Schemas:** Pydantic V2

* **Database & ORM:** PostgreSQL + SQLAlchemy 2.0 (Async) + Alembic (Migrations)

* **Caching & Rate Limiting:** Redis

* **Task Queue & Workers:** Celery with Redis as message broker

* **Testing:** Pytest, HTTPX, Pytest-Asyncio

* **Containerization & Deployment:** Docker, Docker Compose, Uvicorn

## Project Directory Structure

```
fastapi-notification-hub/
├── alembic/                 # Database migration scripts
├── src/
│   ├── api/                 # Route controllers (v1 endpoints)
│   ├── core/                # Global config, security, database sessions, middleware
│   ├── models/              # SQLAlchemy database ORM models
│   ├── schemas/             # Pydantic schemas (DTOs, request/response models)
│   ├── services/            # Business logic and external service integrations
│   ├── workers/             # Celery background tasks & queue processors
│   └── main.py              # Application entrypoint & FastAPI app initialization
├── tests/                   # Automated tests suite (unit & integration)
├── .env.example             # Environment variable templates
├── docker-compose.yml       # Local development stack (App, Postgres, Redis, Celery)
├── Dockerfile               # Production multi-stage build setup
├── pyproject.toml           # Package configuration and dependencies
└── README.md                # Project documentation
```

## Common Development Commands

### Environment Setup

```bash
# Dependencies are managed with uv + pyproject.toml
uv sync
source .venv/bin/activate
```

### Running Locally (Docker Compose)

```bash
# Start all services (API, Postgres, Redis, Celery)
docker-compose up -d --build

# View logs
docker-compose logs -f app worker
```

### Running Locally (Without Docker)

```bash
# Run FastAPI server with auto-reload
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker process
celery -A src.workers.celery_app worker --loglevel=info
```

### Database Migrations (Alembic)

```bash
# Generate a new migration script
alembic revision --autogenerate -m "describe_changes"

# Apply pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

### Testing & Quality Checks

```bash
# Run full test suite
pytest

# Run tests with coverage report
pytest --cov=src tests/

# Run linting and code formatting
ruff check src/
ruff format --check src/
```

## Implementation Roadmap (Iterative Building Strategy)

### Phase 1: MVP Core (Target: Standalone Async Processing)

1. **API Initialization:** Configure FastAPI app instance, CORS middleware, global exception handlers, and basic healthcheck route (`GET /health`).

2. **Schema & Models:** Create basic SQLAlchemy models (`User`, `Notification`) and Pydantic schemas for payload validation.

3. **Database Integration:** Setup async SQLAlchemy engine session management (`src/core/database.py`).

4. **Queue Offloading:** Implement `POST /api/v1/notifications/send` endpoint that accepts notification payload, pushes a job to Redis, and returns `202 Accepted` immediately with a `task_id`.

5. **Background Worker:** Write a Celery worker task (`src/workers/tasks.py`) that consumes the job, simulates notification dispatch (mock SMTP/FCM), and updates status in PostgreSQL (`PENDING` -> `DELIVERED`).

6. **Tests & CI:** Add Pytest tests for the health and send endpoints and the worker task. Add a GitHub Actions workflow (`.github/workflows/ci.yml`) running `ruff check`, `ruff format --check` and `pytest`, with a status badge in the README.

7. **README v1:** Architecture diagram, `docker-compose up` quickstart, and a short "design decisions" section. State clearly that SMTP/FCM delivery is mocked.

### Phase 2: System Resilience & Dynamic Processing

1. **Idempotency Support:** Add `X-Idempotency-Key` validation middleware leveraging Redis cache to prevent duplicate request processing.

2. **Rate Limiting:** Implement token bucket or sliding-window rate limiting per API key using Redis.

3. **Dynamic Template Engine:** Integrate Jinja2 template rendering inside the background task for message payload interpolation.

4. **Load Test & Benchmarks:** Add a `locust` or `k6` script under `loadtest/`. Record real numbers (p50/p95 latency, requests/sec for the 202 response) in the README. Do not claim throughput figures that have not been measured.

5. **Real FCM (optional):** Replace the mocked push provider with real Firebase Cloud Messaging, received by the Flutter demo client.

6. **Production Config & Secrets (optional):** Stop hardcoding credentials in `docker-compose.yml`. Inject secrets via `env_file` / environment (kept out of Git and out of the image), use non-default DB passwords, stop publishing Postgres/Redis ports to the host, and add a short "Security notes" section to the README. Do this together with real FCM, since the Firebase service-account key is the first real secret.

### Phase 3: Real-Time Communication & Observability

1. **WebSocket Dispatcher:** Add WebSocket endpoint (`/ws/notifications/{user_id}`) for live client updates on notification status changes.

2. **Retry Mechanism & DLQ:** Configure automatic retry policies with exponential backoff for failed network calls to external providers.

3. **Prometheus Metrics:** Expose basic system metrics endpoint (`/metrics`) tracking worker throughput and job latency.

4. **Flutter Demo Client:** A small Flutter app (separate `flutter_client/` folder or sibling repo) that sends notifications through the API and shows live status updates over the WebSocket. Generate the Dart API client from the FastAPI OpenAPI schema. Use it for the README demo GIF.

> **Scope rule:** A finished, tested, benchmarked Phase 1–2 is better than an unfinished Phase 3. Complete and document each phase before starting the next.

## Code Guidelines & Conventions

1. **Strict Type Annotations:** Utilize Python type hints (`str`, `int`, `Optional[T]`, `List[T]`) across all function signatures and parameters.

2. **Async-First IO:** Use `async def` for FastAPI endpoint handlers and asynchronous DB queries (`select()`, `execute()`). Use synchronous functions only for CPU-bound or standard blocking worker routines. Note: Celery tasks are synchronous, so the worker must use a sync DB session (or wrap async calls with `asyncio.run`), not the API's async session.

3. **Validation Layers:** Keep input validation strict via Pydantic V2 `BaseModel`. Never bypass validation in controller route definitions.

4. **Environment Variables:** Access configurations strictly through dynamic settings via `pydantic-settings` (`src/core/config.py`). Do not read raw `os.getenv` throughout business logic.

5. **Explicit Error Handling:** Throw structured custom HTTP exceptions with clear error messages and status codes.