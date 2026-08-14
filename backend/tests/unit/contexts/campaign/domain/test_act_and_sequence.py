import uuid
from datetime import UTC, datetime

import pytest

from app.common.ids import ActId, CampaignId, SequenceId
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.position import POSITION_GAP
from app.contexts.campaign.domain.scene import Scene, SceneStatus
from app.contexts.campaign.domain.sequence import Sequence

LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)


def an_act(**overrides) -> Act:
    defaults = {
        "title": "Act II — The War for the Fen",
        "campaign_id": CampaignId(uuid.uuid4()),
        "position": POSITION_GAP,
    }
    return Act(**{**defaults, **overrides})


def a_sequence(**overrides) -> Sequence:
    defaults = {
        "title": "Getting the dwarves to commit",
        "campaign_id": CampaignId(uuid.uuid4()),
        "position": POSITION_GAP,
    }
    return Sequence(**{**defaults, **overrides})


class TestAct:
    def test_starts_without_a_description(self):
        assert an_act().description == ""

    def test_two_acts_have_different_ids(self):
        campaign_id = CampaignId(uuid.uuid4())

        assert an_act(campaign_id=campaign_id).id != an_act(campaign_id=campaign_id).id

    def test_revising_moves_the_updated_time(self):
        act = an_act()
        act.updated_at = LONG_AGO

        act.revise("Act II — Low Water", "The war ends badly.")

        assert act.title == "Act II — Low Water"
        assert act.description == "The war ends badly."
        assert act.updated_at > LONG_AGO


class TestSequence:
    def test_hangs_off_the_campaign_by_default(self):
        """The skippable middle: a sequence needs no act to exist."""
        assert a_sequence().act_id is None

    def test_can_be_written_under_an_act(self):
        act_id = ActId(uuid.uuid4())

        assert a_sequence(act_id=act_id).act_id == act_id

    def test_revising_moves_the_updated_time(self):
        sequence = a_sequence()
        sequence.updated_at = LONG_AGO

        sequence.revise("Ilmareth Wakes", "What has been breathing under the boards.")

        assert sequence.updated_at > LONG_AGO

    def test_revising_leaves_it_where_it_sits(self):
        """Editing is not reparenting — see the service for why they are separate."""
        act_id = ActId(uuid.uuid4())
        sequence = a_sequence(act_id=act_id, position=4096)

        sequence.revise("Ilmareth Wakes", "")

        assert sequence.act_id == act_id
        assert sequence.position == 4096


class TestSequenceMoveUnder:
    def test_takes_the_new_parent_and_a_new_place(self):
        sequence = a_sequence(position=4096)
        act_id = ActId(uuid.uuid4())

        sequence.move_under(act_id, POSITION_GAP)

        assert sequence.act_id == act_id
        assert sequence.position == POSITION_GAP

    def test_moving_to_the_campaign_is_a_parent_not_an_absence(self):
        sequence = a_sequence(act_id=ActId(uuid.uuid4()))

        sequence.move_under(None, POSITION_GAP)

        assert sequence.act_id is None

    def test_moving_moves_the_updated_time(self):
        sequence = a_sequence()
        sequence.updated_at = LONG_AGO

        sequence.move_under(ActId(uuid.uuid4()), POSITION_GAP)

        assert sequence.updated_at > LONG_AGO


class TestSceneParentage:
    """The levels are skippable, expressed in two nullable columns and one rule."""

    def _scene(self, **overrides) -> Scene:
        defaults = {
            "title": "The parley at Stonegate",
            "campaign_id": CampaignId(uuid.uuid4()),
            "position": POSITION_GAP,
        }
        return Scene(**{**defaults, **overrides})

    def test_hangs_off_the_campaign_by_default(self):
        scene = self._scene()

        assert scene.act_id is None
        assert scene.sequence_id is None

    def test_can_hang_off_an_act_skipping_the_sequence(self):
        act_id = ActId(uuid.uuid4())
        scene = self._scene(act_id=act_id)

        assert scene.act_id == act_id
        assert scene.sequence_id is None

    def test_can_hang_off_a_sequence(self):
        sequence_id = SequenceId(uuid.uuid4())
        scene = self._scene(sequence_id=sequence_id)

        assert scene.sequence_id == sequence_id
        assert scene.act_id is None

    def test_cannot_hang_off_both(self):
        """Not a deeper tree — an ambiguous one, with two answers to where the scene is."""
        with pytest.raises(ValueError, match="not both"):
            self._scene(act_id=ActId(uuid.uuid4()), sequence_id=SequenceId(uuid.uuid4()))


class TestSceneMoveUnder:
    def _scene(self, **overrides) -> Scene:
        defaults = {
            "title": "The parley at Stonegate",
            "campaign_id": CampaignId(uuid.uuid4()),
            "position": POSITION_GAP,
        }
        return Scene(**{**defaults, **overrides})

    def test_moves_between_acts(self):
        """#80's reason for existing: scenes move between acts, get cut and come back."""
        scene = self._scene(act_id=ActId(uuid.uuid4()), position=4096)
        somewhere_else = ActId(uuid.uuid4())

        scene.move_under(somewhere_else, None, POSITION_GAP)

        assert scene.act_id == somewhere_else
        assert scene.position == POSITION_GAP

    def test_moving_under_a_sequence_clears_the_act(self):
        """Only the direct parent is stored, so the two can never disagree."""
        scene = self._scene(act_id=ActId(uuid.uuid4()))
        sequence_id = SequenceId(uuid.uuid4())

        scene.move_under(None, sequence_id, POSITION_GAP)

        assert scene.sequence_id == sequence_id
        assert scene.act_id is None

    def test_moving_to_the_campaign_is_a_parent_not_an_absence(self):
        scene = self._scene(sequence_id=SequenceId(uuid.uuid4()))

        scene.move_under(None, None, POSITION_GAP)

        assert scene.act_id is None
        assert scene.sequence_id is None

    def test_cannot_move_under_both(self):
        scene = self._scene()

        with pytest.raises(ValueError, match="not both"):
            scene.move_under(ActId(uuid.uuid4()), SequenceId(uuid.uuid4()), POSITION_GAP)

    def test_moving_moves_the_updated_time(self):
        scene = self._scene()
        scene.updated_at = LONG_AGO

        scene.move_under(ActId(uuid.uuid4()), None, POSITION_GAP)

        assert scene.updated_at > LONG_AGO

    def test_moving_does_not_touch_what_the_scene_says(self):
        scene = self._scene(body="The gate does not swing.", status=SceneStatus.DONE)

        scene.move_under(ActId(uuid.uuid4()), None, POSITION_GAP)

        assert scene.body == "The gate does not swing."
        assert scene.status is SceneStatus.DONE
