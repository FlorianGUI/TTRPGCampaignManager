from uuid import UUID

from app.contexts.source.domain.ports.source_repository import SourceRepository
from app.contexts.source.domain.source import Source


class SourceService:
    """Every read and write is scoped to the game master making it.

    A source belonging to someone else is not reported as forbidden but as absent:
    the caller cannot tell it apart from an id that was never used, so probing ids
    reveals nothing about what other game masters own.
    """

    def __init__(self, repository: SourceRepository) -> None:
        self._repository = repository

    async def create(self, title: str, owner_id: UUID) -> Source:
        source = Source(title=title, owner_id=owner_id)
        return await self._repository.save(source)

    async def get_for(self, id: UUID, owner_id: UUID) -> Source | None:
        return await self._repository.find_by_id_for(id, owner_id)

    async def list_for(self, owner_id: UUID) -> list[Source]:
        return await self._repository.find_all_for(owner_id)

    async def rename(self, id: UUID, owner_id: UUID, title: str) -> Source | None:
        source = await self._repository.find_by_id_for(id, owner_id)
        if source is None:
            return None
        source.title = title
        return await self._repository.save(source)
