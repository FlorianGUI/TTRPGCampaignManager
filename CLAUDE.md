# TTRPG Campaign Manager

An app to gather TTRPG information from all kinds of sources (source books, character
sheets, campaign notes) into one place for the Game Master. FastAPI backend following
hexagonal architecture, organised by bounded contexts, with a Vue 3 frontend.

## Project layout

The repo is a monorepo split into two apps:

```
backend/    # FastAPI app (this document's architecture applies here)
frontend/   # Vue 3 + Vite SPA (see frontend/README.md)
```

Orchestration and shared config live at the root: `docker-compose*.yml`, `Justfile`,
`.pre-commit-config.yaml`, `.github/`, `nginx/`. All backend paths below are relative
to `backend/`; run the `just` recipes from the repo root (they `cd backend` for you).

### Frontend conventions

This document covers the backend. The frontend has its own conventions, documented
in full in `frontend/README.md` — read that before touching `frontend/`. The parts
that bite hardest if missed:

- **The design system is three token layers** (`src/design-system/tokens/`):
  primitives → semantic → components, each reaching downwards only. Never reference
  a primitive from a component override.
- **`LIGHT_ROLES` / `DARK_ROLES` must not be collapsed** into shared numeric indices.
  The two schemes walk the ramp in opposite directions; collapsing them reintroduces
  a light-on-light dark theme.
- **Contrast is checked, not eyeballed**: `node scripts/check-contrast.mjs` gates
  WCAG AA in both themes and exits non-zero on failure. Run it after any palette change.
- **PrimeVue is pinned to v4 (MIT)**; v5 is commercially licensed and injects a
  license banner. Don't bump the major.
- **`/styleguide`** renders every token and component — the living reference. It is
  **dev only**: the route sits behind an `import.meta.env.DEV` literal so it is
  stripped from production builds entirely.
- **There is no elevation scale**, deliberately. Depth comes from rules, borders and
  the chrome/content split.
- **Authored prose renders through `src/markdown/`** — one dialect and one component
  for every long-form field, never a second parser in a view. It renders vnodes, so
  there is **no `v-html` and no dependency that can produce an HTML string**: adding
  `remark-rehype`, `remark-stringify`, any `rehype-*` or a sanitiser breaks the
  guarantee the whole design rests on.

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
- The suite runs against its own database (`TEST_DATABASE_URL`, not `DATABASE_URL`), dropped
  and rebuilt from the migrations at the start of each session. Never point the tests at the
  development database — data created by hand through `just dev` would start failing
  acceptance scenarios. The variable is required on purpose and is a dev/CI setting only:
  production never defines it, so the suite fails closed there rather than creating a test
  database beside the real one.
- Those fixtures share one connection per test, held open in a transaction that is rolled
  back on teardown. Sessions join it with a savepoint, so repository `commit()` calls never
  reach the database and the suite can be re-run against the same local volume. Don't bind a
  test session to the engine directly — that escapes the rollback and leaks rows across runs.
- `asyncio_mode = "auto"` is set globally — all async test functions are collected automatically
- Add unit tests only when real business logic exists in the domain; do not test framework behaviour

## Stack

- **FastAPI** + **uvicorn** — async HTTP
- **SQLAlchemy** (async) + **asyncpg** — database
- **Alembic** — migrations
- **PostgreSQL** — run locally via `docker-compose.yml`
- **pytest** + **pytest-asyncio** + **pytest-bdd** — test suite
- **Poetry** — dependency management