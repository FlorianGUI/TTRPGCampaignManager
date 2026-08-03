from abc import ABC, abstractmethod
from datetime import datetime

from app.common.ids import SessionId
from app.contexts.user.domain.refresh_token import RefreshToken


class RefreshTokenRepository(ABC):
    """Where sessions are remembered, which is what makes them revocable.

    An access token is checked by its signature and nothing else, so nothing can withdraw
    one before it expires. Refresh tokens are the opposite by design: every use is a
    lookup here, and that lookup is the hook logout and reuse detection both hang on.

    Note `find_by_hash` returns the token whether or not it is still usable, rather than
    filtering the dead ones out. A revoked token that comes back is the single most
    important signal this system has — it means the secret is in more than one pair of
    hands — and a repository that quietly answered "no such token" would throw it away.
    Deciding what a revoked or expired token means belongs to the service.
    """

    @abstractmethod
    async def save(self, token: RefreshToken) -> RefreshToken: ...

    @abstractmethod
    async def find_by_hash(self, token_hash: str) -> RefreshToken | None: ...

    @abstractmethod
    async def revoke_session(self, session_id: SessionId, at: datetime) -> None:
        """Retire every token in the session, live or already rotated away.

        Whole-session because that is the unit that survives rotation: revoking only the
        token in hand would leave the one it was rotated into working, which is neither
        logging out nor containing a leak.
        """
