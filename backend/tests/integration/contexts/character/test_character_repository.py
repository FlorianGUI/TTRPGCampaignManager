import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.character.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.character.domain.character import Character


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyCharacterRepository:
    return SqlAlchemyCharacterRepository(db)


class TestSave:
    async def test_returns_the_saved_character(self, repository: SqlAlchemyCharacterRepository):
        character = Character(name="Aragorn", character_class="Ranger")

        result = await repository.save(character)

        assert result == character

    async def test_persists_character(self, repository: SqlAlchemyCharacterRepository):
        character = Character(name="Aragorn", character_class="Ranger")
        await repository.save(character)

        found = await repository.find_by_id(character.id)

        assert found is not None
        assert found.name == "Aragorn"
        assert found.character_class == "Ranger"


class TestFindById:
    async def test_returns_character_when_found(self, repository: SqlAlchemyCharacterRepository):
        character = Character(name="Legolas", character_class="Archer")
        await repository.save(character)

        result = await repository.find_by_id(character.id)

        assert result is not None
        assert result.id == character.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemyCharacterRepository):
        result = await repository.find_by_id(uuid.uuid4())

        assert result is None


class TestFindAll:
    async def test_returns_saved_characters(self, repository: SqlAlchemyCharacterRepository):
        await repository.save(Character(name="Gimli", character_class="Fighter"))
        await repository.save(Character(name="Gandalf", character_class="Wizard"))

        results = await repository.find_all()
        names = [c.name for c in results]

        assert "Gimli" in names
        assert "Gandalf" in names
