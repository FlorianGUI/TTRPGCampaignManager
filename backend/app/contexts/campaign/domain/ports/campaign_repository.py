from abc import ABC, abstractmethod
from uuid import UUID

from app.contexts.campaign.domain.campaign import Campaign


class CampaignRepository(ABC):
    """One row is a lookup; all rows is a scan. Only the second can afford a rule.

    `find_by_id` applies none: whether the caller may have what comes back is answered by
    `campaign.readable` / `campaign.editable`, which is the one place `owner_id ==` is
    now written for single records.

    `find_all_for` keeps the owner in its query, because listing cannot load every
    campaign in the database and throw most away — #12 says filtered in the query, not
    after the fact. That leaves exactly one place where the rule is still stated twice,
    which is what the contract test in the integration suite is for.
    """

    @abstractmethod
    async def save(self, campaign: Campaign) -> Campaign: ...

    @abstractmethod
    async def find_by_id(self, id: UUID) -> Campaign | None: ...

    @abstractmethod
    async def find_all_for(self, owner_id: UUID) -> list[Campaign]: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Unscoped on purpose: the caller reached this id through `editable` already."""
