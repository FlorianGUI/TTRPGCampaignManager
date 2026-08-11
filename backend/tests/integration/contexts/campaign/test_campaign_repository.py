import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import CampaignId, UserId
from app.contexts.campaign.adapters.secondary.persistence.campaign_model import CampaignModel
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyCampaignRepository:
    return SqlAlchemyCampaignRepository(db)


@pytest.fixture
def owner_id() -> UserId:
    return UserId(uuid.uuid4())


@pytest.fixture
def someone_else() -> UserId:
    return UserId(uuid.uuid4())


class TestSave:
    async def test_returns_the_saved_campaign(self, repository: SqlAlchemyCampaignRepository, owner_id: UserId):
        campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id)

        assert await repository.save(campaign) == campaign

    async def test_persists_campaign(self, repository: SqlAlchemyCampaignRepository, owner_id: UserId):
        campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id, description="A drowned village")
        await repository.save(campaign)

        found = (await repository.find_by_id(campaign.id)).unchecked

        assert found is not None
        assert found.name == "The Hollow Beneath Greyfen"
        assert found.description == "A drowned village"
        assert found.owner_id == owner_id

    async def test_updates_a_campaign_that_was_already_saved(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId
    ):
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        campaign.name = "The Hollow Beneath Greyfen"
        await repository.save(campaign)

        found = (await repository.find_by_id(campaign.id)).unchecked
        assert found is not None
        assert found.name == "The Hollow Beneath Greyfen"


class TestFindById:
    async def test_returns_campaign_when_found(self, repository: SqlAlchemyCampaignRepository, owner_id: UserId):
        campaign = Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        result = (await repository.find_by_id(campaign.id)).unchecked

        assert result is not None
        assert result.id == campaign.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyCampaignRepository):
        assert (await repository.find_by_id(CampaignId(uuid.uuid4()))).unchecked is None

    async def test_finds_a_campaign_whoever_owns_it(
        self, repository: SqlAlchemyCampaignRepository, someone_else: UserId
    ):
        """Ownership is no longer this method's business, and that is the point.

        It used to filter on the owner, which put `owner_id ==` in a WHERE clause where
        it could not be read or tested. `campaign.readable` holds that rule now, and this
        method's whole job is to say whether a row exists.
        """
        campaign = Campaign(name="Theirs", owner_id=someone_else)
        await repository.save(campaign)

        assert (await repository.find_by_id(campaign.id)).unchecked is not None


class TestFindAllFor:
    async def test_returns_the_campaigns_of_that_owner(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId
    ):
        await repository.save(Campaign(name="The Hollow Beneath Greyfen", owner_id=owner_id))
        await repository.save(Campaign(name="Fen Wardens", owner_id=owner_id))

        names = [c.name for c in await repository.find_all_for(owner_id)]

        assert "The Hollow Beneath Greyfen" in names
        assert "Fen Wardens" in names

    async def test_leaves_out_the_campaigns_of_other_owners(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId, someone_else: UserId
    ):
        await repository.save(Campaign(name="Mine", owner_id=owner_id))
        await repository.save(Campaign(name="Theirs", owner_id=someone_else))

        assert [c.name for c in await repository.find_all_for(owner_id)] == ["Mine"]


class TestDelete:
    async def test_removes_the_campaign(self, repository: SqlAlchemyCampaignRepository, owner_id: UserId):
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        await repository.delete(campaign.id)

        assert (await repository.find_by_id(campaign.id)).unchecked is None

    async def test_leaves_the_owners_other_campaigns_alone(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId
    ):
        doomed = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(doomed)
        await repository.save(Campaign(name="Fen Wardens", owner_id=owner_id))

        await repository.delete(doomed.id)

        assert [c.name for c in await repository.find_all_for(owner_id)] == ["Fen Wardens"]

    async def test_deleting_an_unknown_id_is_not_an_error(self, repository: SqlAlchemyCampaignRepository):
        await repository.delete(CampaignId(uuid.uuid4()))


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
        owner_id: UserId,
        someone_else: UserId,
    ):
        await repository.save(Campaign(name="Mine", owner_id=owner_id))
        await repository.save(Campaign(name="Also mine", owner_id=owner_id))
        await repository.save(Campaign(name="Theirs", owner_id=someone_else))

        queried = await repository.find_all_for(owner_id)
        every_row = (await db.execute(select(CampaignModel))).scalars().all()
        access = CampaignAccess(owner_id)
        allowed = [
            m
            for m in every_row
            if access.may_read(Campaign(name=m.name, owner_id=UserId(m.owner_id), id=CampaignId(m.id)))
        ]

        assert sorted(c.id for c in queried) == sorted(m.id for m in allowed)


class TestTimestamps:
    """The half of #78 that only a real database can answer.

    `save()` builds a fresh `CampaignModel` and hands it to `merge()`, which copies that
    transient object's state onto the loaded row. A column left out of the constructor
    is therefore not left alone — it is copied as absent. Every assertion here fails if
    `created_at` stops being passed, and none of them fails anywhere else in the suite.
    """

    async def test_a_saved_campaign_keeps_the_time_it_was_made(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId
    ):
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        found = (await repository.find_by_id(campaign.id)).unchecked

        assert found is not None
        assert found.created_at == campaign.created_at

    async def test_saving_a_second_time_does_not_erase_when_it_was_made(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId
    ):
        """The merge() hazard, and the reason this test exists at all.

        A campaign is saved, read back, edited and saved again — the exact path a rename
        takes. The second save must not move the moment the campaign was made.
        """
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        reloaded = (await repository.find_by_id(campaign.id)).unchecked
        assert reloaded is not None
        reloaded.revise("The Hollow Beneath Greyfen", None)
        await repository.save(reloaded)

        found = (await repository.find_by_id(campaign.id)).unchecked

        assert found is not None
        assert found.created_at == campaign.created_at
        assert found.updated_at > campaign.updated_at

    async def test_reading_a_campaign_does_not_move_its_updated_time(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId
    ):
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        await repository.save(campaign)

        first = (await repository.find_by_id(campaign.id)).unchecked
        second = (await repository.find_by_id(campaign.id)).unchecked

        assert first is not None and second is not None
        assert first.updated_at == second.updated_at


class TestOrdering:
    async def test_lists_the_most_recently_touched_campaign_first(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId
    ):
        """What #59 could not express while the only orderable column was a uuid4."""
        oldest = Campaign(name="Oldest", owner_id=owner_id, updated_at=datetime(2020, 1, 1, tzinfo=UTC))
        newest = Campaign(name="Newest", owner_id=owner_id, updated_at=datetime(2026, 1, 1, tzinfo=UTC))
        middle = Campaign(name="Middle", owner_id=owner_id, updated_at=datetime(2023, 1, 1, tzinfo=UTC))
        for campaign in (oldest, newest, middle):
            await repository.save(campaign)

        found = await repository.find_all_for(owner_id)

        assert [c.name for c in found] == ["Newest", "Middle", "Oldest"]

    async def test_breaks_a_tie_by_id_rather_than_leaving_it_to_postgres(
        self, repository: SqlAlchemyCampaignRepository, owner_id: UserId
    ):
        """Two rows written in one request share `now()` to the microsecond.

        Without the tie-breaker Postgres may return equal keys in any order it likes,
        and a paged list would start skipping and repeating rows — the bug #59's
        ordering existed to prevent, reintroduced by fixing the sort key.
        """
        same_moment = datetime(2026, 1, 1, tzinfo=UTC)
        first = Campaign(id=CampaignId(uuid.UUID(int=1)), name="First", owner_id=owner_id, updated_at=same_moment)
        second = Campaign(id=CampaignId(uuid.UUID(int=2)), name="Second", owner_id=owner_id, updated_at=same_moment)
        await repository.save(second)
        await repository.save(first)

        found = await repository.find_all_for(owner_id)

        assert [c.name for c in found] == ["First", "Second"]
