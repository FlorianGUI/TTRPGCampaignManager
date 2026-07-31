from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.campaign.adapters.secondary.persistence.character_model import CharacterModel
from app.contexts.campaign.domain.access import CampaignAccess
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository


class SqlAlchemyCharacterRepository(CharacterRepository):
    """The token supplies the campaign every statement filters on.

    Each `access.campaign_id` below is a campaign the caller has already been proved
    entitled to, so the WHERE clause and the authorisation are the same fact rather than
    two that have to be kept in step.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, character: Character) -> Character:
        # merge() rather than add(): one save both inserts and writes back.
        await self._session.merge(
            CharacterModel(
                id=character.id,
                name=character.name,
                description=character.description,
                owner_id=character.owner_id,
                campaign_id=character.campaign_id,
            )
        )
        await self._session.commit()
        return character

    async def find_by_id_in(self, id: UUID, access: CampaignAccess) -> Character | None:
        result = await self._session.execute(
            select(CharacterModel).where(
                CharacterModel.id == id,
                CharacterModel.campaign_id == access.campaign_id,
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_all_in(self, access: CampaignAccess) -> list[Character]:
        result = await self._session.execute(
            select(CharacterModel).where(CharacterModel.campaign_id == access.campaign_id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def delete_in(self, id: UUID, access: CampaignAccess) -> None:
        await self._session.execute(
            delete(CharacterModel).where(
                CharacterModel.id == id,
                CharacterModel.campaign_id == access.campaign_id,
            )
        )
        await self._session.commit()

    async def delete_all_in(self, access: CampaignAccess) -> None:
        # One statement, no rows loaded: emptying a table is not a reason to read it.
        await self._session.execute(delete(CharacterModel).where(CharacterModel.campaign_id == access.campaign_id))
        await self._session.commit()

    @staticmethod
    def _to_domain(model: CharacterModel) -> Character:
        return Character(
            id=model.id,
            name=model.name,
            description=model.description,
            owner_id=model.owner_id,
            campaign_id=model.campaign_id,
        )
