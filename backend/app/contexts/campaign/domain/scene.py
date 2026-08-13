from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from app.common.errors import NotAvailable
from app.common.ids import CampaignId, SceneId


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

    The bottom of the narrative tree and, in this PR, the whole of it. A scene hangs off
    the campaign directly here; #80's PR 2 adds acts and sequences above it and makes the
    parentage nullable, which is what lets a scene attach at any level. Landing this way
    round is deliberate: a campaign with scenes and no acts is a working campaign, and
    building the level that *cannot* be skipped first proves it rather than asserting it.

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
    id: SceneId = field(default_factory=lambda: SceneId(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

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
