from app.common.access import Unsafe
from app.common.ids import CampaignId, UserId
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.character_access import CharacterAccess
from app.contexts.campaign.domain.narrative_access import SceneAccess
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository


class CampaignService:
    """Every read and write is scoped to the game master making it.

    A campaign owned by someone else is reported as absent rather than forbidden, the
    same call the source context makes.

    The service holds the character port as well as its own, because the campaign is the
    aggregate root: what lives at a table goes when the table goes, and that cascade is
    the root's job rather than something every caller has to remember to do first. #52
    and #29 add to what gets swept up here, not to the number of places that sweep.
    """

    def __init__(
        self,
        repository: CampaignRepository,
        characters: CharacterRepository,
        scenes: SceneRepository,
    ) -> None:
        self._repository = repository
        self._characters = characters
        self._scenes = scenes

    async def create(self, name: str, owner_id: UserId, description: str | None = None) -> Campaign:
        campaign = Campaign(name=name, owner_id=owner_id, description=description)
        return await self._repository.save(campaign)

    async def get_for(self, id: CampaignId, owner_id: UserId) -> Campaign:
        return CampaignAccess(owner_id).readable(await self._repository.find_by_id(id))

    async def list_for(self, owner_id: UserId) -> list[Campaign]:
        return await self._repository.find_all_for(owner_id)

    async def characters_at(self, id: CampaignId, viewer_id: UserId) -> CharacterAccess:
        """The one authorisation helper for this context, and the door to everything inside it.

        Fetch the row, hand it to the access object, get back a token or an exception.
        Whether the viewer may reach the table is `CampaignAccess.may_read`, and what
        they may do once there is `CharacterAccess` — two questions that answer the same
        way today and stop doing so in #31, without this call site changing.
        """
        return CampaignAccess(viewer_id).characters_at(await self._repository.find_by_id(id))

    async def narrative_at(self, id: CampaignId, viewer_id: UserId) -> SceneAccess:
        """The same door, for the campaign's prep rather than its sheets.

        Identical in shape to `characters_at` and deliberately so: one fetch, one hand-off
        to the access object, a token or an exception. #80's whole authorisation section
        is this method plus `CampaignAccess.narrative_at`, and neither of them says
        anything a campaign does not already say.
        """
        return CampaignAccess(viewer_id).narrative_at(await self._repository.find_by_id(id))

    async def update(self, id: CampaignId, owner_id: UserId, name: str, description: str | None = None) -> Campaign:
        campaign = CampaignAccess(owner_id).editable(await self._repository.find_by_id(id))
        campaign.revise(name, description)
        return await self._repository.save(campaign)

    async def delete(self, id: CampaignId, owner_id: UserId) -> None:
        """Take the table away, and the sheets and the prep with it.

        The cascade is a rule of the application, not an `ON DELETE CASCADE`: there is
        no foreign key between the tables and #12 chose to keep it that way, so the
        sweeping happens here where it can be read.

        Contents go first, the campaign last. If a later delete fails the table survives
        with some of its contents gone, which is recoverable by hand; the other order
        would leave rows pointing at a campaign nobody can reach, which is not.

        Note what this is *not*: #80 leaves open what deleting a non-empty **act** does —
        refuse, or rehome its children — and that question is PR 3's. It is a different
        question from this one. Closing a table is the game master deliberately ending
        the whole thing, and they were made to type its name to get here.
        """
        access = CampaignAccess(owner_id)
        campaign = access.deletable(await self._repository.find_by_id(id))
        await self._characters.delete_all_in(access.characters_at(Unsafe(campaign)))
        await self._scenes.delete_all_in(access.narrative_at(Unsafe(campaign)))
        await self._repository.delete(campaign.id)
