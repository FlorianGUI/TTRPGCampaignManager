from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.source.adapters.secondary.persistence.source_model import SourceModel
from app.contexts.source.domain.ports.source_repository import SourceRepository
from app.contexts.source.domain.source import Source


class SqlAlchemySourceRepository(SourceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, source: Source) -> Source:
        model = SourceModel(
            id=source.id,
            title=source.title,
            owner_id=source.owner_id,
        )
        self._session.add(model)
        await self._session.commit()
        return source

    async def find_by_id(self, id: UUID) -> Source | None:
        result = await self._session.execute(select(SourceModel).where(SourceModel.id == id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_all(self) -> list[Source]:
        result = await self._session.execute(select(SourceModel))
        return [self._to_domain(m) for m in result.scalars().all()]

    @staticmethod
    def _to_domain(model: SourceModel) -> Source:
        return Source(
            id=model.id,
            title=model.title,
            owner_id=model.owner_id,
        )
