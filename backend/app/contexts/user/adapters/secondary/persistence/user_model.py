import uuid

from sqlalchemy import Boolean, String, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    # Still unique. An address identifies a person for password reset and for verification
    # (#38), and two rows holding one address makes both of those ambiguous. It also means
    # a provider sign-in for an address that already has an account cannot quietly create a
    # second one — it has to be handled, which is the safe behaviour anyway (#36, #39).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Nullable: an account created through a provider has never had a password.
    hashed_password: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # server_default kept rather than dropped after the backfill, so a row inserted by
    # anything that is not this model — a fixture, a migration, psql at 2am — is unverified
    # rather than rejected. False is the only safe default for this column.
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false(), default=False)
