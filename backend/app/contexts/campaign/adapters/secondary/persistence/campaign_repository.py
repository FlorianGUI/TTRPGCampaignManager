from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.common.ids import CampaignId, UserId
from app.contexts.campaign.adapters.secondary.persistence.campaign_model import CampaignModel
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository


class SqlAlchemyCampaignRepository(CampaignRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, campaign: Campaign) -> Campaign:
        # merge() rather than add(): one save both inserts and writes back.
        #
        # Every column the row has must be listed, and `created_at` is the one that
        # punishes forgetting. merge() copies this transient object's state onto the
        # loaded row, so a field left out here is not left alone — it is copied as
        # absent, and the second save of a campaign erases when it was made. The
        # timestamps come from the entity because the entity is what writes them (#78).
        await self._session.merge(
            CampaignModel(
                id=campaign.id,
                name=campaign.name,
                description=campaign.description,
                owner_id=campaign.owner_id,
                created_at=campaign.created_at,
                updated_at=campaign.updated_at,
            )
        )
        await self._session.commit()
        return campaign

    async def find_by_id(self, id: CampaignId) -> Unsafe[Campaign]:
        result = await self._session.execute(select(CampaignModel).where(CampaignModel.id == id))
        model = result.scalar_one_or_none()
        return Unsafe(self._to_domain(model) if model is not None else None)

    async def find_all_for(self, owner_id: UserId) -> list[Campaign]:
        # The SQL twin of Campaign.is_visible_to. A contract test holds the two to the
        # same answer, because this is the one place a wrong rule leaks rows silently.
        #
        # Most recently worked on first, which is what a chooser wants and what #59
        # could not express while the only orderable column was a uuid4. Editing a
        # campaign moves it to the top: that is the feature, not a side effect.
        #
        # `id` is the tie-breaker and is not decoration. Two rows written in one request
        # share `now()` to the microsecond, and Postgres may return equal keys in any
        # order it likes — the day this list is paged, rows would start being skipped
        # and repeated across pages. That is the same bug #59's ordering existed to
        # prevent, and it comes back the moment the sort key stops being unique.
        result = await self._session.execute(
            select(CampaignModel)
            .where(CampaignModel.owner_id == owner_id)
            .order_by(CampaignModel.updated_at.desc(), CampaignModel.id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def delete(self, id: CampaignId) -> None:
        await self._session.execute(delete(CampaignModel).where(CampaignModel.id == id))
        await self._session.commit()

    @staticmethod
    def _to_domain(model: CampaignModel) -> Campaign:
        return Campaign(
            id=CampaignId(model.id),
            name=model.name,
            description=model.description,
            owner_id=UserId(model.owner_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
