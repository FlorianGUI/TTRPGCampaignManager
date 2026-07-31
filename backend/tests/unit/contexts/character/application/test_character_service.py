import uuid
from collections.abc import Sequence
from uuid import UUID

import pytest

from app.contexts.character.application.character_service import CampaignNotAvailable, CharacterService
from app.contexts.character.domain.character import Character
from app.contexts.character.domain.ports.campaign_access import CampaignAccess
from app.contexts.character.domain.ports.character_repository import CharacterRepository


class FakeCharacterRepository(CharacterRepository):
    def __init__(self):
        self._store: dict[UUID, Character] = {}

    async def save(self, character: Character) -> Character:
        self._store[character.id] = character
        return character

    async def find_by_id_visible_to(self, id: UUID, viewer_id: UUID, campaign_ids: Sequence[UUID]) -> Character | None:
        character = self._store.get(id)
        if character is None or not self._visible(character, viewer_id, campaign_ids):
            return None
        return character

    async def find_all_visible_to(self, viewer_id: UUID, campaign_ids: Sequence[UUID]) -> list[Character]:
        return [c for c in self._store.values() if self._visible(c, viewer_id, campaign_ids)]

    @staticmethod
    def _visible(character: Character, viewer_id: UUID, campaign_ids: Sequence[UUID]) -> bool:
        return character.owner_id == viewer_id or character.campaign_id in campaign_ids


class FakeCampaignAccess(CampaignAccess):
    """Who runs what, without a campaign context to ask."""

    def __init__(self, owned: dict[UUID, list[UUID]] | None = None):
        self._owned = owned or {}

    async def campaign_ids_owned_by(self, user_id: UUID) -> list[UUID]:
        return self._owned.get(user_id, [])


@pytest.fixture
def player():
    return uuid.uuid4()


@pytest.fixture
def game_master():
    return uuid.uuid4()


@pytest.fixture
def stranger():
    return uuid.uuid4()


@pytest.fixture
def campaign_id():
    return uuid.uuid4()


@pytest.fixture
def campaigns(game_master: UUID, campaign_id: UUID):
    return FakeCampaignAccess({game_master: [campaign_id]})


@pytest.fixture
def service(campaigns: FakeCampaignAccess):
    return CharacterService(FakeCharacterRepository(), campaigns)


class TestCreate:
    async def test_returns_character_with_correct_fields(self, service: CharacterService, player: UUID):
        character = await service.create("Aragorn", "Ranger", player)

        assert character.name == "Aragorn"
        assert character.character_class == "Ranger"
        assert character.owner_id == player

    async def test_starts_at_no_campaign(self, service: CharacterService, player: UUID):
        character = await service.create("Aragorn", "Ranger", player)

        assert character.campaign_id is None

    async def test_can_start_at_a_campaign_the_creator_runs(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        character = await service.create("Aragorn", "Ranger", game_master, campaign_id)

        assert character.campaign_id == campaign_id

    async def test_refuses_a_campaign_the_creator_does_not_run(
        self, service: CharacterService, player: UUID, campaign_id: UUID
    ):
        with pytest.raises(CampaignNotAvailable):
            await service.create("Aragorn", "Ranger", player, campaign_id)

    async def test_refuses_a_campaign_that_does_not_exist(self, service: CharacterService, player: UUID):
        with pytest.raises(CampaignNotAvailable):
            await service.create("Aragorn", "Ranger", player, uuid.uuid4())


class TestGetFor:
    async def test_the_owner_sees_their_character(self, service: CharacterService, player: UUID):
        created = await service.create("Aragorn", "Ranger", player)

        assert await service.get_for(created.id, player) == created

    async def test_the_game_master_sees_a_character_at_their_table(
        self, service: CharacterService, player: UUID, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create("Aragorn", "Ranger", player)
        created.campaign_id = campaign_id

        assert await service.get_for(created.id, game_master) == created

    async def test_a_stranger_sees_nothing(self, service: CharacterService, player: UUID, stranger: UUID):
        created = await service.create("Aragorn", "Ranger", player)

        assert await service.get_for(created.id, stranger) is None

    async def test_a_game_master_sees_nothing_once_the_character_leaves_their_table(
        self, service: CharacterService, player: UUID, game_master: UUID
    ):
        created = await service.create("Aragorn", "Ranger", player)

        assert await service.get_for(created.id, game_master) is None

    async def test_returns_none_when_not_found(self, service: CharacterService, player: UUID):
        assert await service.get_for(uuid.uuid4(), player) is None


class TestListFor:
    async def test_returns_empty_list_when_nothing_is_visible(self, service: CharacterService, stranger: UUID):
        assert await service.list_for(stranger) == []

    async def test_returns_my_own_characters(self, service: CharacterService, player: UUID):
        await service.create("Aragorn", "Ranger", player)
        await service.create("Legolas", "Archer", player)

        assert len(await service.list_for(player)) == 2

    async def test_returns_characters_at_a_table_i_run(
        self, service: CharacterService, player: UUID, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create("Aragorn", "Ranger", player)
        created.campaign_id = campaign_id

        assert [c.name for c in await service.list_for(game_master)] == ["Aragorn"]

    async def test_leaves_out_characters_i_can_reach_through_neither_link(
        self, service: CharacterService, player: UUID, stranger: UUID
    ):
        await service.create("Aragorn", "Ranger", player)

        assert await service.list_for(stranger) == []


class TestUpdate:
    async def test_the_owner_can_edit_their_character(self, service: CharacterService, player: UUID):
        created = await service.create("Aragorn", "Ranger", player)

        updated = await service.update(created.id, player, "Strider", "Ranger", 5)

        assert updated is not None
        assert updated.name == "Strider"
        assert updated.level == 5

    async def test_the_game_master_can_edit_a_character_at_their_table(
        self, service: CharacterService, player: UUID, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create("Aragorn", "Ranger", player)
        created.campaign_id = campaign_id

        updated = await service.update(created.id, game_master, "Strider", "Ranger", 5, campaign_id)

        assert updated is not None
        assert updated.name == "Strider"

    async def test_editing_does_not_change_who_owns_the_character(
        self, service: CharacterService, player: UUID, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create("Aragorn", "Ranger", player)
        created.campaign_id = campaign_id

        updated = await service.update(created.id, game_master, "Strider", "Ranger", 5, campaign_id)

        assert updated is not None
        assert updated.owner_id == player

    async def test_a_stranger_cannot_edit(self, service: CharacterService, player: UUID, stranger: UUID):
        created = await service.create("Aragorn", "Ranger", player)

        assert await service.update(created.id, stranger, "Stolen", "Thief", 1) is None

    async def test_a_stranger_leaves_the_character_untouched(
        self, service: CharacterService, player: UUID, stranger: UUID
    ):
        created = await service.create("Aragorn", "Ranger", player)

        await service.update(created.id, stranger, "Stolen", "Thief", 1)

        found = await service.get_for(created.id, player)
        assert found is not None
        assert found.name == "Aragorn"

    async def test_returns_none_when_not_found(self, service: CharacterService, player: UUID):
        assert await service.update(uuid.uuid4(), player, "Aragorn", "Ranger", 1) is None

    async def test_can_join_a_campaign_the_editor_runs(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create("Aragorn", "Ranger", game_master)

        updated = await service.update(created.id, game_master, "Aragorn", "Ranger", 1, campaign_id)

        assert updated is not None
        assert updated.campaign_id == campaign_id

    async def test_leaving_the_campaign_out_takes_the_character_off_the_table(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create("Aragorn", "Ranger", game_master, campaign_id)

        updated = await service.update(created.id, game_master, "Aragorn", "Ranger", 1)

        assert updated is not None
        assert updated.campaign_id is None

    async def test_refuses_a_campaign_the_editor_does_not_run(
        self, service: CharacterService, player: UUID, campaign_id: UUID
    ):
        created = await service.create("Aragorn", "Ranger", player)

        with pytest.raises(CampaignNotAvailable):
            await service.update(created.id, player, "Aragorn", "Ranger", 1, campaign_id)

    async def test_an_unreachable_character_is_absent_before_the_campaign_is_judged(
        self, service: CharacterService, player: UUID, stranger: UUID, campaign_id: UUID
    ):
        """No leak either way round: a stranger naming a real campaign still gets None."""
        created = await service.create("Aragorn", "Ranger", player)

        assert await service.update(created.id, stranger, "Stolen", "Thief", 1, campaign_id) is None
