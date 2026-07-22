set dotenv-load := true

default:
    @just --list

dev:
    poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

start:
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

db-up:
    docker compose up -d

db-down:
    docker compose down

test:
    poetry run pytest

coverage:
    poetry run pytest --cov-report=html
    open htmlcov/index.html

lint:
    poetry run ruff check .
    poetry run ruff format --check .

format:
    poetry run ruff check --fix .
    poetry run ruff format .

typecheck:
    poetry run mypy .

migrate:
    poetry run alembic upgrade head

migration name:
    poetry run alembic revision --autogenerate -m "{{name}}"

# --- Frontend (Vue 3 + Vite, in ./frontend) ---

front-install:
    cd frontend && npm install

front-dev:
    cd frontend && npm run dev

front-build:
    cd frontend && npm run build

front-preview:
    cd frontend && npm run preview

front-test:
    cd frontend && npm test

front-lint:
    cd frontend && npm run lint
    cd frontend && npm run format:check

front-format:
    cd frontend && npm run lint:fix
    cd frontend && npm run format