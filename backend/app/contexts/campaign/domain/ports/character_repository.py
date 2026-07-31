from abc import ABC, abstractmethod
from uuid import UUID

from app.contexts.campaign.domain.access import CampaignAccess
from app.contexts.campaign.domain.character import Character


class CharacterRepository(ABC):
    """Every read and write is located by an access token, never by a bare campaign id.

    The token is both the campaign to filter on and the proof that the caller may filter
    on it, which is the point: there is no `campaign_id: UUID` parameter left in this
    port for an unauthorised caller to supply. Where the source context made an
    unfiltered read impossible to write, this makes an unauthorised one impossible to
    write.

    `save` is the exception and takes only the character, because a character cannot be
    built without a token in the first place — `CampaignAccess.new_character` is its
    only constructor in application code, and it stamps the campaign and the owner from
    the proof rather than from anything the caller sent.
    """

    @abstractmethod
    async def save(self, character: Character) -> Character: ...

    @abstractmethod
    async def find_by_id_in(self, id: UUID, access: CampaignAccess) -> Character | None: ...

    @abstractmethod
    async def find_all_in(self, access: CampaignAccess) -> list[Character]: ...

    @abstractmethod
    async def delete_in(self, id: UUID, access: CampaignAccess) -> None: ...

    @abstractmethod
    async def delete_all_in(self, access: CampaignAccess) -> None:
        """Empty a table of its sheets, for when the table itself goes.

        Deleting nothing is not an error: a campaign nobody put a character at is an
        ordinary campaign, not a failed delete.
        """
