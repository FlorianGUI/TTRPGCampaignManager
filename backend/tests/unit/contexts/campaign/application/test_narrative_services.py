import uuid

import pytest

from app.common.access import Unsafe
from app.common.ids import ActId, SequenceId, UserId
from app.contexts.campaign.application.act_service import ActService
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.application.sequence_service import SequenceService
from app.contexts.campaign.domain.act import ActNotAvailable
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.position import POSITION_GAP
from app.contexts.campaign.domain.sequence import SequenceNotAvailable
from tests.unit.contexts.campaign.application.fakes import (
    FakeActRepository,
    FakeSceneRepository,
    FakeSequenceRepository,
)

# The two grouping levels, and the thing PR 2 is really about: a parent that has to belong
# to the same campaign. Every test here holds a token, because every method does.


@pytest.fixture
def game_master(owner_id: UserId):
    return owner_id


@pytest.fixture
def narrative(game_master: UserId) -> Narrative:
    campaign = Campaign(name="The Drowning of Greyfen", owner_id=game_master)
    return CampaignAccess(game_master).narrative_at(Unsafe(campaign))


@pytest.fixture
def elsewhere(game_master: UserId) -> Narrative:
    """A second campaign, run by the same person.

    Same owner deliberately: it isolates the rule being tested. A different owner would
    also be refused, but by the *reach* check, and then these tests would pass even if the
    same-campaign rule were deleted.
    """
    return CampaignAccess(game_master).narrative_at(Unsafe(Campaign(name="Fen Wardens", owner_id=game_master)))


@pytest.fixture
def act_service(acts: FakeActRepository, sequences: FakeSequenceRepository, scenes: FakeSceneRepository):
    return ActService(acts, sequences, scenes)


@pytest.fixture
def sequence_service(sequences: FakeSequenceRepository, acts: FakeActRepository, scenes: FakeSceneRepository):
    return SequenceService(sequences, acts, scenes)


@pytest.fixture
def scene_service(scenes: FakeSceneRepository, acts: FakeActRepository, sequences: FakeSequenceRepository):
    return SceneService(scenes, acts, sequences)


class TestActService:
    async def test_creates_an_act_in_the_campaign_off_the_token(self, act_service: ActService, narrative: Narrative):
        act = await act_service.create(narrative.acts, "Act I — Water Rising")

        assert act.title == "Act I — Water Rising"
        assert act.campaign_id == narrative.campaign_id
        assert act.position == POSITION_GAP

    async def test_acts_are_ordered_and_listed(self, act_service: ActService, narrative: Narrative):
        await act_service.create(narrative.acts, "Act I")
        await act_service.create(narrative.acts, "Act II")

        assert [a.title for a in await act_service.list_for(narrative.acts)] == ["Act I", "Act II"]

    async def test_an_act_in_another_campaign_is_not_found(
        self, act_service: ActService, narrative: Narrative, elsewhere: Narrative
    ):
        theirs = await act_service.create(elsewhere.acts, "Act I")

        with pytest.raises(ActNotAvailable):
            await act_service.get_for(theirs.id, narrative.acts)

    async def test_rewrites_and_deletes(self, act_service: ActService, narrative: Narrative):
        act = await act_service.create(narrative.acts, "Act I")

        await act_service.update(act.id, narrative.acts, "Act I — Water Rising", "The Wardens' trust.")
        assert (await act_service.get_for(act.id, narrative.acts)).title == "Act I — Water Rising"

        await act_service.delete(act.id, narrative)
        assert await act_service.list_for(narrative.acts) == []


class TestSequenceUnderAnAct:
    async def test_a_sequence_may_hang_off_the_campaign(self, sequence_service: SequenceService, narrative: Narrative):
        sequence = await sequence_service.create(narrative, "The Causeway")

        assert sequence.act_id is None

    async def test_a_sequence_may_hang_off_an_act(
        self, sequence_service: SequenceService, act_service: ActService, narrative: Narrative
    ):
        act = await act_service.create(narrative.acts, "Act I")

        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)

        assert sequence.act_id == act.id

    async def test_positions_count_from_the_parent_not_the_campaign(
        self, sequence_service: SequenceService, act_service: ActService, narrative: Narrative
    ):
        """A position is only meaningful among the children of one parent.

        Two under the campaign, then one under an act: the act's first sequence starts at
        the first position rather than continuing the campaign's numbering.
        """
        act = await act_service.create(narrative.acts, "Act I")
        await sequence_service.create(narrative, "Loose one")
        await sequence_service.create(narrative, "Loose two")

        first_in_act = await sequence_service.create(narrative, "The Causeway", act_id=act.id)

        assert first_in_act.position == POSITION_GAP

    async def test_cannot_be_written_under_another_campaigns_act(
        self,
        sequence_service: SequenceService,
        act_service: ActService,
        narrative: Narrative,
        elsewhere: Narrative,
    ):
        """#80's sharp rule. The act exists and the caller runs both campaigns — and it is
        still refused, because the act is not in the campaign this request was reached
        through."""
        theirs = await act_service.create(elsewhere.acts, "Act I")

        with pytest.raises(ActNotAvailable):
            await sequence_service.create(narrative, "The Causeway", act_id=theirs.id)

    async def test_cannot_be_moved_under_another_campaigns_act(
        self,
        sequence_service: SequenceService,
        act_service: ActService,
        narrative: Narrative,
        elsewhere: Narrative,
    ):
        sequence = await sequence_service.create(narrative, "The Causeway")
        theirs = await act_service.create(elsewhere.acts, "Act I")

        with pytest.raises(ActNotAvailable):
            await sequence_service.place(sequence.id, narrative, theirs.id)

    async def test_moving_to_the_campaign_clears_the_act(
        self, sequence_service: SequenceService, act_service: ActService, narrative: Narrative
    ):
        act = await act_service.create(narrative.acts, "Act I")
        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)

        moved = await sequence_service.place(sequence.id, narrative, None)

        assert moved.act_id is None

    async def test_an_act_that_never_existed_is_not_found(
        self, sequence_service: SequenceService, narrative: Narrative
    ):
        with pytest.raises(ActNotAvailable):
            await sequence_service.create(narrative, "The Causeway", act_id=ActId(uuid.uuid4()))


class TestSceneParentage:
    async def test_a_scene_may_hang_off_an_act(
        self, scene_service: SceneService, act_service: ActService, narrative: Narrative
    ):
        act = await act_service.create(narrative.acts, "Act I")

        scene = await scene_service.create(narrative, "Interlude", act_id=act.id)

        assert scene.act_id == act.id
        assert scene.sequence_id is None

    async def test_a_scene_may_hang_off_a_sequence(
        self, scene_service: SceneService, sequence_service: SequenceService, narrative: Narrative
    ):
        sequence = await sequence_service.create(narrative, "The Causeway")

        scene = await scene_service.create(narrative, "Arrival at dusk", sequence_id=sequence.id)

        assert scene.sequence_id == sequence.id
        assert scene.act_id is None

    async def test_a_campaign_with_scenes_and_no_acts_still_works(
        self, scene_service: SceneService, narrative: Narrative
    ):
        """#80's acceptance line, and the whole of a one-shot."""
        scene = await scene_service.create(narrative, "Session zero")

        assert scene.act_id is None
        assert scene.sequence_id is None

    async def test_positions_count_from_the_parent(
        self, scene_service: SceneService, act_service: ActService, narrative: Narrative
    ):
        act = await act_service.create(narrative.acts, "Act I")
        await scene_service.create(narrative, "Loose one")
        await scene_service.create(narrative, "Loose two")

        first_in_act = await scene_service.create(narrative, "Arrival at dusk", act_id=act.id)

        assert first_in_act.position == POSITION_GAP

    async def test_cannot_be_filed_under_another_campaigns_act(
        self,
        scene_service: SceneService,
        act_service: ActService,
        narrative: Narrative,
        elsewhere: Narrative,
    ):
        theirs = await act_service.create(elsewhere.acts, "Act I")

        with pytest.raises(ActNotAvailable):
            await scene_service.create(narrative, "Stolen", act_id=theirs.id)

    async def test_cannot_be_filed_under_another_campaigns_sequence(
        self,
        scene_service: SceneService,
        sequence_service: SequenceService,
        narrative: Narrative,
        elsewhere: Narrative,
    ):
        theirs = await sequence_service.create(elsewhere, "The Causeway")

        with pytest.raises(SequenceNotAvailable):
            await scene_service.create(narrative, "Stolen", sequence_id=theirs.id)

    async def test_a_sequence_that_never_existed_is_not_found(self, scene_service: SceneService, narrative: Narrative):
        with pytest.raises(SequenceNotAvailable):
            await scene_service.create(narrative, "Nowhere", sequence_id=SequenceId(uuid.uuid4()))


class TestSceneMove:
    async def test_moves_a_scene_between_acts(
        self, scene_service: SceneService, act_service: ActService, narrative: Narrative
    ):
        first = await act_service.create(narrative.acts, "Act I")
        second = await act_service.create(narrative.acts, "Act II")
        scene = await scene_service.create(narrative, "The muster", act_id=first.id)

        moved = await scene_service.place(scene.id, narrative, act_id=second.id)

        assert moved.act_id == second.id

    async def test_moving_to_a_sequence_clears_the_act(
        self,
        scene_service: SceneService,
        act_service: ActService,
        sequence_service: SequenceService,
        narrative: Narrative,
    ):
        act = await act_service.create(narrative.acts, "Act I")
        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)
        scene = await scene_service.create(narrative, "Arrival at dusk", act_id=act.id)

        moved = await scene_service.place(scene.id, narrative, sequence_id=sequence.id)

        assert moved.sequence_id == sequence.id
        assert moved.act_id is None

    async def test_moving_to_the_campaign_takes_it_out_of_the_act(
        self, scene_service: SceneService, act_service: ActService, narrative: Narrative
    ):
        act = await act_service.create(narrative.acts, "Act I")
        scene = await scene_service.create(narrative, "Interlude", act_id=act.id)

        moved = await scene_service.place(scene.id, narrative)

        assert moved.act_id is None
        assert moved.sequence_id is None

    async def test_cannot_move_under_another_campaigns_act(
        self,
        scene_service: SceneService,
        act_service: ActService,
        narrative: Narrative,
        elsewhere: Narrative,
    ):
        """The difference between reparenting a scene and moving it under another game
        master's act — #80's words for why this rule is the sharp one."""
        scene = await scene_service.create(narrative, "The muster")
        theirs = await act_service.create(elsewhere.acts, "Act I")

        with pytest.raises(ActNotAvailable):
            await scene_service.place(scene.id, narrative, act_id=theirs.id)

    async def test_no_anchor_means_first_in_the_new_parent(
        self, scene_service: SceneService, act_service: ActService, narrative: Narrative
    ):
        """`after=None` is the head of the list, not "wherever".

        This is the one semantic PR 2's `move` did not have — it appended. A drop target
        has a top, and expressing it as an absent anchor is what makes "put this first" an
        ordinary placement rather than a second endpoint.
        """
        act = await act_service.create(narrative.acts, "Act I")
        already = await scene_service.create(narrative, "Already there", act_id=act.id)
        scene = await scene_service.create(narrative, "The muster")

        moved = await scene_service.place(scene.id, narrative, act_id=act.id)

        assert moved.position < already.position
        assert [s.title for s in await scene_service.list_for(narrative) if s.act_id == act.id] == [
            "The muster",
            "Already there",
        ]

    async def test_naming_the_last_sibling_appends(
        self, scene_service: SceneService, act_service: ActService, narrative: Narrative
    ):
        """Appending is not a special case — it is a placement after the last row."""
        act = await act_service.create(narrative.acts, "Act I")
        already = await scene_service.create(narrative, "Already there", act_id=act.id)
        scene = await scene_service.create(narrative, "The muster")

        moved = await scene_service.place(scene.id, narrative, act_id=act.id, after=already.id)

        assert moved.position > already.position


class TestTheCampaignSweepsTheWholeTree:
    async def test_deleting_a_campaign_takes_acts_sequences_and_scenes(
        self,
        campaigns,
        act_service: ActService,
        sequence_service: SequenceService,
        scene_service: SceneService,
        game_master: UserId,
    ):
        """The root owns the lifecycle of what lives inside it, three levels deep."""
        campaign = await campaigns.create("The Drowning of Greyfen", game_master)
        narrative = await campaigns.narrative_at(campaign.id, game_master)

        act = await act_service.create(narrative.acts, "Act I")
        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)
        await scene_service.create(narrative, "Arrival at dusk", sequence_id=sequence.id)

        await campaigns.delete(campaign.id, game_master)

        assert await act_service.list_for(narrative.acts) == []
        assert await sequence_service.list_for(narrative) == []
        assert await scene_service.list_for(narrative) == []
