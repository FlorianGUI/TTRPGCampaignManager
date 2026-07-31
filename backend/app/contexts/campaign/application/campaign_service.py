from uuid import UUID

from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository


class CampaignService:
    """Every read and write is scoped to the game master making it.

    A campaign owned by someone else is reported as absent rather than forbidden, the
    same call the source context makes.
    """

    def __init__(self, repository: CampaignRepository) -> None:
        self._repository = repository

    async def create(self, name: str, owner_id: UUID, description: str | None = None) -> Campaign:
        campaign = Campaign(name=name, owner_id=owner_id, description=description)
        return await self._repository.save(campaign)

    async def get_for(self, id: UUID, owner_id: UUID) -> Campaign | None:
        return await self._repository.find_by_id_for(id, owner_id)

    async def list_for(self, owner_id: UUID) -> list[Campaign]:
        return await self._repository.find_all_for(owner_id)

    async def ids_owned_by(self, owner_id: UUID) -> list[UUID]:
        """The campaigns this user owns, as ids.

        Exists for other contexts to ask "which campaigns may this user reach?"
        without being handed whole campaigns they have no business reading.
        """
        return await self._repository.find_ids_for(owner_id)

    async def update(self, id: UUID, owner_id: UUID, name: str, description: str | None = None) -> Campaign | None:
        campaign = await self._repository.find_by_id_for(id, owner_id)
        if campaign is None:
            return None
        campaign.name = name
        campaign.description = description
        return await self._repository.save(campaign)
