from uuid import UUID

import pytest

from app.common.access import Unsafe
from app.common.errors import NotAvailable
from app.common.ids import UserId
from app.contexts.campaign.application.act_service import ActService
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.application.sequence_service import SequenceService
from app.contexts.campaign.application.siblings import SiblingGroups
from app.contexts.campaign.application.structure_service import StructureService
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.placement import NarrativeItem, NarrativeKind, Placement
from app.contexts.campaign.domain.scene import SceneSummary
from tests.unit.contexts.campaign.application.fakes import (
    FakeActRepository,
    FakeSceneRepository,
    FakeSequenceRepository,
)

BODY = ":::read-aloud\nThe gate does not swing. It sinks —\n:::"


def _item(id: UUID, kind: NarrativeKind) -> NarrativeItem:
    return NarrativeItem(id=id, kind=kind)


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
    return ActService(acts, sequences, scenes, SiblingGroups(acts, sequences, scenes))


@pytest.fixture
def sequence_service(sequences: FakeSequenceRepository, acts: FakeActRepository, scenes: FakeSceneRepository):
    return SequenceService(sequences, acts, scenes, SiblingGroups(acts, sequences, scenes))


@pytest.fixture
def scene_service(scenes: FakeSceneRepository, acts: FakeActRepository, sequences: FakeSequenceRepository):
    return SceneService(scenes, acts, sequences, SiblingGroups(acts, sequences, scenes))


@pytest.fixture
def structure(
    acts: FakeActRepository,
    sequences: FakeSequenceRepository,
    scenes: FakeSceneRepository,
    act_service: ActService,
    sequence_service: SequenceService,
    scene_service: SceneService,
):
    # The same three services the router builds: `place` dispatches to them rather than
    # holding a fourth copy of the reorder.
    return StructureService(acts, sequences, scenes, act_service, sequence_service, scene_service)


class TestTheWholeTree:
    async def test_an_empty_campaign_is_three_empty_lists(self, structure: StructureService, narrative: Narrative):
        """Not an error and not a null — a campaign nobody has written in yet."""
        tree = await structure.of(narrative)

        assert tree.acts == []
        assert tree.sequences == []
        assert tree.scenes == []

    async def test_gathers_all_three_levels(
        self,
        structure: StructureService,
        act_service: ActService,
        sequence_service: SequenceService,
        scene_service: SceneService,
        narrative: Narrative,
    ):
        act = await act_service.create(narrative, "Act I — Water Rising")
        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)
        await scene_service.create(narrative, "Arrival at dusk", sequence_id=sequence.id)
        await scene_service.create(narrative, "Session zero")

        tree = await structure.of(narrative)

        assert [a.title for a in tree.acts] == ["Act I — Water Rising"]
        assert [s.title for s in tree.sequences] == ["The Causeway"]
        assert {s.title for s in tree.scenes} == {"Arrival at dusk", "Session zero"}

    async def test_parentage_is_carried_so_the_client_can_group(
        self,
        structure: StructureService,
        act_service: ActService,
        sequence_service: SequenceService,
        scene_service: SceneService,
        narrative: Narrative,
    ):
        """Flat plus parentage, which is what makes the skippable levels need no bucket."""
        act = await act_service.create(narrative, "Act I")
        sequence = await sequence_service.create(narrative, "The Causeway", act_id=act.id)
        await scene_service.create(narrative, "Arrival at dusk", sequence_id=sequence.id)
        await scene_service.create(narrative, "Interlude", act_id=act.id)
        await scene_service.create(narrative, "Session zero")

        tree = await structure.of(narrative)

        assert [s.act_id for s in tree.sequences] == [act.id]
        assert {s.title: (s.act_id, s.sequence_id) for s in tree.scenes} == {
            "Arrival at dusk": (None, sequence.id),
            "Interlude": (act.id, None),
            "Session zero": (None, None),
        }

    async def test_scenes_come_back_in_narrative_order(
        self, structure: StructureService, scene_service: SceneService, narrative: Narrative
    ):
        for title in ["Arrival at dusk", "The sunken arch", "The nesting pair"]:
            await scene_service.create(narrative, title)

        tree = await structure.of(narrative)

        assert [s.title for s in tree.scenes] == ["Arrival at dusk", "The sunken arch", "The nesting pair"]

    async def test_another_campaigns_tree_is_not_in_it(
        self,
        structure: StructureService,
        act_service: ActService,
        narrative: Narrative,
        elsewhere: Narrative,
    ):
        await act_service.create(elsewhere, "Theirs")

        assert (await structure.of(narrative)).acts == []


class TestNoBodies:
    async def test_a_scene_arrives_without_its_body(
        self, structure: StructureService, scene_service: SceneService, narrative: Narrative
    ):
        """The single property this endpoint exists for.

        Not a field hidden at the boundary — a `SceneSummary` has nowhere to put a body, so
        nothing downstream can accidentally start relying on one being there.
        """
        await scene_service.create(narrative, "The sunken arch", BODY)

        tree = await structure.of(narrative)

        assert isinstance(tree.scenes[0], SceneSummary)
        assert not hasattr(tree.scenes[0], "body")

    async def test_the_body_is_still_there_when_the_scene_itself_is_read(
        self, structure: StructureService, scene_service: SceneService, narrative: Narrative
    ):
        """The summary is a view, not a deletion — reading one scene still gives its prose."""
        created = await scene_service.create(narrative, "The sunken arch", BODY)

        await structure.of(narrative)

        assert (await scene_service.get_for(created.id, narrative)).body == BODY


class TestPlacingOneRow:
    """One gesture over the whole tree, dispatched to whichever level owns the row."""

    async def test_an_act_moves_among_its_siblings(
        self, structure: StructureService, act_service: ActService, narrative: Narrative
    ):
        first = await act_service.create(narrative.acts, "Arrival")
        second = await act_service.create(narrative.acts, "The flood")

        tree = await structure.place(
            narrative,
            Placement(item=_item(second.id, NarrativeKind.ACT), parent=None, after=None),
        )

        assert [a.title for a in tree.acts] == ["The flood", "Arrival"]
        assert first.id in {a.id for a in tree.acts}

    async def test_a_sequence_moves_under_an_act(
        self,
        structure: StructureService,
        act_service: ActService,
        sequence_service: SequenceService,
        narrative: Narrative,
    ):
        act = await act_service.create(narrative.acts, "Arrival")
        sequence = await sequence_service.create(narrative, "The long road")

        tree = await structure.place(
            narrative,
            Placement(
                item=_item(sequence.id, NarrativeKind.SEQUENCE),
                parent=_item(act.id, NarrativeKind.ACT),
                after=None,
            ),
        )

        assert [s.act_id for s in tree.sequences] == [act.id]

    async def test_a_scene_moves_under_a_sequence(
        self,
        structure: StructureService,
        sequence_service: SequenceService,
        scene_service: SceneService,
        narrative: Narrative,
    ):
        sequence = await sequence_service.create(narrative, "The long road")
        scene = await scene_service.create(narrative, "The sunken arch", BODY)

        tree = await structure.place(
            narrative,
            Placement(
                item=_item(scene.id, NarrativeKind.SCENE),
                parent=_item(sequence.id, NarrativeKind.SEQUENCE),
                after=None,
            ),
        )

        assert [s.sequence_id for s in tree.scenes] == [sequence.id]

    async def test_a_scene_moves_under_an_act(
        self,
        structure: StructureService,
        act_service: ActService,
        scene_service: SceneService,
        narrative: Narrative,
    ):
        """The same field, read as the other parent — a scene may hang off either."""
        act = await act_service.create(narrative.acts, "Arrival")
        scene = await scene_service.create(narrative, "The sunken arch", BODY)

        tree = await structure.place(
            narrative,
            Placement(
                item=_item(scene.id, NarrativeKind.SCENE),
                parent=_item(act.id, NarrativeKind.ACT),
                after=None,
            ),
        )

        assert [s.act_id for s in tree.scenes] == [act.id]
        assert [s.sequence_id for s in tree.scenes] == [None]

    async def test_the_whole_tree_comes_back_not_the_moved_row(
        self,
        structure: StructureService,
        act_service: ActService,
        scene_service: SceneService,
        narrative: Narrative,
    ):
        """Why this returns a tree: a move can shift rows nobody dragged."""
        act = await act_service.create(narrative.acts, "Arrival")
        scene = await scene_service.create(narrative, "The sunken arch", BODY)

        tree = await structure.place(
            narrative,
            Placement(item=_item(scene.id, NarrativeKind.SCENE), parent=None, after=None),
        )

        assert [a.id for a in tree.acts] == [act.id]
        assert [s.id for s in tree.scenes] == [scene.id]

    async def test_another_campaigns_row_is_not_found(
        self,
        structure: StructureService,
        act_service: ActService,
        narrative: Narrative,
        elsewhere: Narrative,
    ):
        """The body is not trusted: ids are resolved against this campaign's tokens."""
        theirs = await act_service.create(elsewhere.acts, "Theirs")

        with pytest.raises(NotAvailable):
            await structure.place(
                narrative,
                Placement(item=_item(theirs.id, NarrativeKind.ACT), parent=None, after=None),
            )
