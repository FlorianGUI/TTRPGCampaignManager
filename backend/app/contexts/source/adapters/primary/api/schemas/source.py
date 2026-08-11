from datetime import datetime
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
    # On the way out only. What a record says about itself is not something a caller
    # sends: both are written by the domain, and a request that carried them would be
    # asking the server to lie about when something happened.
    created_at: datetime
    updated_at: datetime
