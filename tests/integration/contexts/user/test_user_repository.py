import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.domain.user import User


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db)


class TestSave:
    async def test_returns_the_saved_user(self, repository: SqlAlchemyUserRepository):
        user = User(username="bilbo", email="bilbo@shire.com", hashed_password="hashed")

        result = await repository.save(user)

        assert result == user

    async def test_persists_user(self, repository: SqlAlchemyUserRepository):
        user = User(username="samwise", email="samwise@shire.com", hashed_password="hashed")
        await repository.save(user)

        found = await repository.find_by_id(user.id)

        assert found is not None
        assert found.username == "samwise"
        assert found.email == "samwise@shire.com"


class TestFindById:
    async def test_returns_user_when_found(self, repository: SqlAlchemyUserRepository):
        user = User(username="pippin", email="pippin@shire.com", hashed_password="hashed")
        await repository.save(user)

        result = await repository.find_by_id(user.id)

        assert result is not None
        assert result.id == user.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyUserRepository):
        result = await repository.find_by_id(uuid.uuid4())

        assert result is None


class TestFindByUsername:
    async def test_returns_user_when_found(self, repository: SqlAlchemyUserRepository):
        user = User(username="merry", email="merry@shire.com", hashed_password="hashed")
        await repository.save(user)

        result = await repository.find_by_username("merry")

        assert result is not None
        assert result.id == user.id

    async def test_returns_none_for_unknown_username(self, repository: SqlAlchemyUserRepository):
        result = await repository.find_by_username("unknown")

        assert result is None
