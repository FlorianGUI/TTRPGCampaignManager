from abc import ABC, abstractmethod
from uuid import UUID

from app.common.access import Unsafe
from app.contexts.source.domain.source import Source


class SourceRepository(ABC):
    """Same split as the campaign's, for the same reasons.

    `find_all_for` still filters in the query, because a list cannot afford to load rows
    it will discard. `find_by_id` does not, because a single row costs nothing to fetch
    and the rule reads better in `source.readable` than in a WHERE clause.

    #41 wrote here that leaving out an unscoped `find_by_id` made the omission a type
    error rather than a silent leak, and that was true and is now given up. What replaces
    it is that the rule is stated once, in the domain, where it can be read and tested —
    rather than in SQL, in the fake, and in prose, agreeing by hand.
    """

    @abstractmethod
    async def save(self, source: Source) -> Source: ...

    @abstractmethod
    async def find_by_id(self, id: UUID) -> Unsafe[Source]: ...

    @abstractmethod
    async def find_all_for(self, owner_id: UUID) -> list[Source]: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None:
        """Unscoped on purpose: the caller reached this id through `editable` already."""
