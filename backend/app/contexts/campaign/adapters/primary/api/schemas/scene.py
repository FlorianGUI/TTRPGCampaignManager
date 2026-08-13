from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.markdown import CampaignMarkdown
from app.contexts.campaign.domain.scene import SceneStatus


class SceneCreate(BaseModel):
    title: str = Field(max_length=200)
    body: CampaignMarkdown = ""
    status: SceneStatus = SceneStatus.PLANNED


class SceneUpdate(BaseModel):
    """A full replacement, not a patch — the rule `PUT /campaigns/{id}` already follows.

    Every field is sent on every write, so a body left out of the request is cleared
    rather than kept. The frontend depends on knowing which of the two this is: #88's
    inline description edit is only safe because the client sends the whole record.

    `body` and `status` carry defaults so a title-only rename is one field, which is the
    common edit — and the default is the same "" the create schema uses, so a rename that
    omits the body clears it rather than doing something surprising. That is the full
    replacement rule being consistent, not an exception to it.
    """

    title: str = Field(max_length=200)
    body: CampaignMarkdown = ""
    status: SceneStatus = SceneStatus.PLANNED


class SceneResponse(BaseModel):
    id: UUID
    title: str
    body: CampaignMarkdown
    status: SceneStatus
    campaign_id: UUID
    # On the way out only, like the timestamps below it. Where a scene sits among its
    # siblings is the campaign's business, not something a caller asserts on a write —
    # a create appends, and moving one is PR 3's own endpoint. Sending it here would
    # invite a client to reorder by editing, which is the thing an explicit position
    # exists to prevent.
    position: int
    # What a record says about itself is not something a caller sends: both are written
    # by the domain, and a request carrying them would be asking the server to lie about
    # when something happened.
    created_at: datetime
    updated_at: datetime
