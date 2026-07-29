from abc import ABC, abstractmethod
from uuid import UUID

from app.contexts.source.domain.source import Source


class SourceRepository(ABC):
    @abstractmethod
    async def save(self, source: Source) -> Source: ...

    @abstractmethod
    async def find_by_id(self, id: UUID) -> Source | None: ...

    @abstractmethod
    async def find_all(self) -> list[Source]: ...
