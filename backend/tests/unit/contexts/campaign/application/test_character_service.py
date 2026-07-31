import uuid
from uuid import UUID

import pytest

from app.common.access import Unsafe
from app.contexts.campaign.application.character_service import CharacterService
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.character import CharacterNotAvailable
from app.contexts.campaign.domain.character_access import CharacterAccess
from tests.unit.contexts.campaign.application.fakes import FakeCharacterRepository

# Every test here starts from a token, because every method does. Whether a viewer may
# have one is the campaign's question and is answered in test_campaign_service and
# test_access; what is left for this service is what happens once they do.


@pytest.fixture
def game_master(owner_id: UUID):
    return owner_id


@pytest.fixture
def access(game_master: UUID) -> CharacterAccess:
    campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=game_master)
    return CampaignAccess(game_master).characters_at(Unsafe(campaign))


@pytest.fixture
def other_access(game_master: UUID) -> CharacterAccess:
    return CampaignAccess(game_master).characters_at(Unsafe(Campaign(name="Fen Wardens", owner_id=game_master)))


@pytest.fixture
def service(characters: FakeCharacterRepository):
    return CharacterService(characters)


class TestCreate:
    async def test_returns_character_with_correct_fields(
        self, service: CharacterService, access: CharacterAccess, game_master: UUID
    ):
        character = await service.create(access, "Aragorn", "A ranger of the North")

        assert character.name == "Aragorn"
        assert character.description == "A ranger of the North"
        assert character.owner_id == game_master
        assert character.campaign_id == access.campaign_id

    async def test_description_is_optional(self, service: CharacterService, access: CharacterAccess):
        character = await service.create(access, "Aragorn")

        assert character.description is None


class TestGetFor:
    async def test_the_game_master_sees_a_character_at_their_table(
        self, service: CharacterService, access: CharacterAccess
    ):
        created = await service.create(access, "Aragorn")

        assert await service.get_for(created.id, access) == created

    async def test_raises_when_not_found(self, service: CharacterService, access: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            await service.get_for(uuid.uuid4(), access)

    async def test_raises_for_a_character_at_another_table(
        self, service: CharacterService, access: CharacterAccess, other_access: CharacterAccess
    ):
        """The id is real and both tables are mine — it is still not at this one."""
        created = await service.create(other_access, "Aragorn")

        with pytest.raises(CharacterNotAvailable):
            await service.get_for(created.id, access)


class TestListFor:
    async def test_returns_empty_list_when_the_table_is_empty(self, service: CharacterService, access: CharacterAccess):
        assert await service.list_for(access) == []

    async def test_returns_the_characters_at_that_table(self, service: CharacterService, access: CharacterAccess):
        await service.create(access, "Aragorn")
        await service.create(access, "Legolas")

        assert len(await service.list_for(access)) == 2

    async def test_leaves_out_characters_at_another_table(
        self, service: CharacterService, access: CharacterAccess, other_access: CharacterAccess
    ):
        await service.create(access, "Aragorn")
        await service.create(other_access, "Boromir")

        assert [c.name for c in await service.list_for(access)] == ["Aragorn"]


class TestUpdate:
    async def test_returns_the_character_with_its_new_name(self, service: CharacterService, access: CharacterAccess):
        created = await service.create(access, "Aragorn")

        updated = await service.update(created.id, access, "Strider", "Also called Elessar")

        assert updated is not None
        assert updated.name == "Strider"
        assert updated.description == "Also called Elessar"

    async def test_clears_a_description_that_is_left_out(self, service: CharacterService, access: CharacterAccess):
        created = await service.create(access, "Aragorn", "A ranger of the North")

        updated = await service.update(created.id, access, "Aragorn")

        assert updated is not None
        assert updated.description is None

    async def test_does_not_change_who_owns_the_character(
        self, service: CharacterService, access: CharacterAccess, game_master: UUID
    ):
        created = await service.create(access, "Aragorn")

        updated = await service.update(created.id, access, "Strider")

        assert updated is not None
        assert updated.owner_id == game_master

    async def test_raises_when_not_found(self, service: CharacterService, access: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            await service.update(uuid.uuid4(), access, "Strider")

    async def test_raises_for_a_character_at_another_table(
        self, service: CharacterService, access: CharacterAccess, other_access: CharacterAccess
    ):
        created = await service.create(other_access, "Aragorn")

        with pytest.raises(CharacterNotAvailable):
            await service.update(created.id, access, "Stolen")

    async def test_a_character_reached_through_the_wrong_table_is_untouched(
        self, service: CharacterService, access: CharacterAccess, other_access: CharacterAccess
    ):
        created = await service.create(other_access, "Aragorn")

        with pytest.raises(CharacterNotAvailable):
            await service.update(created.id, access, "Stolen")

        assert (await service.get_for(created.id, other_access)).name == "Aragorn"


class TestDelete:
    async def test_removes_the_character(self, service: CharacterService, access: CharacterAccess):
        created = await service.create(access, "Aragorn")

        await service.delete(created.id, access)

        with pytest.raises(CharacterNotAvailable):
            await service.get_for(created.id, access)

    async def test_leaves_the_other_sheets_at_the_table(self, service: CharacterService, access: CharacterAccess):
        doomed = await service.create(access, "Aragorn")
        await service.create(access, "Legolas")

        await service.delete(doomed.id, access)

        assert [c.name for c in await service.list_for(access)] == ["Legolas"]

    async def test_raises_when_not_found(self, service: CharacterService, access: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            await service.delete(uuid.uuid4(), access)

    async def test_raises_for_a_character_at_another_table(
        self, service: CharacterService, access: CharacterAccess, other_access: CharacterAccess
    ):
        created = await service.create(other_access, "Aragorn")

        with pytest.raises(CharacterNotAvailable):
            await service.delete(created.id, access)

    async def test_a_character_reached_through_the_wrong_table_survives(
        self, service: CharacterService, access: CharacterAccess, other_access: CharacterAccess
    ):
        created = await service.create(other_access, "Aragorn")

        with pytest.raises(CharacterNotAvailable):
            await service.delete(created.id, access)

        assert await service.get_for(created.id, other_access) is not None
