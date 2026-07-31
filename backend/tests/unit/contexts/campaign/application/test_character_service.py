import uuid
from uuid import UUID

import pytest

from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.application.character_service import CampaignNotAvailable, CharacterService
from tests.unit.contexts.campaign.application.fakes import FakeCharacterRepository


@pytest.fixture
def game_master(owner_id: UUID):
    return owner_id


@pytest.fixture
def stranger(someone_else: UUID):
    return someone_else


@pytest.fixture
def service(characters: FakeCharacterRepository, campaigns: CampaignService):
    return CharacterService(characters, campaigns)


@pytest.fixture
async def campaign_id(campaigns: CampaignService, game_master: UUID):
    campaign = await campaigns.create("The Hollow Beneath Greyfen", game_master)
    return campaign.id


class TestCreate:
    async def test_returns_character_with_correct_fields(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        character = await service.create(campaign_id, game_master, "Aragorn", "A ranger of the North")

        assert character.name == "Aragorn"
        assert character.description == "A ranger of the North"
        assert character.owner_id == game_master
        assert character.campaign_id == campaign_id

    async def test_description_is_optional(self, service: CharacterService, game_master: UUID, campaign_id: UUID):
        character = await service.create(campaign_id, game_master, "Aragorn")

        assert character.description is None

    async def test_refuses_a_campaign_the_creator_cannot_reach(
        self, service: CharacterService, stranger: UUID, campaign_id: UUID
    ):
        with pytest.raises(CampaignNotAvailable):
            await service.create(campaign_id, stranger, "Aragorn")

    async def test_refuses_a_campaign_that_does_not_exist(self, service: CharacterService, game_master: UUID):
        with pytest.raises(CampaignNotAvailable):
            await service.create(uuid.uuid4(), game_master, "Aragorn")


class TestGetFor:
    async def test_the_game_master_sees_a_character_at_their_table(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn")

        assert await service.get_for(created.id, campaign_id, game_master) == created

    async def test_a_stranger_cannot_reach_the_table_at_all(
        self, service: CharacterService, game_master: UUID, stranger: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn")

        with pytest.raises(CampaignNotAvailable):
            await service.get_for(created.id, campaign_id, stranger)

    async def test_returns_none_when_not_found(self, service: CharacterService, game_master: UUID, campaign_id: UUID):
        assert await service.get_for(uuid.uuid4(), campaign_id, game_master) is None

    async def test_returns_none_for_a_character_at_another_table(
        self, service: CharacterService, campaigns: CampaignService, game_master: UUID, campaign_id: UUID
    ):
        """The id is real and both tables are mine — it is still not at this one."""
        other = await campaigns.create("Fen Wardens", game_master)
        created = await service.create(other.id, game_master, "Aragorn")

        assert await service.get_for(created.id, campaign_id, game_master) is None


class TestListFor:
    async def test_returns_empty_list_when_the_table_is_empty(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        assert await service.list_for(campaign_id, game_master) == []

    async def test_returns_the_characters_at_that_table(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        await service.create(campaign_id, game_master, "Aragorn")
        await service.create(campaign_id, game_master, "Legolas")

        assert len(await service.list_for(campaign_id, game_master)) == 2

    async def test_leaves_out_characters_at_another_table(
        self, service: CharacterService, campaigns: CampaignService, game_master: UUID, campaign_id: UUID
    ):
        other = await campaigns.create("Fen Wardens", game_master)
        await service.create(campaign_id, game_master, "Aragorn")
        await service.create(other.id, game_master, "Boromir")

        assert [c.name for c in await service.list_for(campaign_id, game_master)] == ["Aragorn"]

    async def test_a_stranger_cannot_reach_the_table(
        self, service: CharacterService, stranger: UUID, campaign_id: UUID
    ):
        with pytest.raises(CampaignNotAvailable):
            await service.list_for(campaign_id, stranger)


class TestUpdate:
    async def test_returns_the_character_with_its_new_name(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn")

        updated = await service.update(created.id, campaign_id, game_master, "Strider", "Also called Elessar")

        assert updated is not None
        assert updated.name == "Strider"
        assert updated.description == "Also called Elessar"

    async def test_clears_a_description_that_is_left_out(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn", "A ranger of the North")

        updated = await service.update(created.id, campaign_id, game_master, "Aragorn")

        assert updated is not None
        assert updated.description is None

    async def test_does_not_change_who_owns_the_character(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn")

        updated = await service.update(created.id, campaign_id, game_master, "Strider")

        assert updated is not None
        assert updated.owner_id == game_master

    async def test_returns_none_when_not_found(self, service: CharacterService, game_master: UUID, campaign_id: UUID):
        assert await service.update(uuid.uuid4(), campaign_id, game_master, "Strider") is None

    async def test_a_stranger_cannot_reach_the_table(
        self, service: CharacterService, game_master: UUID, stranger: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn")

        with pytest.raises(CampaignNotAvailable):
            await service.update(created.id, campaign_id, stranger, "Stolen")

    async def test_a_stranger_leaves_the_character_untouched(
        self, service: CharacterService, game_master: UUID, stranger: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn")

        with pytest.raises(CampaignNotAvailable):
            await service.update(created.id, campaign_id, stranger, "Stolen")

        found = await service.get_for(created.id, campaign_id, game_master)
        assert found is not None
        assert found.name == "Aragorn"


class TestDelete:
    async def test_removes_the_character(self, service: CharacterService, game_master: UUID, campaign_id: UUID):
        created = await service.create(campaign_id, game_master, "Aragorn")

        assert await service.delete(created.id, campaign_id, game_master) is True
        assert await service.get_for(created.id, campaign_id, game_master) is None

    async def test_leaves_the_other_sheets_at_the_table(
        self, service: CharacterService, game_master: UUID, campaign_id: UUID
    ):
        doomed = await service.create(campaign_id, game_master, "Aragorn")
        await service.create(campaign_id, game_master, "Legolas")

        await service.delete(doomed.id, campaign_id, game_master)

        assert [c.name for c in await service.list_for(campaign_id, game_master)] == ["Legolas"]

    async def test_returns_false_when_not_found(self, service: CharacterService, game_master: UUID, campaign_id: UUID):
        assert await service.delete(uuid.uuid4(), campaign_id, game_master) is False

    async def test_returns_false_for_a_character_at_another_table(
        self, service: CharacterService, campaigns: CampaignService, game_master: UUID, campaign_id: UUID
    ):
        """The id is real and both tables are mine — it is still not at this one."""
        other = await campaigns.create("Fen Wardens", game_master)
        created = await service.create(other.id, game_master, "Aragorn")

        assert await service.delete(created.id, campaign_id, game_master) is False

    async def test_a_character_reached_through_the_wrong_table_survives(
        self, service: CharacterService, campaigns: CampaignService, game_master: UUID, campaign_id: UUID
    ):
        other = await campaigns.create("Fen Wardens", game_master)
        created = await service.create(other.id, game_master, "Aragorn")

        await service.delete(created.id, campaign_id, game_master)

        assert await service.get_for(created.id, other.id, game_master) is not None

    async def test_a_stranger_cannot_reach_the_table(
        self, service: CharacterService, game_master: UUID, stranger: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn")

        with pytest.raises(CampaignNotAvailable):
            await service.delete(created.id, campaign_id, stranger)

    async def test_a_stranger_leaves_the_character_standing(
        self, service: CharacterService, game_master: UUID, stranger: UUID, campaign_id: UUID
    ):
        created = await service.create(campaign_id, game_master, "Aragorn")

        with pytest.raises(CampaignNotAvailable):
            await service.delete(created.id, campaign_id, stranger)

        assert await service.get_for(created.id, campaign_id, game_master) is not None
