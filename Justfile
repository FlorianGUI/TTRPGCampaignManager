set dotenv-load := true

default:
    @just --list

dev:
    cd backend && poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

start:
    cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

db-up:
    docker compose up -d

db-down:
    docker compose down

test:
    cd backend && poetry run pytest

coverage:
    cd backend && poetry run pytest --cov-report=html
    open backend/htmlcov/index.html

lint:
    cd backend && poetry run ruff check .
    cd backend && poetry run ruff format --check .

format:
    cd backend && poetry run ruff check --fix .
    cd backend && poetry run ruff format .

typecheck:
    cd backend && poetry run mypy .

migrate:
    cd backend && poetry run alembic upgrade head

migration name:
    cd backend && poetry run alembic revision --autogenerate -m "{{name}}"

seed:
    cd backend && poetry run python -m scripts.seed_dev_data

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