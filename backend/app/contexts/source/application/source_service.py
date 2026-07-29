from uuid import UUID

from app.contexts.source.domain.ports.source_repository import SourceRepository
from app.contexts.source.domain.source import Source


class SourceService:
    def __init__(self, repository: SourceRepository) -> None:
        self._repository = repository

    async def create(self, title: str, owner_id: UUID) -> Source:
        source = Source(title=title, owner_id=owner_id)
        return await self._repository.save(source)

    async def get(self, id: UUID) -> Source | None:
        return await self._repository.find_by_id(id)

    async def list_all(self) -> list[Source]:
        return await self._repository.find_all()
