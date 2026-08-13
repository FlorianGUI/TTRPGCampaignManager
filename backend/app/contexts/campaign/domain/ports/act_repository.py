from abc import ABC, abstractmethod

from app.common.access import Unsafe
from app.common.ids import ActId
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.narrative_access import ActAccess


class ActRepository(ABC):
    """The same split as the other two: single-row reads carry no rule, bulk reads do.

    See `SceneRepository` for the argument, which is the same one in every port in this
    context. Acts are the simplest of the three — the top of the tree has no parentage,
    so its siblings are always "the acts of this campaign" and there is one ordering
    scope rather than several.
    """

    @abstractmethod
    async def save(self, act: Act) -> Act: ...

    @abstractmethod
    async def find_by_id(self, id: ActId) -> Unsafe[Act]: ...

    @abstractmethod
    async def find_all_in(self, access: ActAccess) -> list[Act]:
        """In `position` order, decided here rather than by whoever renders it."""

    @abstractmethod
    async def find_under(self, access: ActAccess) -> list[Act]:
        """The campaign's acts, in order — which for the top of the tree is every act.

        Named for the shape the other two share rather than for what it does here, so a
        reorder reads the same at all three levels. It is the sibling list a drop is placed
        into, and an act is the one level whose siblings are always the whole campaign's.
        """

    @abstractmethod
    async def last_position_in(self, access: ActAccess) -> int | None:
        """The highest position among the campaign's acts, or `None` if it has none."""

    @abstractmethod
    async def delete(self, id: ActId) -> None:
        """Unscoped on purpose: the caller reached this through a token method already.

        What happens to the children of a deleted act — refuse, or rehome them to the
        campaign — is #80's open question and PR 3's to answer. Until then this deletes
        one row and leaves its children where they are, which is why the acceptance suite
        only deletes empty acts.
        """

    @abstractmethod
    async def delete_all_in(self, access: ActAccess) -> None:
        """Empty a campaign of its acts, for when the campaign itself goes."""
