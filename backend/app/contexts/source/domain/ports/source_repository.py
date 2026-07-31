from abc import ABC, abstractmethod
from uuid import UUID

from app.contexts.source.domain.source import Source


class SourceRepository(ABC):
    """Reads carry the owner rather than being filtered afterwards.

    There is deliberately no unscoped `find_all()` or `find_by_id(id)`: a source is
    only ever visible to the game master who owns it, and an unfiltered read is one
    autocomplete away as soon as such a method exists. Leaving it out makes the
    omission a type error rather than a silent leak.
    """

    @abstractmethod
    async def save(self, source: Source) -> Source: ...

    @abstractmethod
    async def find_by_id_for(self, id: UUID, owner_id: UUID) -> Source | None: ...

    @abstractmethod
    async def find_all_for(self, owner_id: UUID) -> list[Source]: ...

    @abstractmethod
    async def delete_for(self, id: UUID, owner_id: UUID) -> None: ...
