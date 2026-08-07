from abc import ABC, abstractmethod

from app.contexts.user.domain.password_reset import PasswordReset


class PasswordResetRepository(ABC):
    @abstractmethod
    async def save(self, reset: PasswordReset) -> PasswordReset: ...

    @abstractmethod
    async def find_by_hash(self, token_hash: str) -> PasswordReset | None:
        """Look a link up by what was emailed, which is all a caller ever presents.

        Returns it whether or not it is still usable, like `RefreshTokenRepository` does
        and for the same reason: deciding what a spent or expired token means belongs to
        the service, not to the store.
        """
