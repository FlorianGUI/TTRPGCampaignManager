# TTRPG Campaign Manager — Setup

## Requirements

- [Python 3.13+](https://www.python.org/)
- [Poetry 2+](https://python-poetry.org/)
- [Docker](https://www.docker.com/)
- [just](https://github.com/casey/just)

## Installation

```bash
# Install backend dependencies
cd backend && poetry install && cd ..

# Copy environment config
cp .env.example .env
```

## Running the app

```bash
# Start the database
just db-up

# Apply migrations
just migrate

# Start the API (with hot-reload)
just dev
```

The API is available at <http://localhost:8000>.
Interactive docs (Swagger UI) at <http://localhost:8000/docs>.

## Common commands

```bash
just dev                        # Start API with hot-reload
just start                      # Start API without hot-reload
just test                       # Run test suite
just db-up                      # Start Postgres container
just db-down                    # Stop Postgres container
just migrate                    # Apply pending migrations
just migration "add users table" # Create a new migration
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://dnd:dnd@localhost:5435/dnd_db` | SQLAlchemy async connection URL |
| `TEST_DATABASE_URL` | `postgresql+asyncpg://dnd:dnd@localhost:5435/dnd_db_test` | **Local development and CI only — never set in production.** Database the test suite uses, dropped and rebuilt from the migrations on every run. Unset means the suite refuses to start, which is what keeps it from ever running against a deployed database |
| `POSTGRES_USER` | `dnd` | Postgres username |
| `POSTGRES_PASSWORD` | `dnd` | Postgres password |
| `POSTGRES_DB` | `dnd_db` | Postgres database name |
| `POSTGRES_HOST` | `localhost` | Postgres host |
| `POSTGRES_PORT` | `5435` | Postgres port (5435 to avoid conflicts with local installs). Drives the `docker-compose.yml` port mapping, so changing it here is enough |

## Project structure

```
backend/
  app/           # FastAPI app (hexagonal, by bounded context — see CLAUDE.md)
    main.py      # app entry point, router registration
    contexts/    # bounded contexts (character, user, ...)
    common/      # cross-cutting infrastructure (health, security, rate limiting)
  alembic/       # database migrations
    versions/    # migration files
  tests/         # unit / integration / system / acceptance
  pyproject.toml
  Dockerfile
frontend/        # Vue 3 + Vite SPA (see frontend/README.md)
nginx/           # reference host nginx config for the VPS
docker-compose.yml       # local Postgres
docker-compose.prod.yml  # production stack (app + db)
Justfile
```