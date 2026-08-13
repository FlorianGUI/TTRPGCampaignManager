import uuid

import pytest

from app.common.errors import NotAvailable
from app.common.ids import CampaignId
from app.contexts.campaign.domain.position import (
    POSITION_GAP,
    index_after,
    position_after,
    position_between,
    renumbered,
)
from app.contexts.campaign.domain.scene import Scene


class Missing(NotAvailable):
    detail = "Not found"


def a_scene(position: int) -> Scene:
    return Scene(title="x", campaign_id=CampaignId(uuid.uuid4()), position=position)


class TestPositionBetween:
    def test_an_empty_parent_starts_at_the_gap(self):
        assert position_between(None, None) == POSITION_GAP

    def test_dropping_last_appends_a_gap(self):
        assert position_between(2048, None) == 2048 + POSITION_GAP

    def test_dropping_first_halves_the_leading_position(self):
        """Halving rather than subtracting, so it never reaches for a negative number."""
        assert position_between(None, 1024) == 512
        assert position_between(None, 512) == 256

    def test_dropping_between_takes_the_midpoint(self):
        assert position_between(1024, 2048) == 1536

    def test_one_row_written_because_the_neighbours_do_not_move(self):
        """The whole argument for the sparse scheme, as an assertion.

        The new position is strictly between its neighbours, so neither of them has to
        change — which is #80's "reordering a sibling does not touch unrelated rows".
        """
        before, after = 1024, 2048

        placed = position_between(before, after)

        assert placed is not None
        assert before < placed < after

    def test_adjacent_neighbours_have_no_room(self):
        assert position_between(1024, 1025) is None

    def test_identical_neighbours_have_no_room(self):
        """Two rows tied on a position, which `create` can produce in a race."""
        assert position_between(1024, 1024) is None

    def test_there_is_nothing_above_position_one(self):
        assert position_between(None, 1) is None

    def test_the_gap_survives_about_ten_drops_in_the_same_place(self):
        """The trade the scheme makes, measured rather than asserted in prose.

        Repeatedly dropping into the same slot is the worst case, and it takes ten of them
        before a renumber is needed — a game master reordering by hand will not get there,
        and if they do, one sibling list is rewritten.
        """
        before, after = 1024, 2048
        drops = 0

        while (position := position_between(before, after)) is not None:
            after = position
            drops += 1

        assert drops == 10


class TestRenumbered:
    def test_spaces_a_list_evenly_from_the_gap(self):
        assert renumbered(3) == [1024, 2048, 3072]

    def test_an_empty_list_needs_no_numbers(self):
        assert renumbered(0) == []

    def test_every_pair_has_room_again(self):
        positions = renumbered(5)

        assert all(position_between(a, b) is not None for a, b in zip(positions, positions[1:], strict=False))


class TestIndexAfter:
    def test_no_anchor_is_the_head_of_the_list(self):
        assert index_after([a_scene(1024)], None, Missing) == 0

    def test_an_anchor_puts_the_record_after_it(self):
        first, second = a_scene(1024), a_scene(2048)

        assert index_after([first, second], first.id, Missing) == 1
        assert index_after([first, second], second.id, Missing) == 2

    def test_an_anchor_that_is_not_a_sibling_raises(self):
        """An id from another act, another campaign, or one deleted mid-drag.

        All three arrive here identically and all three answer the caller's own 404, so
        none of them says which it was.
        """
        with pytest.raises(Missing):
            index_after([a_scene(1024)], uuid.uuid4(), Missing)

    def test_an_anchor_in_an_empty_list_raises(self):
        with pytest.raises(Missing):
            index_after([], uuid.uuid4(), Missing)


class TestPositionAfterStillHolds:
    def test_appending_to_an_empty_parent(self):
        assert position_after(None) == POSITION_GAP

    def test_appending_after_the_last(self):
        assert position_after(2048) == 2048 + POSITION_GAP
