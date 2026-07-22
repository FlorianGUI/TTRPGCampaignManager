from uuid import UUID

from pydantic import BaseModel


class CharacterCreate(BaseModel):
    name: str
    character_class: str


class CharacterResponse(BaseModel):
    id: UUID
    name: str
    character_class: str
    level: int
