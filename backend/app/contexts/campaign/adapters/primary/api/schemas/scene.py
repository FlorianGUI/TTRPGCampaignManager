from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.common.markdown import CampaignMarkdown
from app.contexts.campaign.domain.scene import SceneStatus


class OneParent(BaseModel):
    """A scene hangs off an act, a sequence, or the campaign — never two of them.

    Rejecting both here rather than in the domain is what makes it a **422 and not a 500**.
    `Scene.__post_init__` guards the same thing, but that guard exists to catch a bug in
    this codebase; this is the one that answers a caller, and it says which two fields are
    the problem rather than leaving them to guess from a stack trace.

    Both omitted is not an error and never should be: that is the campaign, and it is the
    whole of a one-shot.
    """

    act_id: UUID | None = None
    sequence_id: UUID | None = None

    @model_validator(mode="after")
    def _one_parent_at_most(self) -> Self:
        if self.act_id is not None and self.sequence_id is not None:
            raise ValueError("A scene hangs off an act or a sequence, not both")
        return self


class SceneCreate(OneParent):
    title: str = Field(max_length=200)
    body: CampaignMarkdown = ""
    status: SceneStatus = SceneStatus.PLANNED


class SceneUpdate(BaseModel):
    """What the scene says. Where it sits is `PUT .../parent`.

    A full replacement, not a patch: every field is sent on every write, so a body left
    out is cleared rather than kept. #88's editor depends on knowing which of the two this
    is.

    No parentage here on purpose — see `SequenceUpdate` for the argument. It matters more
    for a scene, because the common write is a long body typed over an hour, and that is
    exactly the request most likely to be carrying a stale parent.
    """

    title: str = Field(max_length=200)
    body: CampaignMarkdown = ""
    status: SceneStatus = SceneStatus.PLANNED


class ScenePlacement(OneParent):
    """Where the scene sits: which parent, and where among its siblings.

    One body for one gesture — a drag can cross acts and land mid-list at once, and two
    requests would leave a visible wrong order between them if the second failed. Both
    parent ids null is the campaign; `after` null is first.
    """

    after: UUID | None = None


class SceneResponse(BaseModel):
    id: UUID
    title: str
    body: CampaignMarkdown
    status: SceneStatus
    campaign_id: UUID
    # The direct parent, and at most one is ever set. A scene under a sequence does not
    # report that sequence's act — a client that wants the whole tree reads the whole
    # tree, rather than trusting a copy that a move could have left stale.
    act_id: UUID | None
    sequence_id: UUID | None
    position: int
    created_at: datetime
    updated_at: datetime
