import uuid

import pytest

from app.common.access import Unsafe
from app.common.ids import SceneId, UserId
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.position import POSITION_GAP
from app.contexts.campaign.domain.scene import SceneNotAvailable, SceneStatus
from tests.unit.contexts.campaign.application.fakes import (
    FakeActRepository,
    FakeSceneRepository,
    FakeSequenceRepository,
)

# Every test here starts from a token, because every method does. Whether a viewer may
# have one is the campaign's question and is answered in test_campaign_service and
# test_narrative_access; what is left for this service is what happens once they do.

READ_ALOUD = ":::read-aloud\nThe gate does not swing. It sinks —\n:::"


@pytest.fixture
def game_master(owner_id: UserId):
    return owner_id


@pytest.fixture
def access(game_master: UserId) -> Narrative:
    campaign = Campaign(name="The Drowning of Greyfen", owner_id=game_master)
    return CampaignAccess(game_master).narrative_at(Unsafe(campaign))


@pytest.fixture
def other_access(game_master: UserId) -> Narrative:
    return CampaignAccess(game_master).narrative_at(Unsafe(Campaign(name="Fen Wardens", owner_id=game_master)))


@pytest.fixture
def service(scenes: FakeSceneRepository, acts: FakeActRepository, sequences: FakeSequenceRepository):
    return SceneService(scenes, acts, sequences)


class TestCreate:
    async def test_returns_a_scene_with_the_campaign_off_the_token(self, service: SceneService, access: Narrative):
        scene = await service.create(access, "The parley at Stonegate")

        assert scene.title == "The parley at Stonegate"
        assert scene.campaign_id == access.campaign_id

    async def test_a_scene_starts_unwritten_and_planned(self, service: SceneService, access: Narrative):
        scene = await service.create(access, "The parley at Stonegate")

        assert scene.body == ""
        assert scene.status is SceneStatus.PLANNED

    async def test_the_first_scene_leaves_room_above_it(self, service: SceneService, access: Narrative):
        scene = await service.create(access, "Arrival at dusk")

        assert scene.position == POSITION_GAP

    async def test_each_new_scene_goes_after_the_last(self, service: SceneService, access: Narrative):
        first = await service.create(access, "Arrival at dusk")
        second = await service.create(access, "The sunken arch")
        third = await service.create(access, "The nesting pair")

        assert first.position < second.position < third.position

    async def test_scenes_are_placed_within_their_own_campaign(
        self, service: SceneService, access: Narrative, other_access: Narrative
    ):
        """A campaign's positions are its own. Otherwise the first scene of a new campaign
        would be handed a position past the end of an unrelated one, and every list would
        start at whatever number the busiest campaign had reached."""
        await service.create(access, "Arrival at dusk")

        elsewhere = await service.create(other_access, "Session zero")

        assert elsewhere.position == POSITION_GAP

    async def test_a_body_is_stored_byte_for_byte(self, service: SceneService, access: Narrative):
        scene = await service.create(access, "The sunken arch", READ_ALOUD)

        assert scene.body == READ_ALOUD


class TestGetFor:
    async def test_the_game_master_sees_a_scene_in_their_campaign(self, service: SceneService, access: Narrative):
        created = await service.create(access, "The parley at Stonegate")

        assert (await service.get_for(created.id, access)).id == created.id

    async def test_a_scene_in_another_campaign_is_not_found(
        self, service: SceneService, access: Narrative, other_access: Narrative
    ):
        elsewhere = await service.create(other_access, "Session zero")

        with pytest.raises(SceneNotAvailable):
            await service.get_for(elsewhere.id, access)

    async def test_a_scene_that_never_existed_is_not_found(self, service: SceneService, access: Narrative):
        with pytest.raises(SceneNotAvailable):
            await service.get_for(SceneId(uuid.uuid4()), access)


class TestListFor:
    async def test_lists_in_narrative_order(self, service: SceneService, access: Narrative):
        """Not creation order by accident — the fake sorts by position because the SQL
        does, and the integration test is what holds the two together."""
        await service.create(access, "Arrival at dusk")
        await service.create(access, "The sunken arch")
        await service.create(access, "The nesting pair")

        titles = [s.title for s in await service.list_for(access)]

        assert titles == ["Arrival at dusk", "The sunken arch", "The nesting pair"]

    async def test_lists_nothing_for_a_campaign_with_no_scenes(self, service: SceneService, access: Narrative):
        assert await service.list_for(access) == []

    async def test_does_not_list_another_campaigns_scenes(
        self, service: SceneService, access: Narrative, other_access: Narrative
    ):
        await service.create(other_access, "Session zero")

        assert await service.list_for(access) == []


class TestUpdate:
    async def test_rewrites_the_scene(self, service: SceneService, access: Narrative):
        created = await service.create(access, "The parley")

        updated = await service.update(created.id, access, "The parley at Stonegate", READ_ALOUD, SceneStatus.DONE)

        assert updated.title == "The parley at Stonegate"
        assert updated.body == READ_ALOUD
        assert updated.status is SceneStatus.DONE

    async def test_leaves_the_scene_where_it_was(self, service: SceneService, access: Narrative):
        """Editing is not reordering. A body edit that moved the scene would make the
        order depend on who last touched what."""
        await service.create(access, "Arrival at dusk")
        second = await service.create(access, "The sunken arch")

        updated = await service.update(second.id, access, "The sunken arch", READ_ALOUD, SceneStatus.DONE)

        assert updated.position == second.position

    async def test_a_scene_in_another_campaign_cannot_be_rewritten(
        self, service: SceneService, access: Narrative, other_access: Narrative
    ):
        elsewhere = await service.create(other_access, "Session zero")

        with pytest.raises(SceneNotAvailable):
            await service.update(elsewhere.id, access, "Stolen", "", SceneStatus.PLANNED)


class TestDelete:
    async def test_removes_the_scene(self, service: SceneService, access: Narrative):
        created = await service.create(access, "The rubbing")

        await service.delete(created.id, access)

        assert await service.list_for(access) == []

    async def test_a_scene_in_another_campaign_cannot_be_deleted(
        self, service: SceneService, access: Narrative, other_access: Narrative
    ):
        elsewhere = await service.create(other_access, "Session zero")

        with pytest.raises(SceneNotAvailable):
            await service.delete(elsewhere.id, access)

        assert len(await service.list_for(other_access)) == 1
