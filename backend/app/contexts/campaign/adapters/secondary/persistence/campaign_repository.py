from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def find_by_id_for(self, id: UUID, owner_id: UUID) -> Campaign | None:
        result = await self._session.execute(
            select(CampaignModel).where(CampaignModel.id == id, CampaignModel.owner_id == owner_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_all_for(self, owner_id: UUID) -> list[Campaign]:
        result = await self._session.execute(select(CampaignModel).where(CampaignModel.owner_id == owner_id))
        return [self._to_domain(m) for m in result.scalars().all()]

    async def find_ids_for(self, owner_id: UUID) -> list[UUID]:
        result = await self._session.execute(select(CampaignModel.id).where(CampaignModel.owner_id == owner_id))
        return list(result.scalars().all())

    @staticmethod
    def _to_domain(model: CampaignModel) -> Campaign:
        return Campaign(
            id=model.id,
            name=model.name,
            description=model.description,
            owner_id=model.owner_id,
        )
