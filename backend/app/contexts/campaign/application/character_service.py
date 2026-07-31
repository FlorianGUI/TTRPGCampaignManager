from uuid import UUID

from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.domain.access import CampaignAccess
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository


class CampaignNotAvailable(Exception):
    """The campaign named in the path is not one this user can reach.

    Raised rather than returned so the caller can tell it apart from "no such
    character at this table" — both answer 404, but not with the same words.
    """


class CharacterService:
    """Characters are reached through the campaign they belong to, never on their own.

    Authorisation happens once, at the campaign, and comes back as a `CampaignAccess`
    that every repository call then requires. That is what stops the check being
    skippable: there is no method here that can locate a character without a token, and
    no way to get a token except by asking the campaign for one.

    What the token permits is the campaign's business, not this service's. Today
    reaching a table means running it, so the game master sees and edits every sheet at
    their own and nobody else sees any of them. When #31 lets a game master invite
    players, `may_edit` and `may_delete` start distinguishing the sheet that is yours
    from the one beside it — and the methods below already ask, so they will not need
    revisiting.
    """

    def __init__(self, repository: CharacterRepository, campaigns: CampaignService) -> None:
        self._repository = repository
        self._campaigns = campaigns

    async def create(self, campaign_id: UUID, viewer_id: UUID, name: str, description: str | None = None) -> Character:
        access = await self._reach(campaign_id, viewer_id)
        return await self._repository.save(access.new_character(name, description))

    async def get_for(self, id: UUID, campaign_id: UUID, viewer_id: UUID) -> Character | None:
        access = await self._reach(campaign_id, viewer_id)
        return await self._repository.find_by_id_in(id, access)

    async def list_for(self, campaign_id: UUID, viewer_id: UUID) -> list[Character]:
        access = await self._reach(campaign_id, viewer_id)
        return await self._repository.find_all_in(access)

    async def update(
        self,
        id: UUID,
        campaign_id: UUID,
        viewer_id: UUID,
        name: str,
        description: str | None = None,
    ) -> Character | None:
        access = await self._reach(campaign_id, viewer_id)
        character = await self._repository.find_by_id_in(id, access)
        if character is None or not access.may_edit(character):
            return None
        character.name = name
        character.description = description
        return await self._repository.save(character)

    async def delete(self, id: UUID, campaign_id: UUID, viewer_id: UUID) -> bool:
        access = await self._reach(campaign_id, viewer_id)
        character = await self._repository.find_by_id_in(id, access)
        if character is None or not access.may_delete(character):
            return False
        await self._repository.delete_in(id, access)
        return True

    async def _reach(self, campaign_id: UUID, viewer_id: UUID) -> CampaignAccess:
        access = await self._campaigns.access_to(campaign_id, viewer_id)
        if access is None:
            raise CampaignNotAvailable
        return access
