from uuid import UUID

from app.contexts.campaign.domain.access import CampaignAccess
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository


class CharacterService:
    """Characters are reached through the campaign they belong to, never on their own.

    Every method here takes a `CampaignAccess`, so authorisation has already happened by
    the time any of them run — resolved once at the edge, by the dependency that turns
    the campaign in the path into proof. That leaves this service as pure orchestration:
    it has no campaign to look up, no check to make, and nothing to raise.

    What the token permits is the campaign's business, not this service's. Today
    reaching a table means running it, so the game master sees and edits every sheet at
    their own and nobody else sees any of them. When #31 lets a game master invite
    players, `may_edit` and `may_delete` start distinguishing the sheet that is yours
    from the one beside it — and the methods below already ask, so they will not need
    revisiting.
    """

    def __init__(self, repository: CharacterRepository) -> None:
        self._repository = repository

    async def create(self, access: CampaignAccess, name: str, description: str | None = None) -> Character:
        return await self._repository.save(access.new_character(name, description))

    async def get_for(self, id: UUID, access: CampaignAccess) -> Character | None:
        return await self._repository.find_by_id_in(id, access)

    async def list_for(self, access: CampaignAccess) -> list[Character]:
        return await self._repository.find_all_in(access)

    async def update(
        self,
        id: UUID,
        access: CampaignAccess,
        name: str,
        description: str | None = None,
    ) -> Character | None:
        character = await self._repository.find_by_id_in(id, access)
        if character is None or not access.may_edit(character):
            return None
        character.name = name
        character.description = description
        return await self._repository.save(character)

    async def delete(self, id: UUID, access: CampaignAccess) -> bool:
        character = await self._repository.find_by_id_in(id, access)
        if character is None or not access.may_delete(character):
            return False
        await self._repository.delete_in(id, access)
        return True
