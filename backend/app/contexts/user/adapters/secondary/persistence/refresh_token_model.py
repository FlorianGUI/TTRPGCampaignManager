import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # Indexed because it is what revocation works on: ending a session updates every row
    # sharing this value, and reuse detection does it on the hot path of a rejected refresh.
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # The SHA-256 hex digest, never the token. Sixty-four characters exactly, and unique
    # because two live sessions sharing a hash would mean the generator repeated itself.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # timezone=True throughout: these are compared against an aware datetime.now(UTC), and
    # a naive column would make that comparison raise rather than quietly answer wrong.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
