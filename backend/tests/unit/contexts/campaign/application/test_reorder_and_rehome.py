import uuid

import pytest

from app.common.access import Unsafe
from app.common.ids import SceneId, UserId
from app.contexts.campaign.application.act_service import ActService
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.application.sequence_service import SequenceService
from app.contexts.campaign.domain.act import ActNotAvailable
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.position import POSITION_GAP
from app.contexts.campaign.domain.scene import SceneNotAvailable
from tests.unit.contexts.campaign.application.fakes import (
    FakeActRepository,
    FakeSceneRepository,
    FakeSequenceRepository,
)

# PR 3's two halves: putting a record where it was dropped, and deciding what happens to
# what was inside something a game master removed.


@pytest.fixture
def game_master(owner_id: UserId):
    return owner_id


@pytest.fixture
def narrative(game_master: UserId) -> Narrative:
    return CampaignAccess(game_master).narrative_at(
        Unsafe(Campaign(name="The Drowning of Greyfen", owner_id=game_master))
    )


@pytest.fixture
def elsewhere(game_master: UserId) -> Narrative:
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


async def titles_in(scene_service: SceneService, narrative: Narrative) -> list[str]:
    return [s.title for s in await scene_service.list_for(narrative)]


class TestReorderingWithinOneParent:
    async def test_dropping_a_scene_between_two_others(self, scene_service: SceneService, narrative: Narrative):
        first = await scene_service.create(narrative, "Arrival at dusk")
        await scene_service.create(narrative, "The sunken arch")
        last = await scene_service.create(narrative, "The nesting pair")

        await scene_service.place(last.id, narrative, after=first.id)

        assert await titles_in(scene_service, narrative) == [
            "Arrival at dusk",
            "The nesting pair",
            "The sunken arch",
        ]

    async def test_dropping_a_scene_at_the_top(self, scene_service: SceneService, narrative: Narrative):
        await scene_service.create(narrative, "Arrival at dusk")
        last = await scene_service.create(narrative, "The nesting pair")

        await scene_service.place(last.id, narrative)

        assert await titles_in(scene_service, narrative) == ["The nesting pair", "Arrival at dusk"]

    async def test_a_drop_touches_only_the_row_that_moved(self, scene_service: SceneService, narrative: Narrative):
        """#80's requirement, stated as an assertion about the other rows.

        The neighbours keep the positions *and the timestamps* they had. A scheme that
        renumbered on every drop would fail the first half; moving `updated_at` on the
        neighbours would fail the second and make "recently changed" mean "sat near
        something that moved".
        """
        first = await scene_service.create(narrative, "Arrival at dusk")
        middle = await scene_service.create(narrative, "The sunken arch")
        last = await scene_service.create(narrative, "The nesting pair")
        untouched = {s.id: (s.position, s.updated_at) for s in [first, middle]}

        await scene_service.place(last.id, narrative, after=first.id)

        after = {s.id: (s.position, s.updated_at) for s in await scene_service.list_for(narrative)}
        assert all(after[id] == was for id, was in untouched.items())

    async def test_an_anchor_from_another_parent_is_refused(
        self, scene_service: SceneService, act_service: ActService, narrative: Narrative
    ):
        """A real scene of this campaign, but not a sibling of where this one is going."""
        act = await act_service.create(narrative.acts, "Act I")
        in_the_act = await scene_service.create(narrative, "Arrival at dusk", act_id=act.id)
        loose = await scene_service.create(narrative, "Session zero")

        with pytest.raises(SceneNotAvailable):
            await scene_service.place(loose.id, narrative, after=in_the_act.id)

    async def test_an_anchor_that_never_existed_is_refused(self, scene_service: SceneService, narrative: Narrative):
        scene = await scene_service.create(narrative, "Session zero")

        with pytest.raises(SceneNotAvailable):
            await scene_service.place(scene.id, narrative, after=SceneId(uuid.uuid4()))


class TestRenumberingWhenTheGapRunsOut:
    async def test_a_drop_with_no_room_renumbers_the_sibling_list(
        self, scene_service: SceneService, narrative: Narrative, scenes: FakeSceneRepository
    ):
        """The rare multi-row write, and the only one this feature has.

        The two neighbours are forced adjacent so there is no integer between them, which
        is what ten drops in the same slot would eventually produce.
        """
        first = await scene_service.create(narrative, "Arrival at dusk")
        second = await scene_service.create(narrative, "The sunken arch")
        third = await scene_service.create(narrative, "The nesting pair")
        first.reposition(1024)
        second.reposition(1025)
        await scenes.save(first)
        await scenes.save(second)

        await scene_service.place(third.id, narrative, after=first.id)

        placed = await scene_service.list_for(narrative)
        assert [s.title for s in placed] == ["Arrival at dusk", "The nesting pair", "The sunken arch"]
        assert [s.position for s in placed] == [1024, 2048, 3072]

    async def test_renumbering_does_not_reach_into_another_parent(
        self,
        scene_service: SceneService,
        act_service: ActService,
        narrative: Narrative,
        scenes: FakeSceneRepository,
    ):
        """Scoped to one sibling list, which is the requirement in #80's own words."""
        act = await act_service.create(narrative.acts, "Act I")
        untouched = await scene_service.create(narrative, "In the act", act_id=act.id)

        first = await scene_service.create(narrative, "Arrival at dusk")
        second = await scene_service.create(narrative, "The sunken arch")
        third = await scene_service.create(narrative, "The nesting pair")
        first.reposition(1024)
        second.reposition(1025)
        await scenes.save(first)
        await scenes.save(second)

        await scene_service.place(third.id, narrative, after=first.id)

        still = (await scenes.find_by_id(untouched.id)).unchecked
        assert still is not None
        assert still.position == untouched.position
        assert still.updated_at == untouched.updated_at


class TestReorderingActsAndSequences:
    async def test_acts_reorder(self, act_service: ActService, narrative: Narrative):
        first = await act_service.create(narrative.acts, "Act I")
        await act_service.create(narrative.acts, "Act II")
        third = await act_service.create(narrative.acts, "Act III")

        await act_service.place(third.id, narrative.acts, after=first.id)

        assert [a.title for a in await act_service.list_for(narrative.acts)] == ["Act I", "Act III", "Act II"]

    async def test_sequences_reorder_within_their_act(
        self, sequence_service: SequenceService, act_service: ActService, narrative: Narrative
    ):
        act = await act_service.create(narrative.acts, "Act I")
        first = await sequence_service.create(narrative, "The Causeway", act_id=act.id)
        second = await sequence_service.create(narrative, "What the Wardens Want", act_id=act.id)

        await sequence_service.place(second.id, narrative, act_id=act.id)

        placed = [s.title for s in await sequence_service.list_for(narrative) if s.act_id == act.id]
        assert placed == ["What the Wardens Want", "The Causeway"]
        assert first.id is not None

    async def test_a_sequence_cannot_be_placed_under_another_campaigns_act(
        self,
        sequence_service: SequenceService,
        act_service: ActService,
        narrative: Narrative,
        elsewhere: Narrative,
    ):
        """Placement resolves the parent exactly as PR 2's move did — the rule did not
        move when the operation grew a position."""
        sequence = await sequence_service.create(narrative, "The Causeway")
        theirs = await act_service.create(elsewhere.acts, "Act I")

        with pytest.raises(ActNotAvailable):
            await sequence_service.place(sequence.id, narrative, act_id=theirs.id)


class TestRenumberingAtTheOtherTwoLevels:
    """The same branch as a scene's, exercised where it actually lives.

    Three services run this code; the gate wants each of them proved rather than assumed
    from the one that happens to be tested. It is also the only place `Act.reposition` and
    `Sequence.reposition` are reached.
    """

    async def test_acts_renumber_when_the_gap_runs_out(
        self, act_service: ActService, narrative: Narrative, acts: FakeActRepository
    ):
        first = await act_service.create(narrative.acts, "Act I")
        second = await act_service.create(narrative.acts, "Act II")
        third = await act_service.create(narrative.acts, "Act III")
        first.reposition(1024)
        second.reposition(1025)
        await acts.save(first)
        await acts.save(second)

        await act_service.place(third.id, narrative.acts, after=first.id)

        placed = await act_service.list_for(narrative.acts)
        assert [a.title for a in placed] == ["Act I", "Act III", "Act II"]
        assert [a.position for a in placed] == [1024, 2048, 3072]

    async def test_sequences_renumber_when_the_gap_runs_out(
        self, sequence_service: SequenceService, narrative: Narrative, sequences: FakeSequenceRepository
    ):
        first = await sequence_service.create(narrative, "The Causeway")
        second = await sequence_service.create(narrative, "What the Wardens Want")
        third = await sequence_service.create(narrative, "Ilmareth Wakes")
        first.reposition(1024)
        second.reposition(1025)
        await sequences.save(first)
        await sequences.save(second)

        await sequence_service.place(third.id, narrative, after=first.id)

        placed = await sequence_service.list_for(narrative)
        assert [s.title for s in placed] == ["The Causeway", "Ilmareth Wakes", "What the Wardens Want"]
        assert [s.position for s in placed] == [1024, 2048, 3072]


class TestDeletingAnActRehomes:
    async def test_its_sequences_go_to_the_campaign(
        self, act_service: ActService, sequence_service: SequenceService, narrative: Narrative
    ):
        act = await act_service.create(narrative.acts, "Act I")
        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)

        await act_service.delete(act.id, narrative)

        survivor = await sequence_service.get_for(sequence.id, narrative)
        assert survivor.act_id is None

    async def test_its_own_scenes_go_to_the_campaign(
        self, act_service: ActService, scene_service: SceneService, narrative: Narrative
    ):
        act = await act_service.create(narrative.acts, "Act I")
        scene = await scene_service.create(narrative, "Interlude", act_id=act.id)

        await act_service.delete(act.id, narrative)

        survivor = await scene_service.get_for(scene.id, narrative)
        assert survivor.act_id is None
        assert survivor.sequence_id is None

    async def test_scenes_inside_its_sequences_stay_where_they_are(
        self,
        act_service: ActService,
        sequence_service: SequenceService,
        scene_service: SceneService,
        narrative: Narrative,
    ):
        """Nearest surviving ancestor, not a flattening.

        The sequence survives the act, so its scenes have not lost their parent and must
        not be scattered — that would throw away a grouping nobody asked to lose.
        """
        act = await act_service.create(narrative.acts, "Act I")
        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)
        scene = await scene_service.create(narrative, "Arrival at dusk", sequence_id=sequence.id)

        await act_service.delete(act.id, narrative)

        survivor = await scene_service.get_for(scene.id, narrative)
        assert survivor.sequence_id == sequence.id

    async def test_rehomed_children_are_appended_rather_than_interleaved(
        self, act_service: ActService, scene_service: SceneService, narrative: Narrative
    ):
        """Their old positions meant something only inside the act.

        Kept as they were, a rehomed scene numbered 1024 would land on top of the
        campaign's own first scene and the order would be decided by an id tie-break.
        """
        already = await scene_service.create(narrative, "Session zero")
        act = await act_service.create(narrative.acts, "Act I")
        rehomed = await scene_service.create(narrative, "Interlude", act_id=act.id)
        assert rehomed.position == already.position  # both first, in different parents

        await act_service.delete(act.id, narrative)

        assert await titles_in(scene_service, narrative) == ["Session zero", "Interlude"]

    async def test_an_empty_act_still_just_goes(self, act_service: ActService, narrative: Narrative):
        act = await act_service.create(narrative.acts, "Act III — Low Water")

        await act_service.delete(act.id, narrative)

        assert await act_service.list_for(narrative.acts) == []


class TestDeletingASequenceRehomes:
    async def test_its_scenes_go_to_the_act_above_it(
        self,
        act_service: ActService,
        sequence_service: SequenceService,
        scene_service: SceneService,
        narrative: Narrative,
    ):
        """The phrase "nearest surviving ancestor" earning itself: the act is still there."""
        act = await act_service.create(narrative.acts, "Act I")
        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)
        scene = await scene_service.create(narrative, "Arrival at dusk", sequence_id=sequence.id)

        await sequence_service.delete(sequence.id, narrative)

        survivor = await scene_service.get_for(scene.id, narrative)
        assert survivor.act_id == act.id
        assert survivor.sequence_id is None

    async def test_a_sequence_on_the_campaign_hands_its_scenes_to_the_campaign(
        self, sequence_service: SequenceService, scene_service: SceneService, narrative: Narrative
    ):
        """No branch produces this — it falls out of the sequence's own act being None."""
        sequence = await sequence_service.create(narrative, "Loose thread")
        scene = await scene_service.create(narrative, "Arrival at dusk", sequence_id=sequence.id)

        await sequence_service.delete(sequence.id, narrative)

        survivor = await scene_service.get_for(scene.id, narrative)
        assert survivor.act_id is None
        assert survivor.sequence_id is None

    async def test_nothing_is_lost(
        self, sequence_service: SequenceService, scene_service: SceneService, narrative: Narrative
    ):
        """Cascading is the one answer #80 rules out, so this is the assertion that matters."""
        sequence = await sequence_service.create(narrative, "The Causeway")
        for title in ["Arrival at dusk", "The sunken arch", "The nesting pair"]:
            await scene_service.create(narrative, title, sequence_id=sequence.id)

        await sequence_service.delete(sequence.id, narrative)

        assert len(await scene_service.list_for(narrative)) == 3

    async def test_rehomed_scenes_keep_the_order_they_had(
        self, sequence_service: SequenceService, scene_service: SceneService, narrative: Narrative
    ):
        sequence = await sequence_service.create(narrative, "The Causeway")
        for title in ["Arrival at dusk", "The sunken arch", "The nesting pair"]:
            await scene_service.create(narrative, title, sequence_id=sequence.id)

        await sequence_service.delete(sequence.id, narrative)

        assert await titles_in(scene_service, narrative) == [
            "Arrival at dusk",
            "The sunken arch",
            "The nesting pair",
        ]

    async def test_positions_stay_usable_after_a_rehome(
        self, sequence_service: SequenceService, scene_service: SceneService, narrative: Narrative
    ):
        sequence = await sequence_service.create(narrative, "The Causeway")
        for title in ["Arrival at dusk", "The sunken arch"]:
            await scene_service.create(narrative, title, sequence_id=sequence.id)

        await sequence_service.delete(sequence.id, narrative)

        positions = [s.position for s in await scene_service.list_for(narrative)]
        assert positions == [POSITION_GAP, 2 * POSITION_GAP]
