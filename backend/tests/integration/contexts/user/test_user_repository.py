import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import UserId
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.domain.ports.user_repository import EmailTakenError, UsernameTakenError
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


class TestUniqueViolations:
    """The index's answer, translated — checked against a real Postgres rather than a
    guess about what the driver reports.

    Which constraint failed decides what the caller does next: retry with another name, or
    report that the address belongs to someone. Collapsing both into one error would leave
    the application guessing, and matching on the message text would break the day the
    driver rewords it.
    """

    async def test_a_duplicate_username_is_reported_as_such(self, repository: SqlAlchemyUserRepository):
        await repository.save(User(username="frodo", email="frodo@shire.com", hashed_password="hashed"))

        with pytest.raises(UsernameTakenError):
            await repository.save(User(username="frodo", email="other@shire.com", hashed_password="hashed"))

    async def test_a_duplicate_email_is_reported_separately(self, repository: SqlAlchemyUserRepository):
        await repository.save(User(username="rosie", email="shared@shire.com", hashed_password="hashed"))

        with pytest.raises(EmailTakenError):
            await repository.save(User(username="other", email="shared@shire.com", hashed_password="hashed"))

    async def test_the_session_survives_a_rejected_save(self, repository: SqlAlchemyUserRepository):
        """The point of the rollback. A caller retrying with the next variant needs a
        working session, and a failed flush leaves one unusable until it is rolled back —
        so without it the retry fails for an unrelated reason.
        """
        await repository.save(User(username="taken", email="taken@shire.com", hashed_password="hashed"))
        with pytest.raises(UsernameTakenError):
            await repository.save(User(username="taken", email="new@shire.com", hashed_password="hashed"))

        saved = await repository.save(User(username="taken-2", email="new@shire.com", hashed_password="hashed"))

        assert await repository.find_by_username("taken-2") == saved

    async def test_an_integrity_error_it_does_not_recognise_is_left_alone(self, repository: SqlAlchemyUserRepository):
        """Two named constraints are translated; everything else is re-raised as it came.

        Reinterpreting an unfamiliar violation would be a guess, and the guess would be
        wrong in the direction that matters — a caller retrying with another username
        against a failure that had nothing to do with the username. Here the collision is
        on the primary key.
        """
        existing = User(username="theoden", email="theoden@rohan.test", hashed_password="hashed")
        await repository.save(existing)

        with pytest.raises(IntegrityError):
            await repository.save(
                User(id=existing.id, username="eomer", email="eomer@rohan.test", hashed_password="hashed")
            )
