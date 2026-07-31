import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.campaign.domain.character import Character


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyCharacterRepository:
    return SqlAlchemyCharacterRepository(db)


@pytest.fixture
def owner_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def campaign_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_campaign_id() -> uuid.UUID:
    return uuid.uuid4()


class TestSave:
    async def test_returns_the_saved_character(
        self, repository: SqlAlchemyCharacterRepository, owner_id: uuid.UUID, campaign_id: uuid.UUID
    ):
        character = Character(name="Aragorn", owner_id=owner_id, campaign_id=campaign_id)

        assert await repository.save(character) == character

    async def test_persists_character(
        self, repository: SqlAlchemyCharacterRepository, owner_id: uuid.UUID, campaign_id: uuid.UUID
    ):
        character = Character(
            name="Aragorn", owner_id=owner_id, campaign_id=campaign_id, description="A ranger of the North"
        )
        await repository.save(character)

        found = await repository.find_by_id_in(character.id, campaign_id)

        assert found is not None
        assert found.name == "Aragorn"
        assert found.description == "A ranger of the North"
        assert found.owner_id == owner_id
        assert found.campaign_id == campaign_id

    async def test_updates_a_character_that_was_already_saved(
        self, repository: SqlAlchemyCharacterRepository, owner_id: uuid.UUID, campaign_id: uuid.UUID
    ):
        character = Character(name="Aragorn", owner_id=owner_id, campaign_id=campaign_id)
        await repository.save(character)

        character.name = "Strider"
        await repository.save(character)

        found = await repository.find_by_id_in(character.id, campaign_id)
        assert found is not None
        assert found.name == "Strider"


class TestFindByIdIn:
    async def test_returns_character_when_found(
        self, repository: SqlAlchemyCharacterRepository, owner_id: uuid.UUID, campaign_id: uuid.UUID
    ):
        character = Character(name="Aragorn", owner_id=owner_id, campaign_id=campaign_id)
        await repository.save(character)

        result = await repository.find_by_id_in(character.id, campaign_id)

        assert result is not None
        assert result.id == character.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyCharacterRepository, campaign_id: uuid.UUID):
        assert await repository.find_by_id_in(uuid.uuid4(), campaign_id) is None

    async def test_returns_none_for_a_character_at_another_table(
        self,
        repository: SqlAlchemyCharacterRepository,
        owner_id: uuid.UUID,
        campaign_id: uuid.UUID,
        other_campaign_id: uuid.UUID,
    ):
        character = Character(name="Aragorn", owner_id=owner_id, campaign_id=other_campaign_id)
        await repository.save(character)

        assert await repository.find_by_id_in(character.id, campaign_id) is None


class TestFindAllIn:
    async def test_returns_the_characters_at_that_table(
        self, repository: SqlAlchemyCharacterRepository, owner_id: uuid.UUID, campaign_id: uuid.UUID
    ):
        await repository.save(Character(name="Aragorn", owner_id=owner_id, campaign_id=campaign_id))
        await repository.save(Character(name="Legolas", owner_id=owner_id, campaign_id=campaign_id))

        names = [c.name for c in await repository.find_all_in(campaign_id)]

        assert "Aragorn" in names
        assert "Legolas" in names

    async def test_leaves_out_characters_at_another_table(
        self,
        repository: SqlAlchemyCharacterRepository,
        owner_id: uuid.UUID,
        campaign_id: uuid.UUID,
        other_campaign_id: uuid.UUID,
    ):
        await repository.save(Character(name="Aragorn", owner_id=owner_id, campaign_id=campaign_id))
        await repository.save(Character(name="Boromir", owner_id=owner_id, campaign_id=other_campaign_id))

        assert [c.name for c in await repository.find_all_in(campaign_id)] == ["Aragorn"]

    async def test_returns_empty_list_for_an_empty_table(
        self, repository: SqlAlchemyCharacterRepository, campaign_id: uuid.UUID
    ):
        assert await repository.find_all_in(campaign_id) == []
