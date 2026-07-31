from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.character.adapters.secondary.persistence.character_model import CharacterModel
from app.contexts.character.domain.character import Character
from app.contexts.character.domain.ports.character_repository import CharacterRepository


class SqlAlchemyCharacterRepository(CharacterRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, character: Character) -> Character:
        # merge() rather than add(): one save both inserts and writes back.
        await self._session.merge(
            CharacterModel(
                id=character.id,
                name=character.name,
                character_class=character.character_class,
                level=character.level,
                owner_id=character.owner_id,
                campaign_id=character.campaign_id,
            )
        )
        await self._session.commit()
        return character

    async def find_by_id_visible_to(self, id: UUID, viewer_id: UUID, campaign_ids: Sequence[UUID]) -> Character | None:
        result = await self._session.execute(
            select(CharacterModel).where(CharacterModel.id == id, self._visible_to(viewer_id, campaign_ids))
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_all_visible_to(self, viewer_id: UUID, campaign_ids: Sequence[UUID]) -> list[Character]:
        result = await self._session.execute(select(CharacterModel).where(self._visible_to(viewer_id, campaign_ids)))
        return [self._to_domain(m) for m in result.scalars().all()]

    @staticmethod
    def _visible_to(viewer_id: UUID, campaign_ids: Sequence[UUID]) -> ColumnElement[bool]:
        """Mine, or sitting at a table I run — decided in the query, not afterwards.

        A viewer running no campaigns gives an empty IN, which Postgres evaluates as
        false rather than matching everything, so the clause degrades to "mine only".
        """
        return or_(
            CharacterModel.owner_id == viewer_id,
            CharacterModel.campaign_id.in_(campaign_ids),
        )

    @staticmethod
    def _to_domain(model: CharacterModel) -> Character:
        return Character(
            id=model.id,
            name=model.name,
            character_class=model.character_class,
            level=model.level,
            owner_id=model.owner_id,
            campaign_id=model.campaign_id,
        )
