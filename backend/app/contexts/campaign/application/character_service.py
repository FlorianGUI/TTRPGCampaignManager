from uuid import UUID

from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository


class CampaignNotAvailable(Exception):
    """The campaign named in the path is not one this user can reach.

    Raised rather than returned so the caller can tell it apart from "no such
    character at this table" — both answer 404, but not with the same words.
    """


class CharacterService:
    """Characters are reached through the campaign they belong to, never on their own.

    Authorisation happens once, at the campaign: reach the table and you reach the
    characters at it. Since a campaign is only reachable by its owner today, that is
    the whole of the rule — the game master sees and edits every sheet at their own
    table, and nobody else sees any of them.

    `Character.owner_id` records who a sheet belongs to and is the same person until
    #31 lets a game master invite players. That is the point at which reaching a
    campaign stops implying reaching every character in it, and this is where the
    "or it is mine" half of the filter belongs when it does.
    """

    def __init__(self, repository: CharacterRepository, campaigns: CampaignService) -> None:
        self._repository = repository
        self._campaigns = campaigns

    async def create(self, campaign_id: UUID, viewer_id: UUID, name: str, description: str | None = None) -> Character:
        await self._reach(campaign_id, viewer_id)
        character = Character(
            name=name,
            owner_id=viewer_id,
            campaign_id=campaign_id,
            description=description,
        )
        return await self._repository.save(character)

    async def get_for(self, id: UUID, campaign_id: UUID, viewer_id: UUID) -> Character | None:
        await self._reach(campaign_id, viewer_id)
        return await self._repository.find_by_id_in(id, campaign_id)

    async def list_for(self, campaign_id: UUID, viewer_id: UUID) -> list[Character]:
        await self._reach(campaign_id, viewer_id)
        return await self._repository.find_all_in(campaign_id)

    async def update(
        self,
        id: UUID,
        campaign_id: UUID,
        viewer_id: UUID,
        name: str,
        description: str | None = None,
    ) -> Character | None:
        await self._reach(campaign_id, viewer_id)
        character = await self._repository.find_by_id_in(id, campaign_id)
        if character is None:
            return None
        character.name = name
        character.description = description
        return await self._repository.save(character)

    async def _reach(self, campaign_id: UUID, viewer_id: UUID) -> None:
        if await self._campaigns.get_for(campaign_id, viewer_id) is None:
            raise CampaignNotAvailable
