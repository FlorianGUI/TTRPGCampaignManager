from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from app.common.ids import RefreshTokenId, SessionId, UserId


@dataclass
class RefreshToken:
    """One link in the chain a single sign-in leaves behind.

    Each refresh replaces the token it was given with a new one, so a session is not one
    token but a succession of them — the `session_id` is what ties them together, and it
    is the unit everything interesting operates on. Logging out revokes a session, not a
    token; a replayed token condemns its session, not itself.

    Only the hash is ever stored, so this holds `token_hash` rather than the secret. The
    secret exists for exactly as long as it takes to put it in a cookie.

    Revocation is a timestamp rather than a flag because the two questions it answers are
    different and both get asked: whether the token still works, and when it stopped —
    which is what tells a replay apart from a token that was never issued here.
    """

    user_id: UserId
    session_id: SessionId
    token_hash: str
    expires_at: datetime
    id: RefreshTokenId = field(default_factory=lambda: RefreshTokenId(uuid4()))
    revoked_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def has_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def revoke(self, now: datetime) -> None:
        """Retire the token, keeping the first refusal's timestamp.

        Rotation revokes the token it just consumed, and logging out revokes every token
        in the session including ones rotation already retired. Overwriting would move the
        moment a token stopped working forward every time something touched it, and that
        moment is the only forensic record of when a session ended.
        """
        if self.revoked_at is None:
            self.revoked_at = now
