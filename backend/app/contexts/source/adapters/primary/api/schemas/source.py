from uuid import UUID

from pydantic import BaseModel


class SourceCreate(BaseModel):
    title: str


class SourceResponse(BaseModel):
    id: UUID
    title: str
    owner_id: UUID
