from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.common.ids import ActId, CampaignId, SequenceId
from app.contexts.campaign.adapters.secondary.persistence.sequence_model import SequenceModel
from app.contexts.campaign.domain.narrative_access import SequenceAccess
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.sequence import Sequence


class SqlAlchemySequenceRepository(SequenceRepository):
    """Only the bulk reads carry a rule; the single-row ones are plain lookups."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, sequence: Sequence) -> Sequence:
        await self._session.merge(
            SequenceModel(
                id=sequence.id,
                title=sequence.title,
                description=sequence.description,
                campaign_id=sequence.campaign_id,
                act_id=sequence.act_id,
                position=sequence.position,
                created_at=sequence.created_at,
                updated_at=sequence.updated_at,
            )
        )
        await self._session.commit()
        return sequence

    async def find_by_id(self, id: SequenceId) -> Unsafe[Sequence]:
        result = await self._session.execute(select(SequenceModel).where(SequenceModel.id == id))
        model = result.scalar_one_or_none()
        return Unsafe(self._to_domain(model) if model is not None else None)

    async def find_all_in(self, access: SequenceAccess) -> list[Sequence]:
        result = await self._session.execute(
            select(SequenceModel)
            .where(SequenceModel.campaign_id == access.campaign_id)
            .order_by(SequenceModel.position, SequenceModel.id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def find_under(self, access: SequenceAccess, act_id: ActId | None) -> list[Sequence]:
        result = await self._session.execute(
            select(SequenceModel)
            .where(SequenceModel.campaign_id == access.campaign_id, self._parent(act_id))
            .order_by(SequenceModel.position, SequenceModel.id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def last_position_under(self, access: SequenceAccess, act_id: ActId | None) -> int | None:
        # `is_(None)` rather than `== None`: in SQL, `act_id = NULL` is NULL rather than
        # true, so the equality form silently matches nothing and every sequence under the
        # campaign would be handed position 1024. `IS NULL` is the only form that asks the
        # question actually meant here.
        result = await self._session.execute(
            select(func.max(SequenceModel.position)).where(
                SequenceModel.campaign_id == access.campaign_id, self._parent(act_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _parent(act_id: ActId | None):
        # `is_(None)` rather than `== None`: in SQL, `act_id = NULL` is NULL rather than
        # true, so the equality form silently matches nothing. Written once now that two
        # queries need it, so a reorder and an append cannot drift into disagreeing about
        # what a sequence under the campaign is.
        return SequenceModel.act_id.is_(None) if act_id is None else SequenceModel.act_id == act_id

    async def delete(self, id: SequenceId) -> None:
        await self._session.execute(delete(SequenceModel).where(SequenceModel.id == id))
        await self._session.commit()

    async def delete_all_in(self, access: SequenceAccess) -> None:
        await self._session.execute(delete(SequenceModel).where(SequenceModel.campaign_id == access.campaign_id))
        await self._session.commit()

    @staticmethod
    def _to_domain(model: SequenceModel) -> Sequence:
        return Sequence(
            id=SequenceId(model.id),
            title=model.title,
            description=model.description,
            campaign_id=CampaignId(model.campaign_id),
            act_id=ActId(model.act_id) if model.act_id is not None else None,
            position=model.position,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
