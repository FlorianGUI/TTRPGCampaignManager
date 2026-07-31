from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def find_by_id_for(self, id: UUID, owner_id: UUID) -> Source | None:
        result = await self._session.execute(
            select(SourceModel).where(SourceModel.id == id, SourceModel.owner_id == owner_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_all_for(self, owner_id: UUID) -> list[Source]:
        # Filtered in the query, not after the fact: rows the caller may not see are
        # never loaded in the first place.
        #
        # The SQL twin of Source.is_visible_to. A contract test holds the two to the same
        # answer, because this is the one place a wrong rule leaks rows silently.
        result = await self._session.execute(select(SourceModel).where(SourceModel.owner_id == owner_id))
        return [self._to_domain(m) for m in result.scalars().all()]

    async def delete_for(self, id: UUID, owner_id: UUID) -> None:
        await self._session.execute(delete(SourceModel).where(SourceModel.id == id, SourceModel.owner_id == owner_id))
        await self._session.commit()

    @staticmethod
    def _to_domain(model: SourceModel) -> Source:
        return Source(
            id=model.id,
            title=model.title,
            owner_id=model.owner_id,
        )
