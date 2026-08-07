import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailVerificationModel(Base):
    """One emailed verification link.

    A row per link rather than a column on `users`, because the re-send cap and the
    cooldown are both questions about *how many* and *how recently* — which a single
    current-token column could not answer. It also means an old link keeps working until it
    expires, so asking for a new one does not break the mail already sitting in an inbox.

    No foreign key on `user_id`, matching every other table here.
    """

    __tablename__ = "email_verifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # Which session asked. Counting rows for the current session is the re-send cap, which
    # is why no counter is stored anywhere.
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # The hash, never the secret. Unique so a lookup cannot be ambiguous, and indexed
    # because finding by it is the only way a link is ever resolved.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
