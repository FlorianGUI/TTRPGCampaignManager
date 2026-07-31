from uuid import UUID

from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.character.domain.ports.campaign_access import CampaignAccess


class CampaignServiceAccess(CampaignAccess):
    """Answers the character domain's campaign question by asking the campaign context.

    This is the only place the two contexts meet, and it is an adapter rather than a
    dependency of the domain: it talks to the campaign context through its service —
    its front door — not to its repository or its tables.
    """

    def __init__(self, campaigns: CampaignService) -> None:
        self._campaigns = campaigns

    async def campaign_ids_owned_by(self, user_id: UUID) -> list[UUID]:
        return await self._campaigns.ids_owned_by(user_id)
