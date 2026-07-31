from uuid import UUID

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str
    description: str | None = None


class CampaignUpdate(BaseModel):
    name: str
    description: str | None = None


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
