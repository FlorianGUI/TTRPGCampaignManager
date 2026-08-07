from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.common.ids import EmailVerificationId, SessionId, UserId


@dataclass
class EmailVerification:
    """One emailed link, and whether it has been walked through yet.

    Only the hash is stored, for the same reason a refresh token's is: a database dump
    should not be a drawer full of working links. The secret exists for exactly as long as
    it takes to put it in a message.

    `used_at` is a timestamp rather than a flag because single-use is the point and the
    moment it was spent is the only record of when. Re-presenting a spent link is not an
    error worth distinguishing to the caller — it usually means someone clicked twice, or
    a mail client prefetched the URL — but it must not verify the address a second time.

    `session_id` is the session that asked for it, and it is what makes the re-send cap
    reset on sign-in without storing a counter anywhere: signing in starts a new session,
    so counting rows for the current one starts again from zero.
    """

    user_id: UserId
    session_id: SessionId
    token_hash: str
    expires_at: datetime
    id: EmailVerificationId = field(default_factory=lambda: EmailVerificationId(uuid4()))
    # When the message went out, which is what the cooldown measures from. Not derivable
    # from `expires_at`: that would break the moment the configured lifetime changed, and
    # break silently, on rows written before the change.
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    used_at: datetime | None = None

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def has_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def use(self, now: datetime) -> None:
        """Spend the link, keeping the first use's timestamp.

        Overwriting would move the moment it was used forward every time someone clicked
        an old mail, which is the opposite of what the record is for.
        """
        if self.used_at is None:
            self.used_at = now
