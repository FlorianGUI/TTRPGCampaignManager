import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PasswordResetModel(Base):
    """An emailed password-reset link.

    Separate from `email_verifications` deliberately — see the note on the domain entity.
    No session_id here, because the caller is signed out by definition: someone who could
    sign in would not be resetting.

    No foreign key on user_id, matching every other table here.
    """

    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # The hash, never the secret. Unique so a lookup cannot be ambiguous.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
