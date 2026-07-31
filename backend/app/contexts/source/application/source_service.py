from uuid import UUID

from app.contexts.source.domain.ports.source_repository import SourceRepository
from app.contexts.source.domain.source import Source, SourceAccess


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

    async def get_for(self, id: UUID, owner_id: UUID) -> Source:
        return SourceAccess(owner_id).readable(await self._repository.find_by_id(id))

    async def list_for(self, owner_id: UUID) -> list[Source]:
        return await self._repository.find_all_for(owner_id)

    async def rename(self, id: UUID, owner_id: UUID, title: str) -> Source:
        source = SourceAccess(owner_id).editable(await self._repository.find_by_id(id))
        source.title = title
        return await self._repository.save(source)

    async def delete(self, id: UUID, owner_id: UUID) -> None:
        """Nothing hangs off a source, so removing one sweeps nothing up after it.

        The contrast with `CampaignService.delete` is the whole reason a source needs no
        access token: there is nothing underneath it to reach.
        """
        source = SourceAccess(owner_id).deletable(await self._repository.find_by_id(id))
        await self._repository.delete(source.id)
