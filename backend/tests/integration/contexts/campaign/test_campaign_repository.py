import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.adapters.secondary.persistence.campaign_model import CampaignModel
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess


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

        found = await repository.find_by_id(campaign.id)

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

        found = await repository.find_by_id(campaign.id)
        assert found is not None
        assert found.name == "The Hollow Beneath Greyfen"


class TestFindById:
    async def test_returns_campaign_when_found(self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID):
        campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        result = await repository.find_by_id(campaign.id)

        assert result is not None
        assert result.id == campaign.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyCampaignRepository):
        assert await repository.find_by_id(uuid.uuid4()) is None

    async def test_finds_a_campaign_whoever_owns_it(
        self, repository: SqlAlchemyCampaignRepository, someone_else: uuid.UUID
    ):
        """Ownership is no longer this method's business, and that is the point.

        It used to filter on the owner, which put `owner_id ==` in a WHERE clause where
        it could not be read or tested. `campaign.readable` holds that rule now, and this
        method's whole job is to say whether a row exists.
        """
        campaign = Campaign(name="Theirs", owner_id=someone_else)
        await repository.save(campaign)

        assert await repository.find_by_id(campaign.id) is not None


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


class TestDelete:
    async def test_removes_the_campaign(self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID):
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        await repository.delete(campaign.id)

        assert await repository.find_by_id(campaign.id) is None

    async def test_leaves_the_owners_other_campaigns_alone(
        self, repository: SqlAlchemyCampaignRepository, owner_id: uuid.UUID
    ):
        doomed = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(doomed)
        await repository.save(Campaign(name="Fen Wardens", owner_id=owner_id))

        await repository.delete(doomed.id)

        assert [c.name for c in await repository.find_all_for(owner_id)] == ["Fen Wardens"]

    async def test_deleting_an_unknown_id_is_not_an_error(self, repository: SqlAlchemyCampaignRepository):
        await repository.delete(uuid.uuid4())


class TestTheQueryAgreesWithTheDomainRule:
    """Holds `find_all_for` and `CampaignAccess.may_read` to the same answer.

    They are one rule written twice: in SQL so that rows the caller may not see are never
    loaded, and in Python so that the rule can be read in the domain. Nothing in the type
    system keeps the two in step — `find_all_for` would still compile with a wrong WHERE
    clause, and the wrongness would look exactly like working code.

    So this is the guard. When #31 teaches `may_read` about membership and the query
    is not taught the same thing, the two disagree here rather than in production.
    """

    async def test_returns_exactly_the_rows_the_domain_rule_accepts(
        self,
        repository: SqlAlchemyCampaignRepository,
        db: AsyncSession,
        owner_id: uuid.UUID,
        someone_else: uuid.UUID,
    ):
        await repository.save(Campaign(name="Mine", owner_id=owner_id))
        await repository.save(Campaign(name="Also mine", owner_id=owner_id))
        await repository.save(Campaign(name="Theirs", owner_id=someone_else))

        queried = await repository.find_all_for(owner_id)
        every_row = (await db.execute(select(CampaignModel))).scalars().all()
        access = CampaignAccess(owner_id)
        allowed = [m for m in every_row if access.may_read(Campaign(name=m.name, owner_id=m.owner_id, id=m.id))]

        assert sorted(c.id for c in queried) == sorted(m.id for m in allowed)
