# D&D Character Sheet Creator

FastAPI application following hexagonal architecture, organised by bounded contexts.

## Project layout

The repo is a monorepo split into two apps:

```
backend/    # FastAPI app (this document's architecture applies here)
frontend/   # Vue 3 + Vite SPA (see frontend/README.md)
```

Orchestration and shared config live at the root: `docker-compose*.yml`, `Justfile`,
`.pre-commit-config.yaml`, `.github/`, `nginx/`. All backend paths below are relative
to `backend/`; run the `just` recipes from the repo root (they `cd backend` for you).

## Commands

```bash
just dev          # start dev server with hot reload (port 8000)
just test         # run all tests (fails if coverage drops below 100%)
just coverage     # run tests and open an HTML coverage report
just lint         # check ruff linting + formatting
just format       # auto-fix ruff linting + formatting
just typecheck    # run mypy
just db-up        # start PostgreSQL via Docker
just db-down      # stop PostgreSQL
just migrate      # apply migrations (alembic upgrade head)
just migration <name>  # generate a new migration
```

Run `poetry run pre-commit install` once after cloning to enable the pre-commit hooks (ruff + mypy) defined in `.pre-commit-config.yaml`.

## Git workflow

Create a new branch from `main` for changes and open a pull request for review — don't push directly to `main`.

## Architecture

### Bounded contexts

All domain logic lives under `app/contexts/<context>/`. Each context is self-contained:

```
app/contexts/<context>/
  domain/              # entities and port interfaces (pure Python, no framework)
    ports/             # abstract repository interfaces
  application/         # use cases / services (orchestrates domain, calls ports)
  adapters/
    primary/           # inbound — HTTP routers and request/response schemas
    secondary/         # outbound — SQLAlchemy models and repository implementations
```

### Common

Cross-cutting infrastructure that does not belong to any context:

```
app/common/            # no hexagonal layers here, flat structure
```

### Dependency rule

Dependencies flow inward only: `adapters → application → domain`. The domain has no knowledge of FastAPI, SQLAlchemy, or any framework.

### Adding a new context

1. Create `app/contexts/<name>/domain/` with the entity and port interface
2. Create `app/contexts/<name>/application/` with the service
3. Create `app/contexts/<name>/adapters/primary/` for HTTP router and schemas
4. Create `app/contexts/<name>/adapters/secondary/` for the SQLAlchemy model and repository
5. Register the router in `app/main.py`
6. Generate a migration with `just migration <name>`

## Tests

Tests are split into four layers mirroring the app structure:

| Layer | Location | What it tests |
|---|---|---|
| Unit | `tests/unit/` | Domain entities and application services in isolation (no DB, no HTTP) |
| Integration | `tests/integration/` | Secondary adapters (repositories) against a real DB |
| System | `tests/system/` | Health and infrastructure only (full HTTP stack) |
| Acceptance | `tests/acceptance/` | Primary adapters — user-facing scenarios written in Gherkin |

### Acceptance tests (Gherkin)

Feature files live next to their step definitions:

```
tests/acceptance/<context>/
  features/<context>.feature   # Gherkin scenarios
  test_<context>.py            # pytest-bdd step definitions
```

Use `parsers.parse(...)` for steps with parameters:

```python
@given(parsers.parse('I create a character named "{name}" with class "{character_class}"'))
```

### Test conventions

- Unit tests use a `Fake*Repository` in-memory stub — no mocking library
- Integration and system tests use the real DB via the `db` and `client` fixtures in `tests/conftest.py`
- `asyncio_mode = "auto"` is set globally — all async test functions are collected automatically
- Add unit tests only when real business logic exists in the domain; do not test framework behaviour

## Stack

- **FastAPI** + **uvicorn** — async HTTP
- **SQLAlchemy** (async) + **asyncpg** — database
- **Alembic** — migrations
- **PostgreSQL** — run locally via `docker-compose.yml`
- **pytest** + **pytest-asyncio** + **pytest-bdd** — test suite
- **Poetry** — dependency management