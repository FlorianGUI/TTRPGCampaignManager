from app.common.access import Unsafe
from app.common.ids import CampaignId, CharacterId, SceneId, UserId
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.character_access import CharacterAccess
from app.contexts.campaign.domain.narrative_access import SceneAccess
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.scene import Scene

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


class FakeSceneRepository(SceneRepository):
    """The same shape as the character fake, plus the two things a tree needs.

    `find_all_in` sorts by `(position, id)` because the real repository does, and a fake
    that returned insertion order would let a service test pass while the endpoint
    handed a game master their scenes in the wrong order. That is the one place this and
    the SQL have to agree, and the integration test is what holds them to it.

    `last_position_in` returns `None` for an empty campaign rather than 0 — `MAX` over no
    rows is `NULL`, and a fake that answered 0 would hide the branch in `position_after`
    that exists for exactly that case.
    """

    def __init__(self):
        self._store: dict[SceneId, Scene] = {}

    async def save(self, scene: Scene) -> Scene:
        self._store[scene.id] = scene
        return scene

    async def find_by_id(self, id: SceneId) -> Unsafe[Scene]:
        return Unsafe(self._store.get(id))

    async def find_all_in(self, access: SceneAccess) -> list[Scene]:
        found = [s for s in self._store.values() if s.campaign_id == access.campaign_id]
        return sorted(found, key=lambda s: (s.position, s.id))

    async def last_position_in(self, access: SceneAccess) -> int | None:
        positions = [s.position for s in self._store.values() if s.campaign_id == access.campaign_id]
        return max(positions) if positions else None

    async def delete(self, id: SceneId) -> None:
        self._store.pop(id, None)

    async def delete_all_in(self, access: SceneAccess) -> None:
        for id in [s.id for s in self._store.values() if s.campaign_id == access.campaign_id]:
            del self._store[id]
