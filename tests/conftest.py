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
_TestSessionLocal = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db():
    async with _TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    async def _override_get_db():
        async with _TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()