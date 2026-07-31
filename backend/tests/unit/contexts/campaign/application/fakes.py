from uuid import UUID

from app.contexts.campaign.domain.access import CampaignAccess
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository

# Both fakes live here rather than in one test module imported by the other: the two
# services are wired to each other now — a campaign deletes the characters at it, and a
# character is reached through its campaign — so neither test file owns them any more.


class FakeCampaignRepository(CampaignRepository):
    def __init__(self):
        self._store: dict[UUID, Campaign] = {}

    async def save(self, campaign: Campaign) -> Campaign:
        self._store[campaign.id] = campaign
        return campaign

    async def find_by_id_for(self, id: UUID, owner_id: UUID) -> Campaign | None:
        campaign = self._store.get(id)
        if campaign is None or campaign.owner_id != owner_id:
            return None
        return campaign

    async def find_all_for(self, owner_id: UUID) -> list[Campaign]:
        return [c for c in self._store.values() if c.owner_id == owner_id]

    async def delete_for(self, id: UUID, owner_id: UUID) -> None:
        campaign = self._store.get(id)
        if campaign is not None and campaign.owner_id == owner_id:
            del self._store[id]


class FakeCharacterRepository(CharacterRepository):
    """Filters on `access.campaign_id`, exactly as the SQL does.

    There is no campaign id here that did not come out of a token, which is the property
    the real repository has too — the fake cannot be more permissive than the thing it
    stands in for, because the port gives it nothing more permissive to accept.
    """

    def __init__(self):
        self._store: dict[UUID, Character] = {}

    async def save(self, character: Character) -> Character:
        self._store[character.id] = character
        return character

    async def find_by_id_in(self, id: UUID, access: CampaignAccess) -> Character | None:
        character = self._store.get(id)
        if character is None or character.campaign_id != access.campaign_id:
            return None
        return character

    async def find_all_in(self, access: CampaignAccess) -> list[Character]:
        return [c for c in self._store.values() if c.campaign_id == access.campaign_id]

    async def delete_in(self, id: UUID, access: CampaignAccess) -> None:
        character = self._store.get(id)
        if character is not None and character.campaign_id == access.campaign_id:
            del self._store[id]

    async def delete_all_in(self, access: CampaignAccess) -> None:
        for id in [c.id for c in self._store.values() if c.campaign_id == access.campaign_id]:
            del self._store[id]
