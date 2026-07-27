import os

import pytest
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.main import app

load_dotenv()

# NullPool avoids asyncpg connections being reused across event loops between tests
_test_engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)

# Sessions are bound to the per-test connection rather than the engine, and join its
# already-open transaction with a savepoint. A repository's commit() then releases a
# savepoint instead of writing for real, so the rollback in db_connection still undoes it.
_TestSessionLocal = async_sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
    join_transaction_mode="create_savepoint",
)


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
