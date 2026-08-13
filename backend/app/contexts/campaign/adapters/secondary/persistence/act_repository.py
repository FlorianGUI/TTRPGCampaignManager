from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.common.ids import ActId, CampaignId
from app.contexts.campaign.adapters.secondary.persistence.act_model import ActModel
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.narrative_access import ActAccess
from app.contexts.campaign.domain.ports.act_repository import ActRepository


class SqlAlchemyActRepository(ActRepository):
    """Only the bulk reads carry a rule; the single-row ones are plain lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, act: Act) -> Act:
        # merge() rather than add(), every column listed — see the scene repository for
        # the hazard that omitting one causes.
        await self._session.merge(
            ActModel(
                id=act.id,
                title=act.title,
                description=act.description,
                campaign_id=act.campaign_id,
                position=act.position,
                created_at=act.created_at,
                updated_at=act.updated_at,
            )
        )
        await self._session.commit()
        return act

    async def find_by_id(self, id: ActId) -> Unsafe[Act]:
        result = await self._session.execute(select(ActModel).where(ActModel.id == id))
        model = result.scalar_one_or_none()
        return Unsafe(self._to_domain(model) if model is not None else None)

    async def find_all_in(self, access: ActAccess) -> list[Act]:
        result = await self._session.execute(
            select(ActModel).where(ActModel.campaign_id == access.campaign_id).order_by(ActModel.position, ActModel.id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def last_position_in(self, access: ActAccess) -> int | None:
        result = await self._session.execute(
            select(func.max(ActModel.position)).where(ActModel.campaign_id == access.campaign_id)
        )
        return result.scalar_one_or_none()

    async def delete(self, id: ActId) -> None:
        await self._session.execute(delete(ActModel).where(ActModel.id == id))
        await self._session.commit()

    async def delete_all_in(self, access: ActAccess) -> None:
        await self._session.execute(delete(ActModel).where(ActModel.campaign_id == access.campaign_id))
        await self._session.commit()

    @staticmethod
    def _to_domain(model: ActModel) -> Act:
        return Act(
            id=ActId(model.id),
            title=model.title,
            description=model.description,
            campaign_id=CampaignId(model.campaign_id),
            position=model.position,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
