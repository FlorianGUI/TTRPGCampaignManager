"""One gesture, named: what was dragged, where it landed, and what it landed after.

The three levels each have a `place` on their own service, and those are not going away —
they carry the rules, and they are where the sibling list and the parent are resolved.
What was missing was a way to *say* a placement without knowing in advance which level it
is about, which is what a drag from a tree view produces: the outline knows it moved a row,
and only the id tells it which kind of row.

**The kind travels as data, not as a type.** `ActId` and friends are `NewType`s, so they
are plain `UUID`s the moment the program runs — a union of them cannot be matched on, and
anything that tried would be reading a tag that no longer exists. `NarrativeItem` keeps the
tag as a field for exactly that reason, and it is the field the service dispatches on.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.common.ids import ActId, SceneId, SequenceId


class NarrativeKind(StrEnum):
    """Which level of the tree a row belongs to."""

    ACT = "act"
    SEQUENCE = "sequence"
    SCENE = "scene"


@dataclass(frozen=True)
class NarrativeItem:
    """One row in the outline, identified well enough to act on without a lookup."""

    id: UUID
    kind: NarrativeKind

    def as_act(self) -> ActId:
        return ActId(self.id)

    def as_sequence(self) -> SequenceId:
        return SequenceId(self.id)

    def as_scene(self) -> SceneId:
        return SceneId(self.id)


@dataclass(frozen=True)
class Placement:
    """Where a row was dropped: under which parent, and after which sibling.

    `parent` is `None` for the campaign itself, which is a real parent here rather than a
    bin — #80's skippable levels mean a scene sitting directly on the campaign is as
    legitimate as one three levels down. `after` is `None` for the head of the list, which
    is an ordinary move and not a missing argument.

    **Both are needed, and `before` deliberately is not.** A single anchor cannot say which
    parent an empty list belongs to, which is why `parent` is here; a second anchor could
    contradict the first, which is why `before` is not. `index_after` and every existing
    placement body already work this way and this does not part from them.
    """

    item: NarrativeItem
    parent: NarrativeItem | None
    after: NarrativeItem | None
