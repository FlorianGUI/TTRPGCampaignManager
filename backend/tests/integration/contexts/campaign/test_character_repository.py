import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.campaign.domain.access import CampaignAccess
from app.contexts.campaign.domain.campaign import Campaign

# The tokens are built through Campaign.grant rather than by hand: it is the only
# constructor application code has, so building them any other way here would test a
# repository nothing in the app can actually call.


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyCharacterRepository:
    return SqlAlchemyCharacterRepository(db)


@pytest.fixture
def owner_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def access(owner_id: uuid.UUID) -> CampaignAccess:
    return Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id).grant(owner_id)


@pytest.fixture
def other_access(owner_id: uuid.UUID) -> CampaignAccess:
    return Campaign(name="Fen Wardens", owner_id=owner_id).grant(owner_id)


class TestSave:
    async def test_returns_the_saved_character(self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess):
        character = access.new_character("Aragorn")

        assert await repository.save(character) == character

    async def test_persists_character(
        self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess, owner_id: uuid.UUID
    ):
        character = access.new_character("Aragorn", "A ranger of the North")
        await repository.save(character)

        found = await repository.find_by_id_in(character.id, access)

        assert found is not None
        assert found.name == "Aragorn"
        assert found.description == "A ranger of the North"
        assert found.owner_id == owner_id
        assert found.campaign_id == access.campaign_id

    async def test_updates_a_character_that_was_already_saved(
        self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess
    ):
        character = access.new_character("Aragorn")
        await repository.save(character)

        character.name = "Strider"
        await repository.save(character)

        found = await repository.find_by_id_in(character.id, access)
        assert found is not None
        assert found.name == "Strider"


class TestFindByIdIn:
    async def test_returns_character_when_found(
        self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess
    ):
        character = access.new_character("Aragorn")
        await repository.save(character)

        result = await repository.find_by_id_in(character.id, access)

        assert result is not None
        assert result.id == character.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess):
        assert await repository.find_by_id_in(uuid.uuid4(), access) is None

    async def test_returns_none_for_a_character_at_another_table(
        self,
        repository: SqlAlchemyCharacterRepository,
        access: CampaignAccess,
        other_access: CampaignAccess,
    ):
        character = other_access.new_character("Aragorn")
        await repository.save(character)

        assert await repository.find_by_id_in(character.id, access) is None


class TestFindAllIn:
    async def test_returns_the_characters_at_that_table(
        self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess
    ):
        await repository.save(access.new_character("Aragorn"))
        await repository.save(access.new_character("Legolas"))

        names = [c.name for c in await repository.find_all_in(access)]

        assert "Aragorn" in names
        assert "Legolas" in names

    async def test_leaves_out_characters_at_another_table(
        self,
        repository: SqlAlchemyCharacterRepository,
        access: CampaignAccess,
        other_access: CampaignAccess,
    ):
        await repository.save(access.new_character("Aragorn"))
        await repository.save(other_access.new_character("Boromir"))

        assert [c.name for c in await repository.find_all_in(access)] == ["Aragorn"]

    async def test_returns_empty_list_for_an_empty_table(
        self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess
    ):
        assert await repository.find_all_in(access) == []


class TestDeleteIn:
    async def test_removes_the_character(self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess):
        character = access.new_character("Aragorn")
        await repository.save(character)

        await repository.delete_in(character.id, access)

        assert await repository.find_by_id_in(character.id, access) is None

    async def test_leaves_the_other_sheets_at_the_table(
        self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess
    ):
        doomed = access.new_character("Aragorn")
        await repository.save(doomed)
        await repository.save(access.new_character("Legolas"))

        await repository.delete_in(doomed.id, access)

        assert [c.name for c in await repository.find_all_in(access)] == ["Legolas"]

    async def test_deleting_an_unknown_id_is_not_an_error(
        self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess
    ):
        await repository.delete_in(uuid.uuid4(), access)

    async def test_leaves_a_character_at_another_table_standing(
        self,
        repository: SqlAlchemyCharacterRepository,
        access: CampaignAccess,
        other_access: CampaignAccess,
    ):
        character = other_access.new_character("Boromir")
        await repository.save(character)

        await repository.delete_in(character.id, access)

        assert await repository.find_by_id_in(character.id, other_access) is not None


class TestDeleteAllIn:
    async def test_empties_the_table(self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess):
        await repository.save(access.new_character("Aragorn"))
        await repository.save(access.new_character("Legolas"))

        await repository.delete_all_in(access)

        assert await repository.find_all_in(access) == []

    async def test_leaves_the_characters_at_another_table_alone(
        self,
        repository: SqlAlchemyCharacterRepository,
        access: CampaignAccess,
        other_access: CampaignAccess,
    ):
        await repository.save(access.new_character("Aragorn"))
        await repository.save(other_access.new_character("Boromir"))

        await repository.delete_all_in(access)

        assert [c.name for c in await repository.find_all_in(other_access)] == ["Boromir"]

    async def test_emptying_an_already_empty_table_is_not_an_error(
        self, repository: SqlAlchemyCharacterRepository, access: CampaignAccess
    ):
        await repository.delete_all_in(access)
