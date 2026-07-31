import uuid
from uuid import UUID

import pytest

from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository


class FakeCampaignRepository(CampaignRepository):
    def __init__(self):
        self._store: dict[UUID, Campaign] = {}

    async def save(self, campaign: Campaign) -> Campaign:
        self._store[campaign.id] = campaign
        return campaign

    async def find_by_id_for(self, id: UUID, owner_id: UUID) -> Campaign | None:
        campaign = self._store.get(id)
        if campaign is None or campaign.owner_id != owner_id:
            return None
        return campaign

    async def find_all_for(self, owner_id: UUID) -> list[Campaign]:
        return [c for c in self._store.values() if c.owner_id == owner_id]

    async def find_ids_for(self, owner_id: UUID) -> list[UUID]:
        return [c.id for c in self._store.values() if c.owner_id == owner_id]


@pytest.fixture
def service():
    return CampaignService(FakeCampaignRepository())


@pytest.fixture
def owner_id():
    return uuid.uuid4()


@pytest.fixture
def someone_else():
    return uuid.uuid4()


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

    async def test_returns_none_when_not_found(self, service: CampaignService, owner_id: UUID):
        assert await service.get_for(uuid.uuid4(), owner_id) is None

    async def test_returns_none_when_owned_by_someone_else(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("The Hollow Beneath Greyfen", owner_id)

        assert await service.get_for(created.id, someone_else) is None


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


class TestIdsOwnedBy:
    async def test_returns_the_ids_of_that_owners_campaigns(self, service: CampaignService, owner_id: UUID):
        first = await service.create("The Hollow Beneath Greyfen", owner_id)
        second = await service.create("Fen Wardens", owner_id)

        result = await service.ids_owned_by(owner_id)

        assert sorted(result) == sorted([first.id, second.id])

    async def test_leaves_out_the_campaigns_of_other_owners(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        mine = await service.create("The Hollow Beneath Greyfen", owner_id)
        await service.create("Someone elses table", someone_else)

        assert await service.ids_owned_by(owner_id) == [mine.id]

    async def test_returns_empty_list_for_a_user_running_nothing(self, service: CampaignService, owner_id: UUID):
        assert await service.ids_owned_by(owner_id) == []


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

    async def test_returns_none_when_not_found(self, service: CampaignService, owner_id: UUID):
        assert await service.update(uuid.uuid4(), owner_id, "Greyfen") is None

    async def test_returns_none_when_owned_by_someone_else(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("Greyfen", owner_id)

        assert await service.update(created.id, someone_else, "Not yours") is None

    async def test_leaves_a_campaign_owned_by_someone_else_untouched(
        self, service: CampaignService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("Greyfen", owner_id)

        await service.update(created.id, someone_else, "Not yours")

        found = await service.get_for(created.id, owner_id)
        assert found is not None
        assert found.name == "Greyfen"
