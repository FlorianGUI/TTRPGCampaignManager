import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.domain.campaign import Campaign


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyCampaignRepository:
    return SqlAlchemyCampaignRepository(db)


@pytest.fixture
def owner_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def someone_else() -> uuid.UUID:
    return uuid.uuid4()


class TestSave:
    async def test_returns_the_saved_campaign(self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID):
        campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id)

        assert await repository.save(campaign) == campaign

    async def test_persists_campaign(self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID):
        campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id, description="A drowned village")
        await repository.save(campaign)

        found = await repository.find_by_id_for(campaign.id, owner_id)

        assert found is not None
        assert found.name == "The Hollow Beneath Greyfen"
        assert found.description == "A drowned village"
        assert found.owner_id == owner_id

    async def test_updates_a_campaign_that_was_already_saved(
        self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID
    ):
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        campaign.name = "The Hollow Beneath Greyfen"
        await repository.save(campaign)

        found = await repository.find_by_id_for(campaign.id, owner_id)
        assert found is not None
        assert found.name == "The Hollow Beneath Greyfen"


class TestFindByIdFor:
    async def test_returns_campaign_when_found(self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID):
        campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        result = await repository.find_by_id_for(campaign.id, owner_id)

        assert result is not None
        assert result.id == campaign.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID):
        assert await repository.find_by_id_for(uuid.uuid4(), owner_id) is None

    async def test_returns_none_when_owned_by_someone_else(
        self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID, someone_else: uuid.UUID
    ):
        campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        assert await repository.find_by_id_for(campaign.id, someone_else) is None


class TestFindAllFor:
    async def test_returns_the_campaigns_of_that_owner(
        self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID
    ):
        await repository.save(Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id))
        await repository.save(Campaign(name="Fen Wardens", owner_id=owner_id))

        names = [c.name for c in await repository.find_all_for(owner_id)]

        assert "The Hollow Beneath Greyfen" in names
        assert "Fen Wardens" in names

    async def test_leaves_out_the_campaigns_of_other_owners(
        self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID, someone_else: uuid.UUID
    ):
        await repository.save(Campaign(name="Mine", owner_id=owner_id))
        await repository.save(Campaign(name="Theirs", owner_id=someone_else))

        assert [c.name for c in await repository.find_all_for(owner_id)] == ["Mine"]


class TestFindIdsFor:
    async def test_returns_the_ids_of_that_owners_campaigns(
        self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID
    ):
        campaign = Campaign(name="Mine", owner_id=owner_id)
        await repository.save(campaign)

        assert await repository.find_ids_for(owner_id) == [campaign.id]

    async def test_leaves_out_the_campaigns_of_other_owners(
        self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID, someone_else: uuid.UUID
    ):
        await repository.save(Campaign(name="Theirs", owner_id=someone_else))

        assert await repository.find_ids_for(owner_id) == []
