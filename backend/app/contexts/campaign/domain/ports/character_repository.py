from abc import ABC, abstractmethod
from uuid import UUID

from app.contexts.campaign.domain.character import Character


class CharacterRepository(ABC):
    """Every read is scoped to one campaign.

    Who may reach that campaign is settled before any of these are called, so there is
    nothing left for the repository to decide — but the campaign still travels with
    each read, so a character cannot be fetched by id alone and turn up from a table
    the caller never asked about.
    """

    @abstractmethod
    async def save(self, character: Character) -> Character: ...

    @abstractmethod
    async def find_by_id_in(self, id: UUID, campaign_id: UUID) -> Character | None: ...

    @abstractmethod
    async def find_all_in(self, campaign_id: UUID) -> list[Character]: ...
