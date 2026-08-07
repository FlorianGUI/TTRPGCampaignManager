from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.common.ids import PasswordResetId, UserId


@dataclass
class PasswordReset:
    """One emailed reset link, and whether it has been spent.

    Its own table rather than sharing `email_verifications` with a purpose column, and the
    differences are the argument: this one lives an hour rather than a day, has no session
    to belong to — the caller is signed out by definition — and spending it takes the
    account over rather than confirming a fact about it. Two rows with the same shape and
    nothing else in common is a coincidence, not a concept.

    Only the hash is stored. A dump of this table is worth more than a dump of any other
    here, so the secret exists for exactly as long as it takes to put it in a message.
    """

    user_id: UserId
    token_hash: str
    expires_at: datetime
    id: PasswordResetId = field(default_factory=lambda: PasswordResetId(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    used_at: datetime | None = None

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def has_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def use(self, now: datetime) -> None:
        """Spend the link, keeping the first use's timestamp.

        Single use is not a nicety here: a reset link that worked twice would let anyone
        who read the message once take the account back after the owner had recovered it.
        """
        if self.used_at is None:
            self.used_at = now
