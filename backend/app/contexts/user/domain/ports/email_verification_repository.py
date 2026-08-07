from abc import ABC, abstractmethod
from datetime import datetime

from app.common.ids import SessionId, UserId
from app.contexts.user.domain.email_verification import EmailVerification


class EmailVerificationRepository(ABC):
    @abstractmethod
    async def save(self, verification: EmailVerification) -> EmailVerification: ...

    @abstractmethod
    async def find_by_hash(self, token_hash: str) -> EmailVerification | None:
        """Look a link up by what was emailed, which is all a caller ever presents."""

    @abstractmethod
    async def count_for_session(self, session_id: SessionId) -> int:
        """How many links this session has already asked for.

        The re-send cap is this number, which is why nothing stores a counter: signing in
        starts a new session, so the count starts again at zero without anything having to
        reset it.
        """

    @abstractmethod
    async def last_sent_at(self, user_id: UserId) -> datetime | None:
        """When this account was last emailed a link, for the cooldown.

        Keyed on the user rather than the session, deliberately: the cap resets when you
        sign in and this must not, or signing out and back in would be a way around it.
        """
