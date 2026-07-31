from uuid import UUID

from app.contexts.character.domain.character import Character
from app.contexts.character.domain.ports.campaign_access import CampaignAccess
from app.contexts.character.domain.ports.character_repository import CharacterRepository


class CampaignNotAvailable(Exception):
    """The campaign a character was pointed at is not one this user runs.

    Raised rather than returned so the caller can tell it apart from "no such
    character" — both answer 404, but not with the same words.
    """


class CharacterService:
    """A character is reachable by its owner and by the game master running its campaign.

    Both halves apply to reads and to writes alike: a GM can correct a sheet at their
    own table, and a player keeps their character when it is not at one. Nobody else
    reaches it at all — a character belonging to neither is reported as absent rather
    than forbidden, so probing ids reveals nothing.
    """

    def __init__(self, repository: CharacterRepository, campaigns: CampaignAccess) -> None:
        self._repository = repository
        self._campaigns = campaigns

    async def create(
        self,
        name: str,
        character_class: str,
        owner_id: UUID,
        campaign_id: UUID | None = None,
    ) -> Character:
        await self._check_campaign(campaign_id, owner_id)
        character = Character(
            name=name,
            character_class=character_class,
            owner_id=owner_id,
            campaign_id=campaign_id,
        )
        return await self._repository.save(character)

    async def get_for(self, id: UUID, viewer_id: UUID) -> Character | None:
        return await self._repository.find_by_id_visible_to(id, viewer_id, await self._runs(viewer_id))

    async def list_for(self, viewer_id: UUID) -> list[Character]:
        return await self._repository.find_all_visible_to(viewer_id, await self._runs(viewer_id))

    async def update(
        self,
        id: UUID,
        viewer_id: UUID,
        name: str,
        character_class: str,
        level: int,
        campaign_id: UUID | None = None,
    ) -> Character | None:
        character = await self._repository.find_by_id_visible_to(id, viewer_id, await self._runs(viewer_id))
        if character is None:
            return None
        # Checked only once the character is known to be reachable, so a caller who
        # cannot see it learns nothing about which campaigns exist either.
        await self._check_campaign(campaign_id, viewer_id)
        character.name = name
        character.character_class = character_class
        character.level = level
        character.campaign_id = campaign_id
        return await self._repository.save(character)

    async def _runs(self, viewer_id: UUID) -> list[UUID]:
        return await self._campaigns.campaign_ids_owned_by(viewer_id)

    async def _check_campaign(self, campaign_id: UUID | None, user_id: UUID) -> None:
        """A character may only be put in a campaign the caller runs.

        Until #31 adds membership there is no way for a player to reach a game
        master's campaign, so this is the whole of the rule: you attach a character to
        a table of your own, or to none.
        """
        if campaign_id is not None and campaign_id not in await self._runs(user_id):
            raise CampaignNotAvailable
