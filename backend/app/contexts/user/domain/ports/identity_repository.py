from abc import ABC, abstractmethod

from app.common.ids import UserId
from app.contexts.user.domain.identity import Identity, Provider


class IdentityRepository(ABC):
    @abstractmethod
    async def save(self, identity: Identity) -> Identity: ...

    @abstractmethod
    async def find_by_subject(self, provider: Provider, subject: str) -> Identity | None:
        """The lookup a provider sign-in makes, and the only one it may make.

        Finding by address instead is the account-takeover route: an address can be
        reassigned to a different person, a `sub` cannot.
        """

    @abstractmethod
    async def find_for_user(self, user_id: UserId) -> list[Identity]:
        """Every way into one account.

        Needed before an identity can be detached — removing the last way in leaves an
        account nobody can reach — and to show someone what is linked.
        """
