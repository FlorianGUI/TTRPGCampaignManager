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
        await self._session.merge(
            SourceModel(
                id=source.id,
                title=source.title,
                owner_id=source.owner_id,
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
        # Ordered for the same reason as campaigns: an unordered SELECT is only
        # incidentally stable, and a library that reshuffles between visits is a list
        # nobody can learn. By id — arbitrary but fixed — until someone wants it by title.
        result = await self._session.execute(
            select(SourceModel).where(SourceModel.owner_id == owner_id).order_by(SourceModel.id)
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
        )
