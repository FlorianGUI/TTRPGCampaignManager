from abc import ABC, abstractmethod
from uuid import UUID

from app.contexts.campaign.domain.campaign import Campaign


class CampaignRepository(ABC):
    """Reads carry the owner, as in the source context: there is no unscoped read."""

    @abstractmethod
    async def save(self, campaign: Campaign) -> Campaign: ...

    @abstractmethod
    async def find_by_id_for(self, id: UUID, owner_id: UUID) -> Campaign | None: ...

    @abstractmethod
    async def find_all_for(self, owner_id: UUID) -> list[Campaign]: ...

    @abstractmethod
    async def find_ids_for(self, owner_id: UUID) -> list[UUID]: ...
