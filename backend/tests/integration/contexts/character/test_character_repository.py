import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.character.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.character.domain.character import Character


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyCharacterRepository:
    return SqlAlchemyCharacterRepository(db)


@pytest.fixture
def player() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def game_master() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def stranger() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def campaign_id() -> uuid.UUID:
    return uuid.uuid4()


class TestSave:
    async def test_returns_the_saved_character(self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=player)

        assert await repository.save(character) == character

    async def test_persists_character(self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=player)
        await repository.save(character)

        found = await repository.find_by_id_visible_to(character.id, player, [])

        assert found is not None
        assert found.name == "Aragorn"
        assert found.character_class == "Ranger"
        assert found.owner_id == player
        assert found.campaign_id is None

    async def test_persists_the_campaign_link(
        self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID, campaign_id: uuid.UUID
    ):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=player, campaign_id=campaign_id)
        await repository.save(character)

        found = await repository.find_by_id_visible_to(character.id, player, [])

        assert found is not None
        assert found.campaign_id == campaign_id

    async def test_updates_a_character_that_was_already_saved(
        self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID
    ):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=player)
        await repository.save(character)

        character.name = "Strider"
        character.level = 5
        await repository.save(character)

        found = await repository.find_by_id_visible_to(character.id, player, [])
        assert found is not None
        assert found.name == "Strider"
        assert found.level == 5


class TestFindByIdVisibleTo:
    async def test_the_owner_sees_their_character(self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=player)
        await repository.save(character)

        assert await repository.find_by_id_visible_to(character.id, player, []) is not None

    async def test_the_game_master_sees_a_character_at_their_table(
        self,
        repository: SqlAlchemyCharacterRepository,
        player: uuid.UUID,
        game_master: uuid.UUID,
        campaign_id: uuid.UUID,
    ):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=player, campaign_id=campaign_id)
        await repository.save(character)

        assert await repository.find_by_id_visible_to(character.id, game_master, [campaign_id]) is not None

    async def test_a_stranger_sees_nothing(
        self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID, stranger: uuid.UUID
    ):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=player)
        await repository.save(character)

        assert await repository.find_by_id_visible_to(character.id, stranger, []) is None

    async def test_a_game_master_sees_nothing_at_a_table_the_character_is_not_at(
        self,
        repository: SqlAlchemyCharacterRepository,
        player: uuid.UUID,
        game_master: uuid.UUID,
        campaign_id: uuid.UUID,
    ):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=player)
        await repository.save(character)

        assert await repository.find_by_id_visible_to(character.id, game_master, [campaign_id]) is None

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID):
        assert await repository.find_by_id_visible_to(uuid.uuid4(), player, []) is None


class TestFindAllVisibleTo:
    async def test_returns_my_own_characters(self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID):
        await repository.save(Character(name="Aragorn", character_class="Ranger", owner_id=player))
        await repository.save(Character(name="Legolas", character_class="Archer", owner_id=player))

        names = [c.name for c in await repository.find_all_visible_to(player, [])]

        assert "Aragorn" in names
        assert "Legolas" in names

    async def test_returns_characters_at_a_table_i_run(
        self,
        repository: SqlAlchemyCharacterRepository,
        player: uuid.UUID,
        game_master: uuid.UUID,
        campaign_id: uuid.UUID,
    ):
        await repository.save(
            Character(name="Aragorn", character_class="Ranger", owner_id=player, campaign_id=campaign_id)
        )

        assert [c.name for c in await repository.find_all_visible_to(game_master, [campaign_id])] == ["Aragorn"]

    async def test_leaves_out_characters_reachable_through_neither_link(
        self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID, stranger: uuid.UUID
    ):
        await repository.save(Character(name="Aragorn", character_class="Ranger", owner_id=player))

        assert await repository.find_all_visible_to(stranger, []) == []

    async def test_an_empty_campaign_list_matches_nothing_rather_than_everything(
        self, repository: SqlAlchemyCharacterRepository, player: uuid.UUID, stranger: uuid.UUID
    ):
        """The clause that would leak everything if IN () were treated as always true."""
        await repository.save(
            Character(name="Aragorn", character_class="Ranger", owner_id=player, campaign_id=uuid.uuid4())
        )

        assert await repository.find_all_visible_to(stranger, []) == []
