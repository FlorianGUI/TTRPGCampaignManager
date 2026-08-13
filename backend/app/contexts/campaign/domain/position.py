"""Where a record sits among its siblings, and how a new one gets a place.

Narrative order is not creation order and not time: a game master writes an act, plans
scenes inside it, cuts two and moves one, and the order they end up in is the order the
story goes in. So it is an explicit column, and this module is the only place that
decides what goes in it.

**Sparse integers, a gap of 1024.** The scheme was chosen over the two alternatives for
what a drag costs, which is the thing #80 says the position scheme decides:

- *Plain 1..n* makes a drop renumber the whole sibling list, and a reparent renumber two
  of them — a genuine multi-row atomic write, on every drag, forever.
- *Lexicographic ranks* never need a rebalance at all, but cost a rank-generation module
  and its tests, and produce values nobody can read in psql. More machinery than a few
  hundred scenes per campaign is worth.

Sparse integers put a drop between two siblings at their midpoint: **one row updated**,
and the gap only runs out after roughly ten drops between the same adjacent pair, at
which point that one parent's children are renumbered. Both halves of that are now here —
`position_between` for the ordinary drop, `renumbered` for the rare occasion it has
nowhere left to land.

This module is shared on purpose. Acts, sequences and scenes order by the same rule;
three copies of `+ 1024` is exactly the kind of triplication #80 warns about.
"""

from collections.abc import Sequence
from typing import Any, Protocol

# Big enough that a person reordering by hand will not exhaust it, small enough that
# positions stay readable. Ten midpoints between one adjacent pair before a renumber.
POSITION_GAP = 1024


def position_after(last: int | None) -> int:
    """The position for a record appended after `last`, or the first position if none.

    `None` means the parent has no children yet — an empty campaign, or an act nobody has
    written a scene into — and is not an error. Starting at `POSITION_GAP` rather than 0
    leaves room to drag something *above* the first row without a renumber, which is
    otherwise the one move a sparse scheme would refuse on its first day.
    """
    return POSITION_GAP if last is None else last + POSITION_GAP


def position_between(before: int | None, after: int | None) -> int | None:
    """The position for a record dropped between these two neighbours.

    `None` on either side is an end of the list rather than a missing value: no `before`
    means the record is going first, no `after` means last, and neither means the parent
    is empty.

    **Returns `None` when there is no room left**, which is the whole reason this can
    fail. Two adjacent positions differing by 1 have no integer between them, and the
    honest answer is to say so and let the caller renumber — the alternative is silently
    landing the record on top of a sibling and letting the id tie-break decide the game
    master's story order.

    Going first halves the leading position rather than subtracting a gap, so it never
    reaches for a negative number: 1024 → 512 → 256, and only a position of 1 has nowhere
    above it. That is the same trade the midpoint makes everywhere else — cheap almost
    always, and a renumber eventually.
    """
    if before is None and after is None:
        return POSITION_GAP
    if before is None:
        return after // 2 if after > 1 else None  # type: ignore[operator]
    if after is None:
        return before + POSITION_GAP
    return (before + after) // 2 if after - before > 1 else None


class InAList(Protocol):
    """Anything that sits among siblings: it has an identity, and a place."""

    id: Any
    position: int


def index_after(siblings: Sequence[InAList], after: Any | None, missing: type[Exception]) -> int:
    """Where in the sibling list a record dropped *after* `after` belongs.

    `None` is the head of the list rather than a missing argument — dropping something
    first is an ordinary move, and the alternative would be a separate "make this first"
    call for no reason.

    An anchor that is not in this list raises. It is the one input a client can get wrong
    in an interesting way: an id from another act, from another campaign, or one deleted
    between the page loading and the drag finishing. All three raise the caller's own
    `NotAvailable`, so they answer alike and none of them says which it was.

    Shared by all three levels because the reasoning is identical at each, and #80 is
    explicit that the tree's rules live in one place rather than in three services.
    """
    if after is None:
        return 0
    for index, record in enumerate(siblings):
        if record.id == after:
            return index + 1
    raise missing


def renumbered(count: int) -> list[int]:
    """Fresh, evenly spaced positions for one parent's children.

    The escape hatch the sparse scheme trades against, and the only multi-row write in
    this feature. It is scoped to a single sibling list on purpose: renumbering an act's
    scenes must not touch another act's, which is #80's "reordering a sibling does not
    touch unrelated rows" stated from the other side.

    Deliberately not clever. There is no attempt to preserve existing numbers or minimise
    the rows written, because the operation is rare and a partial renumber that left one
    pair still adjacent would simply fail again on the next drop.
    """
    return [(index + 1) * POSITION_GAP for index in range(count)]
