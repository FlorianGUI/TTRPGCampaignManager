# D&D Character Sheet Creator

A REST API for creating and managing Dungeons & Dragons character sheets, built with FastAPI and following hexagonal architecture.

## Features

- Create characters with a name, class, and level
- List all characters
- Retrieve a character by ID
- Rate limiting out of the box

## Tech stack

- **FastAPI** + **uvicorn** — async HTTP server
- **SQLAlchemy** (async) + **asyncpg** — database ORM
- **Alembic** — schema migrations
- **PostgreSQL** — database (via Docker)
- **Poetry** — dependency management
- **pytest** + **pytest-asyncio** + **pytest-bdd** — test suite

## Getting started

### Prerequisites

- Python 3.13+
- [Poetry](https://python-poetry.org/)
- [Docker](https://www.docker.com/)
- [just](https://github.com/casey/just)

### Setup

```bash
# Install backend dependencies
cd backend && poetry install && cd ..

# Copy environment variables
cp .env.example .env

# Start the database
just db-up

# Apply migrations
just migrate

# Enable pre-commit hooks (ruff + mypy + frontend eslint/prettier)
(cd backend && poetry run pre-commit install)

# Start the dev server (http://localhost:8000)
just dev
```

> The backend lives in `backend/` and the Vue 3 frontend in `frontend/` (see
> `frontend/README.md`). The `just` recipes below are run from the repo root.

## API

Interactive docs are available at `http://localhost:8000/docs` once the server is running.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/characters/` | Create a character |
| `GET` | `/characters/` | List all characters |
| `GET` | `/characters/{id}` | Get a character by ID |
| `GET` | `/health` | Health check |

### Example

```bash
curl -X POST http://localhost:8000/characters/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Aragorn", "character_class": "Ranger"}'
```

## Commands

```bash
just dev              # start dev server with hot reload
just test             # run all tests
just lint             # check ruff linting + formatting
just format           # auto-fix ruff linting + formatting
just typecheck        # run mypy
just db-up            # start PostgreSQL via Docker
just db-down          # stop PostgreSQL
just migrate          # apply migrations
just migration <name> # generate a new migration
```

## Architecture

The project follows hexagonal architecture organised by bounded contexts.

```
backend/
  app/
    contexts/
      character/
        domain/         # entities and port interfaces (pure Python)
        application/    # use cases / services
        adapters/
          primary/      # inbound — HTTP routers and schemas
          secondary/    # outbound — SQLAlchemy models and repositories
    common/             # cross-cutting infrastructure (health, rate limiting)
```

Dependencies flow inward only: `adapters → application → domain`. The domain has no knowledge of FastAPI or SQLAlchemy.

## Tests

```bash
just test
```

Tests are split into four layers:

| Layer | Location | What it tests |
|-------|----------|---------------|
| Unit | `backend/tests/unit/` | Domain entities and services in isolation |
| Integration | `backend/tests/integration/` | Repositories against a real database |
| System | `backend/tests/system/` | Health and infrastructure via HTTP |
| Acceptance | `backend/tests/acceptance/` | User-facing scenarios written in Gherkin |