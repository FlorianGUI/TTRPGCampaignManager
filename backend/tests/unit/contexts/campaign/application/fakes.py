from app.common.access import Unsafe
from app.common.ids import CampaignId, CharacterId, UserId
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.character_access import CharacterAccess
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository

# Both fakes live here rather than in one test module imported by the other: the two
# services are wired to each other now — a campaign deletes the characters at it, and a
# character is reached through its campaign — so neither test file owns them any more.


class FakeCampaignRepository(CampaignRepository):
    def __init__(self):
        self._store: dict[CampaignId, Campaign] = {}

    async def save(self, campaign: Campaign) -> Campaign:
        self._store[campaign.id] = campaign
        return campaign

    async def find_by_id(self, id: CampaignId) -> Unsafe[Campaign]:
        return Unsafe(self._store.get(id))

    async def find_all_for(self, owner_id: UserId) -> list[Campaign]:
        return [c for c in self._store.values() if c.owner_id == owner_id]

    async def delete(self, id: CampaignId) -> None:
        self._store.pop(id, None)


class FakeCharacterRepository(CharacterRepository):
    """Note how little there is to restate now.

    `find_by_id` and `delete` used to carry a copy of the campaign rule, which meant the
    fake could quietly disagree with the SQL and every unit test would still pass. The
    rule went to `CharacterAccess`, so both are now dictionary operations with nothing to
    get wrong. What is left to keep in step is `find_all_in`, and only that.
    """

    def __init__(self):
        self._store: dict[CharacterId, Character] = {}

    async def save(self, character: Character) -> Character:
        self._store[character.id] = character
        return character

    async def find_by_id(self, id: CharacterId) -> Unsafe[Character]:
        return Unsafe(self._store.get(id))

    async def find_all_in(self, access: CharacterAccess) -> list[Character]:
        return [c for c in self._store.values() if c.campaign_id == access.campaign_id]

    async def delete(self, id: CharacterId) -> None:
        self._store.pop(id, None)

    async def delete_all_in(self, access: CharacterAccess) -> None:
        for id in [c.id for c in self._store.values() if c.campaign_id == access.campaign_id]:
            del self._store[id]
