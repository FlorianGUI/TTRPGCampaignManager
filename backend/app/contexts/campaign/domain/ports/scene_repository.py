from abc import ABC, abstractmethod

from app.common.access import Unsafe
from app.common.ids import ActId, SceneId, SequenceId
from app.contexts.campaign.domain.narrative_access import SceneAccess
from app.contexts.campaign.domain.scene import Scene


class SceneRepository(ABC):
    """The same split as `CharacterRepository`, for the same reason.

    `find_by_id` takes a bare id and applies no rule — whether the row is this viewer's
    is `SceneAccess`'s question, asked in the domain where it can be read and tested,
    rather than a WHERE clause nobody can see. The bulk reads keep the campaign in the
    query, because the alternative is loading every scene in the database and discarding
    most of them in Python.

    Read the character port for the longer argument, including the cost: a bare
    `find_by_id` is reachable, and what stops it leaking is that it returns `Unsafe` and
    the only sensible way to open one is a token method.
    """

    @abstractmethod
    async def save(self, scene: Scene) -> Scene: ...

    @abstractmethod
    async def find_by_id(self, id: SceneId) -> Unsafe[Scene]: ...

    @abstractmethod
    async def find_all_in(self, access: SceneAccess) -> list[Scene]:
        """In narrative order, which is `position` — decided by the query, not the client.

        #80 is explicit that ordering is applied here rather than left to whoever renders
        it: two callers sorting for themselves is two chances to disagree about what order
        the story goes in.
        """

    @abstractmethod
    async def last_position_under(
        self, access: SceneAccess, act_id: ActId | None, sequence_id: SequenceId | None
    ) -> int | None:
        """The highest position among the scenes under this parent, or `None` if it is empty.

        Exists so that appending a scene does not have to load every sibling to find out
        where the end is — the whole point of the sparse scheme is that placing a record
        is arithmetic, and this is the one number the arithmetic needs.

        **The parent is part of the question, not a filter on the answer.** A position is
        only meaningful among the children of one parent, so a scene appended to an act
        counts from that act's scenes and not from the campaign's. Both ids `None` is the
        campaign itself — a legitimate parent under #80's skippable levels, and the whole
        of a one-shot.
        """

    @abstractmethod
    async def delete(self, id: SceneId) -> None:
        """Unscoped on purpose: the caller reached this through a token method already."""

    @abstractmethod
    async def delete_all_in(self, access: SceneAccess) -> None:
        """Empty a campaign of its prep, for when the campaign itself goes.

        Deleting nothing is not an error, the same way it is not for characters: a
        campaign nobody wrote a scene in is an ordinary campaign.
        """
