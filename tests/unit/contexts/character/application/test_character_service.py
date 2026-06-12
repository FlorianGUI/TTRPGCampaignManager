import uuid
from uuid import UUID

import pytest

from app.contexts.character.application.character_service import CharacterService
from app.contexts.character.domain.character import Character
from app.contexts.character.domain.ports.character_repository import CharacterRepository


class FakeCharacterRepository(CharacterRepository):
    def __init__(self):
        self._store: dict[UUID, Character] = {}

    async def save(self, character: Character) -> Character:
        self._store[character.id] = character
        return character

    async def find_by_id(self, id: UUID) -> Character | None:
        return self._store.get(id)

    async def find_all(self) -> list[Character]:
        return list(self._store.values())


@pytest.fixture
def service():
    return CharacterService(FakeCharacterRepository())


class TestCreate:
    async def test_returns_character_with_correct_fields(self, service: CharacterService):
        character = await service.create("Aragorn", "Ranger")

        assert character.name == "Aragorn"
        assert character.character_class == "Ranger"

    async def test_sets_default_level(self, service: CharacterService):
        character = await service.create("Aragorn", "Ranger")

        assert character.level == 1

    async def test_assigns_an_id(self, service: CharacterService):
        character = await service.create("Aragorn", "Ranger")

        assert character.id is not None


class TestGet:
    async def test_returns_character_when_found(self, service: CharacterService):
        created = await service.create("Aragorn", "Ranger")

        found = await service.get(created.id)

        assert found == created

    async def test_returns_none_when_not_found(self, service: CharacterService):
        result = await service.get(uuid.uuid4())

        assert result is None


class TestListAll:
    async def test_returns_empty_list_when_no_characters(self, service: CharacterService):
        result = await service.list_all()

        assert result == []

    async def test_returns_all_created_characters(self, service: CharacterService):
        await service.create("Aragorn", "Ranger")
        await service.create("Legolas", "Archer")

        result = await service.list_all()

        assert len(result) == 2