from app.common.access import Unsafe
from app.common.ids import ActId, CampaignId, CharacterId, SceneId, SequenceId, UserId
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.character_access import CharacterAccess
from app.contexts.campaign.domain.narrative_access import ActAccess, SceneAccess, SequenceAccess
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.ports.campaign_repository import CampaignRepository
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.scene import Scene, SceneSummary
from app.contexts.campaign.domain.sequence import Sequence

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

    async def find_summaries_in(self, access: SceneAccess) -> list[SceneSummary]:
        # Built field by field rather than by copying the scene, so a body cannot reach a
        # summary here even though this store has one — the same promise the SQL makes by
        # naming its columns.
        return [
            SceneSummary(
                id=s.id,
                title=s.title,
                status=s.status,
                campaign_id=s.campaign_id,
                position=s.position,
                act_id=s.act_id,
                sequence_id=s.sequence_id,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in await self.find_all_in(access)
        ]

    async def find_under(
        self, access: SceneAccess, act_id: ActId | None, sequence_id: SequenceId | None
    ) -> list[Scene]:
        found = [
            s
            for s in self._store.values()
            if s.campaign_id == access.campaign_id and s.act_id == act_id and s.sequence_id == sequence_id
        ]
        return sorted(found, key=lambda s: (s.position, s.id))

    async def last_position_under(
        self, access: SceneAccess, act_id: ActId | None, sequence_id: SequenceId | None
    ) -> int | None:
        # Scoped to the parent, because the SQL is. A fake that counted the whole campaign
        # would let every scene of an act be appended after the campaign's last scene, and
        # every service test would pass while the endpoint numbered them wrongly.
        positions = [
            s.position
            for s in self._store.values()
            if s.campaign_id == access.campaign_id and s.act_id == act_id and s.sequence_id == sequence_id
        ]
        return max(positions) if positions else None

    async def delete(self, id: SceneId) -> None:
        self._store.pop(id, None)

    async def delete_all_in(self, access: SceneAccess) -> None:
        for id in [s.id for s in self._store.values() if s.campaign_id == access.campaign_id]:
            del self._store[id]


class FakeActRepository(ActRepository):
    """The top of the tree, so its siblings are always the campaign's acts."""

    def __init__(self):
        self._store: dict[ActId, Act] = {}

    async def save(self, act: Act) -> Act:
        self._store[act.id] = act
        return act

    async def find_by_id(self, id: ActId) -> Unsafe[Act]:
        return Unsafe(self._store.get(id))

    async def find_all_in(self, access: ActAccess) -> list[Act]:
        found = [a for a in self._store.values() if a.campaign_id == access.campaign_id]
        return sorted(found, key=lambda a: (a.position, a.id))

    async def find_under(self, access: ActAccess) -> list[Act]:
        return await self.find_all_in(access)

    async def last_position_in(self, access: ActAccess) -> int | None:
        positions = [a.position for a in self._store.values() if a.campaign_id == access.campaign_id]
        return max(positions) if positions else None

    async def delete(self, id: ActId) -> None:
        self._store.pop(id, None)

    async def delete_all_in(self, access: ActAccess) -> None:
        for id in [a.id for a in self._store.values() if a.campaign_id == access.campaign_id]:
            del self._store[id]


class FakeSequenceRepository(SequenceRepository):
    """Positions scoped to the act, and `act_id=None` counted as a sibling group of its own.

    That last part is the one the SQL gets wrong if `IS NULL` is written as `= NULL`, so
    the fake is deliberately explicit about it: `None` is a parent here, not a wildcard.
    """

    def __init__(self):
        self._store: dict[SequenceId, Sequence] = {}

    async def save(self, sequence: Sequence) -> Sequence:
        self._store[sequence.id] = sequence
        return sequence

    async def find_by_id(self, id: SequenceId) -> Unsafe[Sequence]:
        return Unsafe(self._store.get(id))

    async def find_all_in(self, access: SequenceAccess) -> list[Sequence]:
        found = [s for s in self._store.values() if s.campaign_id == access.campaign_id]
        return sorted(found, key=lambda s: (s.position, s.id))

    async def find_under(self, access: SequenceAccess, act_id: ActId | None) -> list[Sequence]:
        found = [s for s in self._store.values() if s.campaign_id == access.campaign_id and s.act_id == act_id]
        return sorted(found, key=lambda s: (s.position, s.id))

    async def last_position_under(self, access: SequenceAccess, act_id: ActId | None) -> int | None:
        positions = [
            s.position for s in self._store.values() if s.campaign_id == access.campaign_id and s.act_id == act_id
        ]
        return max(positions) if positions else None

    async def delete(self, id: SequenceId) -> None:
        self._store.pop(id, None)

    async def delete_all_in(self, access: SequenceAccess) -> None:
        for id in [s.id for s in self._store.values() if s.campaign_id == access.campaign_id]:
            del self._store[id]
