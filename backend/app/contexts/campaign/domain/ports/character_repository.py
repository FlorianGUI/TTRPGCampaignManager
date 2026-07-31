from abc import ABC, abstractmethod
from uuid import UUID

from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.character_access import CharacterAccess


class CharacterRepository(ABC):
    """Fetching one sheet asks no questions; fetching many cannot afford not to.

    That split is deliberate and is the only asymmetry here worth explaining.

    `find_by_id` takes a bare id and applies no rule. It used to filter on the campaign,
    which meant the rule "a sheet belongs to the table you reached" was written in a
    WHERE clause where it could not be read, tested, or reasoned about — and written a
    second time in the fake, and a third time in prose. It now lives once, in
    `CharacterAccess.readable`, and this method's job is only to answer whether a row
    exists.

    `find_all_in` keeps the campaign in its query, because the alternative is loading
    every character in the database and discarding most of them in Python. #12 rules
    that out in as many words: filtered in the query, not after the fact. One row is a
    lookup; all rows is a scan.

    The cost of the first half, stated plainly: #41 removed unscoped reads so that an
    unauthorised one could not be *written*. A bare `find_by_id` is reachable again, and
    what stops it leaking is now that its return type is Optional and the only sensible
    way to open it is a token method. That is a weaker guarantee than a type error, and
    it buys a rule that exists in one place instead of three.

    `save` takes only the character because whoever built it needed a token to do so:
    `CharacterService.create` stamps both from the token rather than from
    anything the caller sent.
    """

    @abstractmethod
    async def save(self, character: Character) -> Character: ...

    @abstractmethod
    async def find_by_id(self, id: UUID) -> Character | None: ...

    @abstractmethod
    async def find_all_in(self, access: CharacterAccess) -> list[Character]: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Unscoped on purpose: the caller reached this through a token method already."""

    @abstractmethod
    async def delete_all_in(self, access: CharacterAccess) -> None:
        """Empty a table of its sheets, for when the table itself goes.

        Deleting nothing is not an error: a campaign nobody put a character at is an
        ordinary campaign, not a failed delete.
        """
