from abc import ABC, abstractmethod
from uuid import UUID

from app.contexts.character.domain.character import Character


class CharacterRepository(ABC):
    @abstractmethod
    async def save(self, character: Character) -> Character: ...

    @abstractmethod
    async def find_by_id(self, id: UUID) -> Character | None: ...

    @abstractmethod
    async def find_all(self) -> list[Character]: ...
