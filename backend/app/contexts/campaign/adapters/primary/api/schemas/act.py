from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.markdown import CampaignMarkdown


class ActCreate(BaseModel):
    title: str = Field(max_length=200)
    description: CampaignMarkdown = ""


class ActUpdate(BaseModel):
    """A full replacement, not a patch — the rule every write in this API follows."""

    title: str = Field(max_length=200)
    description: CampaignMarkdown = ""


class ActPlacement(BaseModel):
    """Where the act sits among the campaign's acts.

    `after` names the sibling it was dropped below; null is first. An act has no parent to
    name, so placing one is entirely a question of order.
    """

    after: UUID | None = None


class ActResponse(BaseModel):
    id: UUID
    title: str
    description: CampaignMarkdown
    campaign_id: UUID
    # On the way out only. Where an act sits among its siblings is not something a caller
    # asserts on a write: creating appends, and moving is PR 3's own endpoint.
    position: int
    created_at: datetime
    updated_at: datetime
