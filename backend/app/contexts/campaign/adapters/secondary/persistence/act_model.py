import uuid

from sqlalchemy import Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampedModel


class ActModel(Base, TimestampedModel):
    __tablename__ = "acts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    # Grouping carries a description, not a body — the content is in the scenes. Same
    # dialect as a scene body and equally unread here.
    description: Mapped[str] = mapped_column(Text, default="")
    # Not a foreign key, matching every other link in this context. Deleting a campaign
    # deletes its acts — an application rule carried out by CampaignService.
    campaign_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    position: Mapped[int] = mapped_column(Integer)
