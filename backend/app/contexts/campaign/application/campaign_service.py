from uuid import UUID

from app.contexts.campaign.domain.access import CampaignAccess
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository


class CampaignService:
    """Every read and write is scoped to the game master making it.

    A campaign owned by someone else is reported as absent rather than forbidden, the
    same call the source context makes.

    The service holds the character port as well as its own, because the campaign is the
    aggregate root: what lives at a table goes when the table goes, and that cascade is
    the root's job rather than something every caller has to remember to do first. #52
    and #29 add to what gets swept up here, not to the number of places that sweep.
    """

    def __init__(self, repository: CampaignRepository, characters: CharacterRepository) -> None:
        self._repository = repository
        self._characters = characters

    async def create(self, name: str, owner_id: UUID, description: str | None = None) -> Campaign:
        campaign = Campaign(name=name, owner_id=owner_id, description=description)
        return await self._repository.save(campaign)

    async def get_for(self, id: UUID, owner_id: UUID) -> Campaign | None:
        return await self._repository.find_by_id_for(id, owner_id)

    async def list_for(self, owner_id: UUID) -> list[Campaign]:
        return await self._repository.find_all_for(owner_id)

    async def access_to(self, id: UUID, viewer_id: UUID) -> CampaignAccess | None:
        """The one authorisation helper for this context, and the door to everything inside it.

        Two questions in one call, and they stay distinct as the rules grow: the read
        answers *may this viewer reach the table at all*, and `grant` answers *what may
        they do once there*. Today the first implies the second, so a token goes to
        anyone the query returned. After #31 the query also returns campaigns the viewer
        was invited to, and `grant` is what starts telling a game master apart from a
        player — without this call site changing.
        """
        campaign = await self._repository.find_by_id_for(id, viewer_id)
        if campaign is None:
            return None
        return campaign.grant(viewer_id)

    async def update(self, id: UUID, owner_id: UUID, name: str, description: str | None = None) -> Campaign | None:
        campaign = await self._repository.find_by_id_for(id, owner_id)
        if campaign is None or not campaign.is_editable_by(owner_id):
            return None
        campaign.name = name
        campaign.description = description
        return await self._repository.save(campaign)

    async def delete(self, id: UUID, owner_id: UUID) -> bool:
        """Take the table away, and the sheets at it with it.

        The cascade is a rule of the application, not an `ON DELETE CASCADE`: there is
        no foreign key between the two tables and #12 chose to keep it that way, so the
        sweeping happens here where it can be read.

        Characters go first. If the second delete fails the table survives with its
        sheets gone, which is recoverable by hand; the other order would leave sheets
        pointing at a campaign nobody can reach, which is not.
        """
        campaign = await self._repository.find_by_id_for(id, owner_id)
        if campaign is None or not campaign.is_editable_by(owner_id):
            return False
        await self._characters.delete_all_in(campaign.grant(owner_id))
        await self._repository.delete_for(id, owner_id)
        return True
