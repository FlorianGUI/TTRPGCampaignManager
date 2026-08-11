import uuid

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampedModel


class CharacterModel(Base, TimestampedModel):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Neither link is a foreign key, matching sources.owner_id and campaigns.owner_id.
    #
    # campaign_id is not null: a character belongs to exactly one table. Deleting a
    # campaign deletes the characters at it — an application rule carried out by
    # CampaignService, not an ON DELETE CASCADE, and unimplemented until a campaign
    # delete endpoint exists (#12, #43).
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
