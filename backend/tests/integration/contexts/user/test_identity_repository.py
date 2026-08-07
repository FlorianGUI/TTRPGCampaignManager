import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import UserId
from app.contexts.user.adapters.secondary.persistence.identity_repository import SqlAlchemyIdentityRepository
from app.contexts.user.domain.identity import Identity, Provider


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyIdentityRepository:
    return SqlAlchemyIdentityRepository(db)


class TestSave:
    async def test_returns_the_saved_identity(self, repository: SqlAlchemyIdentityRepository):
        identity = Identity(user_id=UserId(uuid.uuid4()), provider=Provider.GOOGLE, subject="1234567890")

        result = await repository.save(identity)

        assert result == identity

    async def test_persists_it(self, repository: SqlAlchemyIdentityRepository):
        identity = Identity(user_id=UserId(uuid.uuid4()), provider=Provider.DISCORD, subject="9876543210")
        await repository.save(identity)

        found = await repository.find_by_subject(Provider.DISCORD, "9876543210")

        assert found is not None
        assert found.id == identity.id
        assert found.user_id == identity.user_id
        assert found.provider is Provider.DISCORD

    async def test_refuses_a_second_row_for_the_same_provider_account(self, repository: SqlAlchemyIdentityRepository):
        """The constraint, checked against the database rather than against the model.

        Two rows claiming one provider subject would make which account a sign-in reaches
        depend on row order. This is the one guarantee the whole lookup rests on, so it is
        worth proving the index really exists rather than trusting the declaration.
        """
        await repository.save(Identity(user_id=UserId(uuid.uuid4()), provider=Provider.GOOGLE, subject="collide"))

        with pytest.raises(IntegrityError):
            await repository.save(Identity(user_id=UserId(uuid.uuid4()), provider=Provider.GOOGLE, subject="collide"))

    async def test_allows_the_same_subject_from_a_different_provider(self, repository: SqlAlchemyIdentityRepository):
        """Subjects are only unique within a provider. Google and Discord are free to hand
        out the same string, and they are different people."""
        await repository.save(Identity(user_id=UserId(uuid.uuid4()), provider=Provider.GOOGLE, subject="shared"))

        await repository.save(Identity(user_id=UserId(uuid.uuid4()), provider=Provider.DISCORD, subject="shared"))

        google = await repository.find_by_subject(Provider.GOOGLE, "shared")
        discord = await repository.find_by_subject(Provider.DISCORD, "shared")
        assert google is not None and discord is not None
        assert google.user_id != discord.user_id


class TestFindBySubject:
    async def test_returns_none_when_nothing_matches(self, repository: SqlAlchemyIdentityRepository):
        result = await repository.find_by_subject(Provider.GOOGLE, "never-seen")

        assert result is None

    async def test_does_not_match_across_providers(self, repository: SqlAlchemyIdentityRepository):
        await repository.save(Identity(user_id=UserId(uuid.uuid4()), provider=Provider.GOOGLE, subject="only-google"))

        assert await repository.find_by_subject(Provider.DISCORD, "only-google") is None


class TestFindForUser:
    async def test_returns_every_way_into_one_account(self, repository: SqlAlchemyIdentityRepository):
        """What a detach has to consult before removing the last one, and what an account
        page shows."""
        user = UserId(uuid.uuid4())
        await repository.save(Identity(user_id=user, provider=Provider.GOOGLE, subject="g-1"))
        await repository.save(Identity(user_id=user, provider=Provider.DISCORD, subject="d-1"))

        found = await repository.find_for_user(user)

        assert {identity.provider for identity in found} == {Provider.GOOGLE, Provider.DISCORD}

    async def test_returns_nothing_for_an_account_with_only_a_password(self, repository: SqlAlchemyIdentityRepository):
        assert await repository.find_for_user(UserId(uuid.uuid4())) == []

    async def test_does_not_return_another_account_s_identities(self, repository: SqlAlchemyIdentityRepository):
        mine = UserId(uuid.uuid4())
        theirs = UserId(uuid.uuid4())
        await repository.save(Identity(user_id=theirs, provider=Provider.GOOGLE, subject="not-mine"))

        assert await repository.find_for_user(mine) == []
