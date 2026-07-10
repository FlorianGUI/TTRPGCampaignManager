from uuid import UUID

from app.contexts.character.domain.character import Character
from app.contexts.character.domain.ports.character_repository import CharacterRepository


class CharacterService:
    def __init__(self, repository: CharacterRepository) -> None:
        self._repository = repository

    async def create(self, name: str, character_class: str) -> Character:
        character = Character(name=name, character_class=character_class)
        return await self._repository.save(character)

    async def get(self, id: UUID) -> Character | None:
        return await self._repository.find_by_id(id)

    async def list_all(self) -> list[Character]:
        return await self._repository.find_all()
