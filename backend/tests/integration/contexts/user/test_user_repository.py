import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import UserId
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

    async def test_persists_an_account_with_no_password(self, repository: SqlAlchemyUserRepository):
        """The column is nullable now, and this is what proves it against a real database
        rather than against the model's opinion of itself."""
        user = User(username="gimli", email="gimli@erebor.test")

        await repository.save(user)
        found = await repository.find_by_id(user.id)

        assert found is not None
        assert found.hashed_password is None
        assert found.has_password is False

    async def test_a_new_row_is_unverified(self, repository: SqlAlchemyUserRepository):
        user = User(username="merry", email="merry@shire.com", hashed_password="hashed")

        await repository.save(user)
        found = await repository.find_by_id(user.id)

        assert found is not None
        assert found.email_verified is False

    async def test_round_trips_a_verified_address(self, repository: SqlAlchemyUserRepository):
        user = User(
            username="galadriel",
            email="galadriel@lorien.test",
            hashed_password="hashed",
            email_verified=True,
        )

        await repository.save(user)
        found = await repository.find_by_id(user.id)

        assert found is not None
        assert found.email_verified is True


class TestFindById:
    async def test_returns_user_when_found(self, repository: SqlAlchemyUserRepository):
        user = User(username="pippin", email="pippin@shire.com", hashed_password="hashed")
        await repository.save(user)

        result = await repository.find_by_id(user.id)

        assert result is not None
        assert result.id == user.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyUserRepository):
        result = await repository.find_by_id(UserId(uuid.uuid4()))

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
