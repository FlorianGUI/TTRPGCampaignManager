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
    async def delete_for(self, id: UUID, owner_id: UUID) -> None:
        """Scoped like every other method here, though the caller has already checked.

        The service loads the campaign and asks `is_editable_by` before getting this
        far, so the owner clause is belt and braces. It stays because a port whose every
        method carries the owner is one nobody has to read twice to trust.
        """
