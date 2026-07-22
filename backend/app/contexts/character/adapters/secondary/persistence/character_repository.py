from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.character.adapters.secondary.persistence.character_model import CharacterModel
from app.contexts.character.domain.character import Character
from app.contexts.character.domain.ports.character_repository import CharacterRepository


class SqlAlchemyCharacterRepository(CharacterRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, character: Character) -> Character:
        model = CharacterModel(
            id=character.id,
            name=character.name,
            character_class=character.character_class,
            level=character.level,
        )
        self._session.add(model)
        await self._session.commit()
        return character

    async def find_by_id(self, id: UUID) -> Character | None:
        result = await self._session.execute(select(CharacterModel).where(CharacterModel.id == id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_all(self) -> list[Character]:
        result = await self._session.execute(select(CharacterModel))
        return [self._to_domain(m) for m in result.scalars().all()]

    @staticmethod
    def _to_domain(model: CharacterModel) -> Character:
        return Character(
            id=model.id,
            name=model.name,
            character_class=model.character_class,
            level=model.level,
        )
