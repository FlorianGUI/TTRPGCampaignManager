from uuid import UUID

from pydantic import BaseModel


class CharacterCreate(BaseModel):
    name: str
    description: str | None = None


class CharacterUpdate(BaseModel):
    name: str
    description: str | None = None


class CharacterResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    owner_id: UUID
    campaign_id: UUID
