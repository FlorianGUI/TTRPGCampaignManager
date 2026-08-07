from abc import ABC, abstractmethod

from app.common.ids import UserId
from app.contexts.user.domain.user import User


class UsernameTakenError(Exception):
    """`save` lost a race for a username, or was simply given one that exists.

    Raised by the store rather than discovered by looking first, because looking first
    cannot be made correct: between the check and the insert another request can take the
    name, and the loser gets an integrity error from the driver — a 500 where a 409 or a
    retry belonged. The unique index is the only thing that actually decides, so this is
    the index's answer, translated.
    """


class EmailTakenError(Exception):
    """The same, for the address.

    Separate from the above because the recovery is different: a taken username can be
    retried with another name, a taken address cannot — it belongs to an account already,
    and that is a fact to report rather than work around.
    """


class UserRepository(ABC):
    @abstractmethod
    async def save(self, user: User) -> User:
        """Persist the user, or raise `UsernameTakenError` / `EmailTakenError`."""

    @abstractmethod
    async def find_by_id(self, id: UserId) -> User | None: ...

    @abstractmethod
    async def find_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def mark_email_verified(self, id: UserId) -> None:
        """Record that this address has been proved.

        Its own method rather than a general `update`, because `save` here inserts — a
        second one for an existing user collides on the primary key. A targeted write is
        also the right shape for this particular change: it touches one column, so it
        cannot lose a concurrent edit to another one the way a read-modify-write would.
        """
