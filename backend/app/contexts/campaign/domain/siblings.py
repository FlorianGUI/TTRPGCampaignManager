"""A sibling group: everything under one parent, whatever kind it is.

#80 says `position` is "within a parent, because narrative order is not creation order".
The first implementation read that as *within a parent, among things of my own kind* —
each repository counted only its own table — and #101 is the bill for the difference. A
sequence and a scene written into the same act were both handed `POSITION_GAP`, sat on
two independent number lines, and were drawn in whatever order their uuids happened to
sort in. No amount of reordering could change it, because a scene's sibling list held
only scenes and there was no way to say "put this after that sequence".

**One parent, one list.** An act's children are its sequences and its scenes together,
because that is what the outline draws and what a game master is arranging. The campaign's
children are its acts, the sequences that skip the act level, and the scenes that skip
both. A sequence holds only scenes, so its group happens to be one kind — but by
arithmetic rather than by rule, which is why nothing below special-cases it.

This module is the rule. Loading a group needs the three repositories and so lives in
`application/siblings.py`; what a group *is*, and where a record lands in one, is here
where it can be read and tested without a database.
"""

from collections.abc import Iterable
from collections.abc import Sequence as Listing
from dataclasses import dataclass
from uuid import UUID

from app.common.errors import NotAvailable
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.position import index_after, position_between
from app.contexts.campaign.domain.scene import Scene
from app.contexts.campaign.domain.sequence import Sequence

type SiblingId = UUID
"""What an anchor names: some member of the group, and not necessarily of one kind.

A bare `UUID` rather than `ActId | SequenceId | SceneId`, which is the honest type. #101's
fix is that a scene may be dropped after a sequence, so the caller cannot know which of
the three an anchor is — that is discovered by looking for it in the group. The union
would only have moved the problem to the boundary, where a router would have had to pick a
label for an id whose kind it does not know, and picking `SceneId(...)` for a sequence is
precisely the fiction that made this look correct before.
"""


class AnchorNotAvailable(NotAvailable):
    """The row a placement was to follow is not in the group it named.

    Its own exception, because the alternative was answering with the *moved* record's
    404 — a scene dropped after an id that does not resolve was told "Scene not found",
    about a scene it had just been asked to move and which was plainly there. That is the
    wrong sentence and it sends whoever reads it looking in the wrong place (#110).

    Still one answer for every way an anchor can fail to resolve: an id from another
    parent, from another campaign, or one deleted while the outline sat open all raise
    this and say the same thing. The 404-not-403 reasoning in #12 applies to the anchor
    exactly as it does to everything else — which of the three it was is not a caller's to
    learn.
    """

    detail = "The record it was to follow was not found"


type Sibling = Act | Sequence | Scene
"""One member of a group: exactly one of the three things a parent can hold.

A union rather than the `InAList` protocol, because placing a record does more than read
its position — a renumber writes to it, and the write differs per kind. Naming the three
keeps that honest and lets the type checker prove the dispatch in
`application/siblings.py` is exhaustive, rather than leaving a fourth kind to be
discovered at runtime by whoever adds one.
"""


def in_narrative_order[T: Sibling](records: Iterable[T]) -> list[T]:
    """One parent's children of every kind, in the order the story goes in.

    The id is a tie-break and not an ordering: two records of one parent should never
    share a position once this module is placing them, and the tie-break exists for the
    rows written before it did. It matches what the client already does with the same
    three lists, so a campaign mid-migration is drawn the same way on both sides rather
    than one order on screen and another in the placement arithmetic.

    `str` on the id because these are uuids of three different `NewType`s: comparing them
    directly is fine at runtime and not a thing the type checker should be asked to agree
    to.
    """
    return sorted(records, key=lambda record: (record.position, str(record.id)))


@dataclass(frozen=True)
class Placement:
    """Where a record lands, and what it costs to put it there.

    `position` is `None` when the two neighbours have no integer between them. That is not
    a failure — it is the sparse scheme's rare case, and `ordered` is then the whole group
    in its new order, ready to be renumbered. Both are returned together because the
    caller needs the same index either way and computing it twice is how they drift.
    """

    position: int | None
    ordered: list[Sibling]


def place_among(
    siblings: Listing[Sibling],
    record: Sibling,
    after: SiblingId | None,
) -> Placement:
    """Drop `record` into its group, below `after`.

    `siblings` must already exclude the record being placed: it is being moved, so it is
    not one of the neighbours it is being moved between. Leaving it in would let something
    be dropped "after itself" and compute a midpoint against its own position.

    `after` may name a sibling **of any kind**, which is the whole of #101's fix. An
    anchor that is not in this group raises `AnchorNotAvailable`, and still says only that
    it was not found — an id from another act, another campaign, or one deleted while the
    page was open all answer alike.

    The caller no longer supplies that exception. It used to pass its own, which meant a
    scene refused for an unresolvable anchor was told "Scene not found" about the scene it
    had just asked to move (#110). What is missing is the anchor, and only this module is
    in a position to know that.

    The arithmetic was written out three times, once per level, and was identical each
    time. It is here now so that a fix to it is a fix everywhere, which is #80's "the
    tree's rules live in one place rather than in three services".
    """
    index = index_after(siblings, after, AnchorNotAvailable)

    position = position_between(
        siblings[index - 1].position if index > 0 else None,
        siblings[index].position if index < len(siblings) else None,
    )

    return Placement(position=position, ordered=[*siblings[:index], record, *siblings[index:]])
