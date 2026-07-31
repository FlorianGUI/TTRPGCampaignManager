from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.contexts.character.domain.character import Character


class CharacterRepository(ABC):
    """Reads carry the viewer, and the campaigns that viewer runs.

    A character is visible to the user who owns it and to the game master whose
    campaign it sits in, so a read needs both halves of the rule. There is
    deliberately no unscoped `find_all()` / `find_by_id(id)`: leaving them out makes
    an unfiltered read a type error rather than a silent leak.
    """

    @abstractmethod
    async def save(self, character: Character) -> Character: ...

    @abstractmethod
    async def find_by_id_visible_to(
        self, id: UUID, viewer_id: UUID, campaign_ids: Sequence[UUID]
    ) -> Character | None: ...

    @abstractmethod
    async def find_all_visible_to(self, viewer_id: UUID, campaign_ids: Sequence[UUID]) -> list[Character]: ...
