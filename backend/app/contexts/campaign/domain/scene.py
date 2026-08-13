from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from app.common.errors import NotAvailable
from app.common.ids import ActId, CampaignId, SceneId, SequenceId


class SceneNotAvailable(NotAvailable):
    """No such scene in this campaign, or not one this viewer may touch.

    One exception for both, the way `CharacterNotAvailable` is: a caller holding a real
    scene id from someone else's campaign learns exactly as much as one guessing.
    """

    detail = "Scene not found"


class SceneStatus(StrEnum):
    """Whether the table has played this yet, as the game master marks it.

    Three values and not a boolean, because `skipped` is the interesting one: a scene
    that was cut in play is not the same as one still waiting, and a campaign that
    deleted its cut scenes would lose the reason the next act reads the way it does.

    **Set by hand, never derived.** #81 joins sessions to scenes, and it would be easy to
    let an appearance in a session log imply `played` — which is exactly the second source
    of truth #80 rules out. This is the game master's own mark on their own prep.

    An act's progress is read off these and is not stored anywhere; see #88 for what the
    frontend does with them.
    """

    PLANNED = "planned"
    PLAYED = "played"
    SKIPPED = "skipped"


@dataclass
class Scene:
    """A unit of play: one place, one cast — "The parley at Stonegate".

    The bottom of the narrative tree, and the one level that cannot be skipped.

    **Its parent is a sequence, an act, or the campaign itself**, which is what "the levels
    are skippable" means in columns: both parent ids are nullable and at most one is set,
    so a one-shot is scenes alone and an act-then-scene campaign never has to invent a
    sequence to hold anything. Nothing here is less valid than anything else — a scene with
    no parent is not an orphan, it belongs to the campaign, which is the only belonging
    the authorisation rule has ever cared about.

    `body` is `str` here and `CampaignMarkdown` at the HTTP boundary. The domain does not
    import pydantic, and more to the point it has no business knowing the field has a
    dialect: this layer stores what it was handed and hands it back unchanged. Nothing in
    this context ever reads inside it.

    `position` is not creation order and not a timestamp — see `position.py` for the
    scheme and why a timestamp would silently reorder a game master's story every time
    they edited an old scene.
    """

    title: str
    campaign_id: CampaignId
    position: int
    body: str = ""
    status: SceneStatus = SceneStatus.PLANNED
    act_id: ActId | None = None
    sequence_id: SequenceId | None = None
    id: SceneId = field(default_factory=lambda: SceneId(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """A scene has one parent, or none. Never two.

        Both columns set would be a scene claiming to hang off an act *and* a sequence,
        which is not a deeper tree but an ambiguous one — and if the sequence were under a
        different act, the two answers to "where is this scene" would disagree forever.
        Only the direct parent is stored; the act above a sequence is reached by looking,
        not by copying it down here where it can rot.

        A guard rather than a validation: the HTTP boundary rejects this with a 422 before
        it can reach the domain, so anything arriving here is a bug in this codebase and
        should read like one.
        """
        if self.act_id is not None and self.sequence_id is not None:
            raise ValueError("A scene hangs off an act or a sequence, not both")

    def revise(self, title: str, body: str, status: SceneStatus) -> None:
        """Rewrite the scene, and record that it was rewritten.

        The shape `Campaign.revise` and `Character.revise` already have, and #78's note
        about it applies with more force here than anywhere: this is the third entity to
        carry the pattern and PR 2 adds two more. A timestamp that depends on every
        caller remembering to set it is wrong the first time one does not.

        `position` is deliberately not a parameter. Reordering is its own operation with
        its own endpoint (PR 3) — folding it in here would mean every body edit sends a
        position, and a stale one from a client that reordered in another tab would
        quietly move the scene.
        """
        self.title = title
        self.body = body
        self.status = status
        self.updated_at = datetime.now(UTC)

    def reposition(self, position: int) -> None:
        """Take a new number in the same list, without claiming to have been edited.

        `updated_at` deliberately does not move. This is what a **neighbour** gets when
        someone else's drop exhausted the gap and the sibling list had to be renumbered —
        the record itself did not change, its surroundings did. Moving the timestamp on
        thirty rows because one scene was dragged past another would make "last changed"
        mean "was near something that moved", and every list ordered by it useless.

        The record being moved goes through `move_under` instead, which does move it.
        """
        self.position = position

    def move_under(self, act_id: ActId | None, sequence_id: SequenceId | None, position: int) -> None:
        """Reparent, and take a place among the new siblings.

        Scenes move between acts, get cut and come back, so parent is mutable — that is
        most of what #80 exists for. Parent and position move together because they are
        one fact: a position means nothing except among the children of one parent.

        Passing both ids raises, for the reason `__post_init__` gives. That the new parent
        belongs to this campaign is checked by whoever resolved the id, through the token
        — the sharp rule in #80, and it is deliberately not restated here.
        """
        if act_id is not None and sequence_id is not None:
            raise ValueError("A scene hangs off an act or a sequence, not both")

        self.act_id = act_id
        self.sequence_id = sequence_id
        self.position = position
        self.updated_at = datetime.now(UTC)
