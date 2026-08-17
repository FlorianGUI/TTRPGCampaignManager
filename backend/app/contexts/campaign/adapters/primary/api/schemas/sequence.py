from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.markdown import CampaignMarkdown


class SequenceCreate(BaseModel):
    title: str = Field(max_length=200)
    description: CampaignMarkdown = ""
    # Omitted or null puts the sequence under the campaign itself, which is a parent and
    # not the absence of one — #80's skippable levels, as a request body.
    act_id: UUID | None = None


class SequenceUpdate(BaseModel):
    """What the sequence says. Where it sits is `PUT .../parent`.

    Kept apart deliberately: an update that also carried `act_id` would mean every rename
    sends one, and a stale value from a client that reorganised in another tab would move
    the sequence and everything under it without anyone asking for that.
    """

    title: str = Field(max_length=200)
    description: CampaignMarkdown = ""


class SequenceResponse(BaseModel):
    id: UUID
    title: str
    description: CampaignMarkdown
    campaign_id: UUID
    act_id: UUID | None
    position: int
    created_at: datetime
    updated_at: datetime
