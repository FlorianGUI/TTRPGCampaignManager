from abc import ABC, abstractmethod
from uuid import UUID


class CampaignAccess(ABC):
    """What the character context needs to know about campaigns, and nothing more.

    Half of "who may touch this character" lives in another context: the game master
    who runs the campaign it sits in. Rather than reach into that context, the domain
    states the one question it has — which campaigns does this user run? — and an
    adapter answers it. Campaigns themselves never cross the boundary; only their ids.
    """

    @abstractmethod
    async def campaign_ids_owned_by(self, user_id: UUID) -> list[UUID]: ...
