from uuid import UUID

from pydantic import BaseModel


class SourceCreate(BaseModel):
    title: str


class SourceUpdate(BaseModel):
    # A full replacement rather than a patch: title is everything a source has.
    title: str


class SourceResponse(BaseModel):
    id: UUID
    title: str
    owner_id: UUID
