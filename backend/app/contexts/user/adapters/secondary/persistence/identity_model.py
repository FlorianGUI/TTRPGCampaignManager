import uuid

from sqlalchemy import String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class IdentityModel(Base):
    """A provider sign-in, pointing at the account it reaches.

    A table rather than columns on `users`, because one account may hold several — a
    password, a Google identity and a Discord identity are three ways into one place. Every
    provider after the first is then a row, not a migration.

    No foreign key on `user_id`, matching every other table here; the schema has none
    anywhere.
    """

    __tablename__ = "user_identities"
    __table_args__ = (
        # The constraint that makes a sign-in unambiguous: one provider account maps to at
        # most one user. Without it a second row could quietly claim the same provider
        # subject for a different account, and which one a sign-in reached would depend on
        # row order.
        UniqueConstraint("provider", "subject", name="uq_user_identities_provider_subject"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    # Stored as the enum's plain string. A String rather than a database enum type so that
    # adding a provider is a deploy rather than a migration.
    provider: Mapped[str] = mapped_column(String(32))
    # The provider's `sub`. Length is generous: Google's is ~21 digits today, Discord's a
    # snowflake, and neither promises to stay that way.
    subject: Mapped[str] = mapped_column(String(255))
