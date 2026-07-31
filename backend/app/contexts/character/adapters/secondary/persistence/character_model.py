import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CharacterModel(Base):
    __tablename__ = "characters"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    character_class: Mapped[str] = mapped_column(String(50))
    level: Mapped[int] = mapped_column(default=1)
    # Neither link is a foreign key, matching sources.owner_id: the contexts stay
    # independent at the schema level. Both cascades are application-level rules —
    # deleting a user deletes their characters, and deleting a campaign unlinks the
    # characters at its table rather than deleting them (#12, #14).
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, index=True, nullable=True)
