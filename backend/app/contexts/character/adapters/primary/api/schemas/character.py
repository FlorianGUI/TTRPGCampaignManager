from uuid import UUID

from pydantic import BaseModel


class CharacterCreate(BaseModel):
    name: str
    character_class: str
    campaign_id: UUID | None = None


class CharacterUpdate(BaseModel):
    name: str
    character_class: str
    level: int = 1
    # Omitted or null takes the character off whatever table it was at, which is what
    # a full replacement should mean.
    campaign_id: UUID | None = None


class CharacterResponse(BaseModel):
    id: UUID
    name: str
    character_class: str
    level: int
    owner_id: UUID
    campaign_id: UUID | None
