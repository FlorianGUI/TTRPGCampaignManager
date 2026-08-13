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
which point that one parent's children are renumbered. That renumbering is real and is
not written here — it belongs with the reorder endpoint in PR 3, and writing it now would
be code no caller reaches and the coverage gate would rightly refuse.

This module is shared on purpose. PR 2 adds acts and sequences, which order by the same
rule; three copies of `+ 1024` is exactly the kind of triplication #80 warns about.
"""

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
