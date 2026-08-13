import uuid
from datetime import UTC, datetime

from app.common.ids import CampaignId
from app.contexts.campaign.domain.position import POSITION_GAP, position_after
from app.contexts.campaign.domain.scene import Scene, SceneStatus


def a_scene(**overrides) -> Scene:
    defaults = {
        "title": "The parley at Stonegate",
        "campaign_id": CampaignId(uuid.uuid4()),
        "position": POSITION_GAP,
    }
    return Scene(**{**defaults, **overrides})


class TestScene:
    def test_starts_unwritten_and_unplayed(self):
        """The normal state of most of a campaign: named, and nothing else yet."""
        scene = a_scene()

        assert scene.body == ""
        assert scene.status is SceneStatus.PLANNED

    def test_id_is_auto_generated(self):
        assert a_scene().id is not None

    def test_two_scenes_have_different_ids(self):
        campaign_id = CampaignId(uuid.uuid4())

        assert a_scene(campaign_id=campaign_id).id != a_scene(campaign_id=campaign_id).id

    def test_body_is_kept_byte_for_byte(self):
        """#80's acceptance line, at the level that can actually promise it.

        Nothing between here and the column touches this string — no parsing, no
        normalising, no stripping. The directives below are #53's dialect and this layer
        is required not to know that.
        """
        body = ":::read-aloud\nThe gate does not swing. It sinks —\n:::\n\n:npc[Torvald]  :dice[2d6]"

        assert a_scene(body=body).body == body


class TestSceneStatus:
    def test_is_the_three_the_game_master_marks(self):
        assert [s.value for s in SceneStatus] == ["planned", "played", "skipped"]

    def test_reads_as_its_own_value(self):
        """A StrEnum, so it goes into a String column and comes back out of one."""
        assert SceneStatus.PLAYED == "played"


class TestSceneTimestamps:
    """The contract `Campaign` and `Character` already have, restated for the third time.

    Not a copy for its own sake: `revise` is what makes `updated_at` true, and a service
    that assigned the fields directly would pass every other test in this file. #78 said
    three tables is where a mixin stops being premature; three entities is where this
    test stops being redundant.
    """

    LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)

    def test_records_time_with_an_offset(self):
        scene = a_scene()

        assert scene.created_at.tzinfo is not None
        assert scene.updated_at.tzinfo is not None

    def test_revising_moves_the_updated_time(self):
        scene = a_scene()
        scene.updated_at = self.LONG_AGO

        scene.revise("The parley", "It sinks.", SceneStatus.PLAYED)

        assert scene.updated_at > self.LONG_AGO

    def test_revising_leaves_the_created_time_alone(self):
        scene = a_scene()
        created = scene.created_at

        scene.revise("The parley", "It sinks.", SceneStatus.PLAYED)

        assert scene.created_at == created


class TestRevise:
    def test_rewrites_every_field_it_is_given(self):
        scene = a_scene()

        scene.revise("The parley", "Torvald hears them standing.", SceneStatus.PLAYED)

        assert scene.title == "The parley"
        assert scene.body == "Torvald hears them standing."
        assert scene.status is SceneStatus.PLAYED

    def test_leaves_the_position_alone(self):
        """Reordering is its own operation (PR 3), not a side effect of editing.

        The alternative — a position parameter here — means every body edit carries one,
        and a stale value from a client that reordered in another tab silently moves the
        scene.
        """
        scene = a_scene(position=4096)

        scene.revise("The parley", "It sinks.", SceneStatus.PLAYED)

        assert scene.position == 4096


class TestPositionAfter:
    def test_the_first_record_leaves_room_above_it(self):
        """Starting at the gap rather than 0, so the first drag *upwards* needs no renumber."""
        assert position_after(None) == POSITION_GAP

    def test_a_later_record_goes_a_gap_beyond_the_last(self):
        assert position_after(POSITION_GAP) == 2 * POSITION_GAP

    def test_leaves_room_to_drop_between_two_siblings(self):
        """The whole point of the scheme: a midpoint exists, so a drop writes one row."""
        first, second = position_after(None), position_after(position_after(None))

        assert first < (first + second) // 2 < second
