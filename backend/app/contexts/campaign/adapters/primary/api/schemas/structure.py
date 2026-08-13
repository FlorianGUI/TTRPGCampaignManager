from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.common.markdown import CampaignMarkdown
from app.contexts.campaign.domain.scene import SceneStatus


class StructureAct(BaseModel):
    id: UUID
    title: str
    description: CampaignMarkdown
    position: int
    created_at: datetime
    updated_at: datetime


class StructureSequence(BaseModel):
    id: UUID
    title: str
    description: CampaignMarkdown
    act_id: UUID | None
    position: int
    created_at: datetime
    updated_at: datetime


class StructureScene(BaseModel):
    """A scene as the tree sees it. **No `body`, and that is the point of the endpoint.**

    Not an omission a caller should work around by fetching each scene: a body is read one
    at a time, on the page that shows it. An outline that wanted a preview of each would
    have to compute it on the client from bodies it already holds — see #80 for why
    deriving one here would mean the API learning the #53 dialect.
    """

    id: UUID
    title: str
    status: SceneStatus
    act_id: UUID | None
    sequence_id: UUID | None
    position: int
    created_at: datetime
    updated_at: datetime


class StructureResponse(BaseModel):
    """The campaign's tree as three ordered lists. See `Structure` for why it is flat.

    `campaign_id` is not repeated on every row. One request is one campaign — it is in the
    path, every row in the answer belongs to it, and saying so a few hundred times would
    only invite a client to trust a copy instead of the request it made.
    """

    acts: list[StructureAct]
    sequences: list[StructureSequence]
    scenes: list[StructureScene]
