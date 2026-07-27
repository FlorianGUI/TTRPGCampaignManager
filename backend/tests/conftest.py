import asyncio
import os
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.main import app

load_dotenv()

# Tests run against their own database, never the one `just dev` writes to. Sharing the
# two means a character created by hand in the running app can fail an acceptance test.
#
# The variable is deliberately required rather than derived from DATABASE_URL: it is set
# for local development and CI only, so on a machine that has no test database configured
# — production, where the repo is checked out but never tested — the suite refuses to
# start instead of quietly creating one next to the real database.
if "TEST_DATABASE_URL" not in os.environ:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set. The suite needs a database of its own so it cannot "
        "collide with development data — copy the line from .env.example. If you are seeing "
        "this on a deployed server, the tests are not meant to run there."
    )

_TEST_URL = make_url(os.environ["TEST_DATABASE_URL"])

# The session fixture below drops whatever this points at, so refuse anything that is not
# unmistakably a test database, however the environment came to be configured.
if not (_TEST_URL.database or "").endswith("_test"):
    raise RuntimeError(
        f"TEST_DATABASE_URL points at {_TEST_URL.database!r}. The suite drops and recreates "
        "its database on every run, so it will only accept a name ending in '_test'."
    )

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

# NullPool avoids asyncpg connections being reused across event loops between tests
_test_engine = create_async_engine(_TEST_URL, poolclass=NullPool)

# Sessions are bound to the per-test connection rather than the engine, and join its
# already-open transaction with a savepoint. A repository's commit() then releases a
# savepoint instead of writing for real, so the rollback in db_connection still undoes it.
_TestSessionLocal = async_sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
    join_transaction_mode="create_savepoint",
)


async def _recreate_test_database():
    """Drop and recreate the test database.

    CREATE/DROP DATABASE cannot run inside a transaction, hence the autocommit connection,
    and it runs against the `postgres` maintenance database because the target is being
    replaced. FORCE evicts connections a previous interrupted run may have left open.
    """
    admin_engine = create_async_engine(_TEST_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{_TEST_URL.database}" WITH (FORCE)'))
            await connection.execute(text(f'CREATE DATABASE "{_TEST_URL.database}"'))
    finally:
        await admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Rebuild the test database from nothing and bring it up to head, once per session.

    Tearing down at the start rather than at the end is deliberate: an interrupted run
    never reaches its teardown, and a leftover database would then be migrated on top of
    instead of rebuilt, which is the schema drift this is meant to prevent. It also means
    every run exercises the migrations from zero.

    Migrations run in a subprocess so alembic gets its own event loop, and so the schema
    under test is the one the migrations actually produce rather than a create_all guess.
    """
    asyncio.run(_recreate_test_database())
    migration = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": _TEST_URL.render_as_string(hide_password=False)},
        capture_output=True,
        text=True,
    )
    if migration.returncode != 0:
        raise RuntimeError(f"Could not migrate the test database:\n{migration.stdout}\n{migration.stderr}")


@pytest.fixture
async def db_connection():
    """Give each test its own connection, inside a transaction that is never committed.

    Everything a test writes is rolled back on teardown, so tests stay independent of
    each other and of previous runs against a persistent local database.
    """
    async with _test_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()


@pytest.fixture
async def db(db_connection):
    async with _TestSessionLocal(bind=db_connection) as session:
        yield session


@pytest.fixture
async def client(db_connection):
    async def _override_get_db():
        async with _TestSessionLocal(bind=db_connection) as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
