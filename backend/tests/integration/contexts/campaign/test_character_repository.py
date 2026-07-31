import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.contexts.campaign.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.character_access import CharacterAccess

# The tokens are built through Campaign.grant rather than by hand: it is the only
# constructor application code has, so building them any other way here would test a
# repository nothing in the app can actually call.


def _character_at(access: CharacterAccess, name: str, description: str | None = None) -> Character:
    return Character(name=name, description=description, owner_id=access.viewer_id, campaign_id=access.campaign_id)


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyCharacterRepository:
    return SqlAlchemyCharacterRepository(db)


@pytest.fixture
def owner_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def access(owner_id: uuid.UUID) -> CharacterAccess:
    campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id)
    return CampaignAccess(owner_id).characters_at(Unsafe(campaign))


@pytest.fixture
def other_access(owner_id: uuid.UUID) -> CharacterAccess:
    return CampaignAccess(owner_id).characters_at(Unsafe(Campaign(name="Fen Wardens", owner_id=owner_id)))


class TestSave:
    async def test_returns_the_saved_character(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        character = _character_at(access, "Aragorn")

        assert await repository.save(character) == character

    async def test_persists_character(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess, owner_id: uuid.UUID
    ):
        character = _character_at(access, "Aragorn", "A ranger of the North")
        await repository.save(character)

        found = (await repository.find_by_id(character.id)).unchecked

        assert found is not None
        assert found.name == "Aragorn"
        assert found.description == "A ranger of the North"
        assert found.owner_id == owner_id
        assert found.campaign_id == access.campaign_id

    async def test_updates_a_character_that_was_already_saved(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        character = _character_at(access, "Aragorn")
        await repository.save(character)

        character.name = "Strider"
        await repository.save(character)

        found = (await repository.find_by_id(character.id)).unchecked
        assert found is not None
        assert found.name == "Strider"


class TestFindById:
    async def test_returns_character_when_found(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        character = _character_at(access, "Aragorn")
        await repository.save(character)

        result = (await repository.find_by_id(character.id)).unchecked

        assert result is not None
        assert result.id == character.id

    async def test_returns_none_for_unknown_id(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        assert (await repository.find_by_id(uuid.uuid4())).unchecked is None

    async def test_finds_a_character_at_any_table(
        self,
        repository: SqlAlchemyCharacterRepository,
        other_access: CharacterAccess,
    ):
        """No longer the repository's business which table it is at.

        Whether the caller may have it is decided by CampaignAccess, and tested there.
        This method's whole job is now to say whether a row exists.
        """
        character = _character_at(other_access, "Aragorn")
        await repository.save(character)

        assert (await repository.find_by_id(character.id)).unchecked is not None


class TestFindAllIn:
    async def test_returns_the_characters_at_that_table(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        await repository.save(_character_at(access, "Aragorn"))
        await repository.save(_character_at(access, "Legolas"))

        names = [c.name for c in await repository.find_all_in(access)]

        assert "Aragorn" in names
        assert "Legolas" in names

    async def test_leaves_out_characters_at_another_table(
        self,
        repository: SqlAlchemyCharacterRepository,
        access: CharacterAccess,
        other_access: CharacterAccess,
    ):
        await repository.save(_character_at(access, "Aragorn"))
        await repository.save(_character_at(other_access, "Boromir"))

        assert [c.name for c in await repository.find_all_in(access)] == ["Aragorn"]

    async def test_returns_empty_list_for_an_empty_table(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        assert await repository.find_all_in(access) == []


class TestDelete:
    async def test_removes_the_character(self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess):
        character = _character_at(access, "Aragorn")
        await repository.save(character)

        await repository.delete(character.id)

        assert (await repository.find_by_id(character.id)).unchecked is None

    async def test_leaves_the_other_sheets_at_the_table(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        doomed = _character_at(access, "Aragorn")
        await repository.save(doomed)
        await repository.save(_character_at(access, "Legolas"))

        await repository.delete(doomed.id)

        assert [c.name for c in await repository.find_all_in(access)] == ["Legolas"]

    async def test_deleting_an_unknown_id_is_not_an_error(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        await repository.delete(uuid.uuid4())


class TestDeleteAllIn:
    async def test_empties_the_table(self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess):
        await repository.save(_character_at(access, "Aragorn"))
        await repository.save(_character_at(access, "Legolas"))

        await repository.delete_all_in(access)

        assert await repository.find_all_in(access) == []

    async def test_leaves_the_characters_at_another_table_alone(
        self,
        repository: SqlAlchemyCharacterRepository,
        access: CharacterAccess,
        other_access: CharacterAccess,
    ):
        await repository.save(_character_at(access, "Aragorn"))
        await repository.save(_character_at(other_access, "Boromir"))

        await repository.delete_all_in(access)

        assert [c.name for c in await repository.find_all_in(other_access)] == ["Boromir"]

    async def test_emptying_an_already_empty_table_is_not_an_error(
        self, repository: SqlAlchemyCharacterRepository, access: CharacterAccess
    ):
        await repository.delete_all_in(access)
