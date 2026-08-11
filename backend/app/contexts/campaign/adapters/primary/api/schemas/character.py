from datetime import datetime
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
    # On the way out only. What a record says about itself is not something a caller
    # sends: both are written by the domain, and a request that carried them would be
    # asking the server to lie about when something happened.
    created_at: datetime
    updated_at: datetime
