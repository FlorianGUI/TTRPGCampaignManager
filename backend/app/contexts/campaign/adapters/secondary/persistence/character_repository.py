from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.common.ids import CampaignId, CharacterId, UserId
from app.contexts.campaign.adapters.secondary.persistence.character_model import CharacterModel
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.character_access import CharacterAccess
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository


class SqlAlchemyCharacterRepository(CharacterRepository):
    """Only the bulk reads carry a rule; the single-row ones are plain lookups.

    Where a query does filter on `access.campaign_id`, that is a campaign the caller has
    already been proved entitled to. Where one does not, the entitlement is checked in
    the domain instead — see the port for why the two halves differ.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, character: Character) -> Character:
        # merge() rather than add(): one save both inserts and writes back.
        #
        # Every column listed, `created_at` included: merge() copies this transient
        # object onto the loaded row, so omitting a field erases it rather than leaving
        # it alone. See the campaign repository for the longer version.
        await self._session.merge(
            CharacterModel(
                id=character.id,
                name=character.name,
                description=character.description,
                owner_id=character.owner_id,
                campaign_id=character.campaign_id,
                created_at=character.created_at,
                updated_at=character.updated_at,
            )
        )
        await self._session.commit()
        return character

    async def find_by_id(self, id: CharacterId) -> Unsafe[Character]:
        result = await self._session.execute(select(CharacterModel).where(CharacterModel.id == id))
        model = result.scalar_one_or_none()
        return Unsafe(self._to_domain(model) if model is not None else None)

    async def find_all_in(self, access: CharacterAccess) -> list[Character]:
        result = await self._session.execute(
            select(CharacterModel).where(CharacterModel.campaign_id == access.campaign_id)
        )
        return [self._to_domain(m) for m in result.scalars().all()]

    async def delete(self, id: CharacterId) -> None:
        await self._session.execute(delete(CharacterModel).where(CharacterModel.id == id))
        await self._session.commit()

    async def delete_all_in(self, access: CharacterAccess) -> None:
        # One statement, no rows loaded: emptying a table is not a reason to read it.
        await self._session.execute(delete(CharacterModel).where(CharacterModel.campaign_id == access.campaign_id))
        await self._session.commit()

    @staticmethod
    def _to_domain(model: CharacterModel) -> Character:
        return Character(
            id=CharacterId(model.id),
            name=model.name,
            description=model.description,
            owner_id=UserId(model.owner_id),
            campaign_id=CampaignId(model.campaign_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
