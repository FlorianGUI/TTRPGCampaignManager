import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SourceModel(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    # No foreign key to users: the contexts stay independent at the schema level too.
    # Scoping reads to the owner is the security layer's job, tracked in #12.
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
