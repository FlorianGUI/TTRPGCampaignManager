from abc import ABC, abstractmethod

from app.common.access import Unsafe
from app.common.ids import ActId, SequenceId
from app.contexts.campaign.domain.narrative_access import SequenceAccess
from app.contexts.campaign.domain.sequence import Sequence


class SequenceRepository(ABC):
    """Like the act port, plus the one thing a middle level needs: a parent to count from.

    `last_position_under` takes the act rather than only the token, because **a position
    is only meaningful among the children of one parent**. Two sequences under different
    acts may share a number and nothing is wrong; two under the same act sharing one is
    the tie `find_all_in` breaks by id.

    `act_id=None` is not a missing argument, it is the campaign — the sequences that skip
    the act level are as much a sibling group as any act's children, and they order among
    themselves.
    """

    @abstractmethod
    async def save(self, sequence: Sequence) -> Sequence: ...

    @abstractmethod
    async def find_by_id(self, id: SequenceId) -> Unsafe[Sequence]: ...

    @abstractmethod
    async def find_all_in(self, access: SequenceAccess) -> list[Sequence]:
        """Every sequence in the campaign, whatever it hangs off.

        Campaign-wide rather than per-act on purpose: the read that matters is the whole
        tree at once (#88's structure query), and an endpoint that could only list one
        act's sequences would have to be called once per act to draw a campaign.
        """

    @abstractmethod
    async def last_position_under(self, access: SequenceAccess, act_id: ActId | None) -> int | None:
        """The highest position among the sequences under this act, or under no act."""

    @abstractmethod
    async def delete(self, id: SequenceId) -> None:
        """Unscoped on purpose: the caller reached this through a token method already."""

    @abstractmethod
    async def delete_all_in(self, access: SequenceAccess) -> None:
        """Empty a campaign of its sequences, for when the campaign itself goes."""
