import uuid
from uuid import UUID

import pytest

from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.domain.access import CampaignNotReachable
from tests.unit.contexts.campaign.application.fakes import FakeCharacterRepository


@pytest.fixture
def service(campaigns: CampaignService):
    return campaigns


class TestCreate:
    async def test_returns_campaign_with_correct_fields(self, service: CampaignService, owner_id: UUID):
        campaign = await service.create("The Hollow Beneath Greyfen", owner_id, "A drowned village")

        assert campaign.name == "The Hollow Beneath Greyfen"
        assert campaign.owner_id == owner_id
        assert campaign.description == "A drowned village"

    async def test_description_is_optional(self, service: CampaignService, owner_id: UUID):
        campaign = await service.create("The Hollow Beneath Greyfen", owner_id)

        assert campaign.description is None

    async def test_gives_each_campaign_its_own_id(self, service: CampaignService, owner_id: UUID):
        first = await service.create("The Hollow Beneath Greyfen", owner_id)
        second = await service.create("Fen Wardens", owner_id)

        assert first.id != second.id


class TestGetFor:
    async def test_returns_campaign_when_found(self, service: CampaignService, owner_id: UUID):
        created = await service.create("The Hollow Beneath Greyfen", owner_id)

        assert await service.get_for(created.id, owner_id) == created

    async def test_raises_when_not_found(self, service: CampaignService, owner_id: UUID):
        with pytest.raises(CampaignNotReachable):
            await service.get_for(uuid.uuid4(), owner_id)

    async def test_raises_when_owned_by_someone_else(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("The Hollow Beneath Greyfen", owner_id)

        with pytest.raises(CampaignNotReachable):
            await service.get_for(created.id, someone_else)


class TestListFor:
    async def test_returns_empty_list_when_no_campaigns(self, service: CampaignService, owner_id: UUID):
        assert await service.list_for(owner_id) == []

    async def test_leaves_out_the_campaigns_of_other_owners(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        await service.create("The Hollow Beneath Greyfen", owner_id)
        await service.create("Someone elses table", someone_else)

        result = await service.list_for(owner_id)

        assert [c.name for c in result] == ["The Hollow Beneath Greyfen"]


class TestAccessTo:
    async def test_grants_a_token_for_my_own_campaign(self, service: CampaignService, owner_id: UUID):
        created = await service.create("The Hollow Beneath Greyfen", owner_id)

        access = await service.access_to(created.id, owner_id)

        assert access is not None
        assert access.campaign_id == created.id
        assert access.viewer_id == owner_id

    async def test_grants_nothing_for_a_campaign_that_does_not_exist(self, service: CampaignService, owner_id: UUID):
        with pytest.raises(CampaignNotReachable):
            await service.access_to(uuid.uuid4(), owner_id)

    async def test_grants_nothing_for_a_campaign_owned_by_someone_else(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("The Hollow Beneath Greyfen", owner_id)

        with pytest.raises(CampaignNotReachable):
            await service.access_to(created.id, someone_else)


class TestUpdate:
    async def test_returns_the_campaign_with_its_new_name(self, service: CampaignService, owner_id: UUID):
        created = await service.create("Greyfen", owner_id)

        updated = await service.update(created.id, owner_id, "The Hollow Beneath Greyfen", "A drowned village")

        assert updated is not None
        assert updated.name == "The Hollow Beneath Greyfen"
        assert updated.description == "A drowned village"

    async def test_clears_a_description_that_is_left_out(self, service: CampaignService, owner_id: UUID):
        created = await service.create("Greyfen", owner_id, "A drowned village")

        updated = await service.update(created.id, owner_id, "Greyfen")

        assert updated is not None
        assert updated.description is None

    async def test_raises_when_not_found(self, service: CampaignService, owner_id: UUID):
        with pytest.raises(CampaignNotReachable):
            await service.update(uuid.uuid4(), owner_id, "Greyfen")

    async def test_raises_when_owned_by_someone_else(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("Greyfen", owner_id)

        with pytest.raises(CampaignNotReachable):
            await service.update(created.id, someone_else, "Not yours")

    async def test_leaves_a_campaign_owned_by_someone_else_untouched(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("Greyfen", owner_id)

        with pytest.raises(CampaignNotReachable):
            await service.update(created.id, someone_else, "Not yours")

        assert (await service.get_for(created.id, owner_id)).name == "Greyfen"


class TestDelete:
    async def test_removes_the_campaign(self, service: CampaignService, owner_id: UUID):
        created = await service.create("Greyfen", owner_id)

        await service.delete(created.id, owner_id)

        with pytest.raises(CampaignNotReachable):
            await service.get_for(created.id, owner_id)

    async def test_takes_the_characters_at_that_table_with_it(
        self, service: CampaignService, characters: FakeCharacterRepository, owner_id: UUID
    ):
        created = await service.create("Greyfen", owner_id)
        access = await service.access_to(created.id, owner_id)
        await characters.save(access.new_character("Aragorn"))

        await service.delete(created.id, owner_id)

        assert await characters.find_all_in(access) == []

    async def test_leaves_the_characters_at_other_tables_alone(
        self, service: CampaignService, characters: FakeCharacterRepository, owner_id: UUID
    ):
        doomed = await service.create("Greyfen", owner_id)
        spared = await service.create("Fen Wardens", owner_id)
        elsewhere = await service.access_to(spared.id, owner_id)
        await characters.save(elsewhere.new_character("Legolas"))

        await service.delete(doomed.id, owner_id)

        assert [c.name for c in await characters.find_all_in(elsewhere)] == ["Legolas"]

    async def test_deleting_an_empty_campaign_is_not_an_error(self, service: CampaignService, owner_id: UUID):
        created = await service.create("Greyfen", owner_id)

        await service.delete(created.id, owner_id)

    async def test_raises_when_not_found(self, service: CampaignService, owner_id: UUID):
        with pytest.raises(CampaignNotReachable):
            await service.delete(uuid.uuid4(), owner_id)

    async def test_raises_when_owned_by_someone_else(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("Greyfen", owner_id)

        with pytest.raises(CampaignNotReachable):
            await service.delete(created.id, someone_else)

    async def test_leaves_a_campaign_owned_by_someone_else_standing(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("Greyfen", owner_id)

        with pytest.raises(CampaignNotReachable):
            await service.delete(created.id, someone_else)

        assert await service.get_for(created.id, owner_id) is not None

    async def test_leaves_the_characters_of_a_campaign_it_could_not_delete(
        self,
        service: CampaignService,
        characters: FakeCharacterRepository,
        owner_id: UUID,
        someone_else: UUID,
    ):
        created = await service.create("Greyfen", owner_id)
        access = await service.access_to(created.id, owner_id)
        await characters.save(access.new_character("Aragorn"))

        with pytest.raises(CampaignNotReachable):
            await service.delete(created.id, someone_else)

        assert [c.name for c in await characters.find_all_in(access)] == ["Aragorn"]
