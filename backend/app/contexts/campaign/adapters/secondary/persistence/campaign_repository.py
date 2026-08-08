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
        await self._session.merge(
            CampaignModel(
                id=campaign.id,
                name=campaign.name,
                description=campaign.description,
                owner_id=campaign.owner_id,
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
        # Ordered because an unordered SELECT is only incidentally stable: Postgres may
        # return rows in a different order after any update, and the frontend draws this
        # list as a grid of cards people find by position. Ordering by id is arbitrary
        # but fixed, which is the property that matters — a friendlier sort is a
        # decision for whenever the list is long enough for anyone to care.
        result = await self._session.execute(
            select(CampaignModel).where(CampaignModel.owner_id == owner_id).order_by(CampaignModel.id)
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
        )
