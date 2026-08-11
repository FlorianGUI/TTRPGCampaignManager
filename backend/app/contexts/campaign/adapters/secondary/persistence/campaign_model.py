import uuid

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampedModel


class CampaignModel(Base, TimestampedModel):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # No foreign key to users, matching the sources table: the contexts stay
    # independent at the schema level, and deleting a user is an application-level
    # cascade rather than a database one (#12).
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
