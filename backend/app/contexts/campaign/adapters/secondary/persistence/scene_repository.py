from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.common.ids import ActId, CampaignId, SceneId, SequenceId
from app.contexts.campaign.adapters.secondary.persistence.scene_model import SceneModel
from app.contexts.campaign.domain.narrative_access import SceneAccess
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.scene import Scene, SceneStatus, SceneSummary


class SqlAlchemySceneRepository(SceneRepository):
    """Only the bulk reads carry a rule; the single-row ones are plain lookups.

    Where a query filters on `access.campaign_id`, that is a campaign the caller has
    already been proved entitled to. Where one does not, the entitlement is checked in
    the domain instead — see the port for why the two halves differ.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, scene: Scene) -> Scene:
        # merge() rather than add(): one save both inserts and writes back.
        #
        # Every column listed, `created_at` and `position` included: merge() copies this
        # transient object onto the loaded row, so a field left out is erased rather than
        # left alone. That is the hazard #78 fixed in the other two repositories before
        # this one existed, and it bites harder here — a missing `position` would not
        # merely blank a value, it would drop the scene out of narrative order.
        await self._session.merge(
            SceneModel(
                id=scene.id,
                title=scene.title,
                body=scene.body,
                status=scene.status,
                campaign_id=scene.campaign_id,
                act_id=scene.act_id,
                sequence_id=scene.sequence_id,
                position=scene.position,
                created_at=scene.created_at,
                updated_at=scene.updated_at,
            )
        )
        await self._session.commit()
        return scene

    async def find_by_id(self, id: SceneId) -> Unsafe[Scene]:
        result = await self._session.execute(select(SceneModel).where(SceneModel.id == id))
        model = result.scalar_one_or_none()
        return Unsafe(self._to_domain(model) if model is not None else None)

    async def find_all_in(self, access: SceneAccess) -> list[Scene]:
        # position, then id. The tie-breaker is #78's rule applied to a different column:
        # equal keys come back in whatever order Postgres likes, and two scenes appended
        # in the same instant can share a position. Without the second key a list can
        # reorder itself between two identical requests.
        result = await self._session.execute(
            select(SceneModel)
            .where(SceneModel.campaign_id == access.campaign_id)
            .order_by(SceneModel.position, SceneModel.id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def find_summaries_in(self, access: SceneAccess) -> list[SceneSummary]:
        # Columns named one by one rather than `select(SceneModel)`, which is the entire
        # point: this is the query that must never touch `body`. Adding a column to the
        # model does not silently join it to this read, and a reviewer can see what is
        # being fetched without knowing how the ORM defers loading.
        result = await self._session.execute(
            select(
                SceneModel.id,
                SceneModel.title,
                SceneModel.status,
                SceneModel.campaign_id,
                SceneModel.position,
                SceneModel.act_id,
                SceneModel.sequence_id,
                SceneModel.created_at,
                SceneModel.updated_at,
            )
            .where(SceneModel.campaign_id == access.campaign_id)
            .order_by(SceneModel.position, SceneModel.id)
        )
        return [
            SceneSummary(
                id=SceneId(row.id),
                title=row.title,
                status=SceneStatus(row.status),
                campaign_id=CampaignId(row.campaign_id),
                position=row.position,
                act_id=ActId(row.act_id) if row.act_id is not None else None,
                sequence_id=SequenceId(row.sequence_id) if row.sequence_id is not None else None,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in result.all()
        ]

    async def find_under(
        self, access: SceneAccess, act_id: ActId | None, sequence_id: SequenceId | None
    ) -> list[Scene]:
        result = await self._session.execute(
            select(SceneModel)
            .where(SceneModel.campaign_id == access.campaign_id, *self._parent(act_id, sequence_id))
            .order_by(SceneModel.position, SceneModel.id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def last_position_under(
        self, access: SceneAccess, act_id: ActId | None, sequence_id: SequenceId | None
    ) -> int | None:
        # MAX over an empty set is NULL, which is exactly "nothing hangs off this parent
        # yet" — so the empty case needs no branch here and none in the caller.
        #
        # `is_(None)` rather than `== None` throughout: in SQL `act_id = NULL` evaluates to
        # NULL rather than true, so the equality form matches nothing and every scene of
        # the campaign would be appended at 1024, stacking them all on one position.
        result = await self._session.execute(
            select(func.max(SceneModel.position)).where(
                SceneModel.campaign_id == access.campaign_id, *self._parent(act_id, sequence_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _parent(act_id: ActId | None, sequence_id: SequenceId | None):
        # `is_(None)` rather than `== None`: in SQL, `act_id = NULL` is NULL rather than
        # true, so the equality form matches nothing and every scene of the campaign would
        # look like a sibling of every other. Written once now that two queries need it, so
        # a reorder and an append cannot disagree about who the siblings are.
        return (
            SceneModel.act_id.is_(None) if act_id is None else SceneModel.act_id == act_id,
            SceneModel.sequence_id.is_(None) if sequence_id is None else SceneModel.sequence_id == sequence_id,
        )

    async def delete(self, id: SceneId) -> None:
        await self._session.execute(delete(SceneModel).where(SceneModel.id == id))
        await self._session.commit()

    async def delete_all_in(self, access: SceneAccess) -> None:
        # One statement, no rows loaded: emptying a campaign is not a reason to read it.
        await self._session.execute(delete(SceneModel).where(SceneModel.campaign_id == access.campaign_id))
        await self._session.commit()

    @staticmethod
    def _to_domain(model: SceneModel) -> Scene:
        return Scene(
            id=SceneId(model.id),
            title=model.title,
            body=model.body,
            # The column is text; this is where a value coming back out of the table is
            # held to the domain's list. A row carrying something else raises here rather
            # than travelling on as a str that only looks like a status.
            status=SceneStatus(model.status),
            campaign_id=CampaignId(model.campaign_id),
            act_id=ActId(model.act_id) if model.act_id is not None else None,
            sequence_id=SequenceId(model.sequence_id) if model.sequence_id is not None else None,
            position=model.position,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
