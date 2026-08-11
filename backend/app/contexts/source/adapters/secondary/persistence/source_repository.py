from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.common.ids import SourceId, UserId
from app.contexts.source.adapters.secondary.persistence.source_model import SourceModel
from app.contexts.source.domain.ports.source_repository import SourceRepository
from app.contexts.source.domain.source import Source


class SqlAlchemySourceRepository(SourceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, source: Source) -> Source:
        # merge() rather than add(): the port has a single save, used both to insert a
        # new source and to write back one that was read and modified.
        #
        # Every column listed, `created_at` included: merge() copies this transient
        # object onto the loaded row, so omitting a field erases it rather than leaving
        # it alone. See the campaign repository for the longer version.
        await self._session.merge(
            SourceModel(
                id=source.id,
                title=source.title,
                owner_id=source.owner_id,
                created_at=source.created_at,
                updated_at=source.updated_at,
            )
        )
        await self._session.commit()
        return source

    async def find_by_id(self, id: SourceId) -> Unsafe[Source]:
        result = await self._session.execute(select(SourceModel).where(SourceModel.id == id))
        model = result.scalar_one_or_none()
        return Unsafe(self._to_domain(model) if model is not None else None)

    async def find_all_for(self, owner_id: UserId) -> list[Source]:
        # Filtered in the query, not after the fact: rows the caller may not see are
        # never loaded in the first place.
        #
        # The SQL twin of Source.is_visible_to. A contract test holds the two to the same
        # answer, because this is the one place a wrong rule leaks rows silently.
        #
        # Ordered for the same reason as campaigns, and now by the same key: most
        # recently touched first, with `id` breaking ties so that equal timestamps
        # cannot make a paged list skip and repeat rows. A library sorted by title is a
        # different feature and can have its own decision.
        result = await self._session.execute(
            select(SourceModel)
            .where(SourceModel.owner_id == owner_id)
            .order_by(SourceModel.updated_at.desc(), SourceModel.id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def delete(self, id: SourceId) -> None:
        await self._session.execute(delete(SourceModel).where(SourceModel.id == id))
        await self._session.commit()

    @staticmethod
    def _to_domain(model: SourceModel) -> Source:
        return Source(
            id=SourceId(model.id),
            title=model.title,
            owner_id=UserId(model.owner_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
