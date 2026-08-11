from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.common.errors import NotAvailable
from app.common.ids import CampaignId, CharacterId, UserId


class CharacterNotAvailable(NotAvailable):
    """No such sheet at this table, or not one this viewer may touch.

    One exception for both, so a caller holding a real character id from someone else's
    campaign learns exactly as much as one guessing at random.
    """

    detail = "Character not found"


@dataclass
class Character:
    """A character sheet at a table.

    A character always belongs to exactly one campaign — that is what makes it part of
    this context rather than one of its own. It also records the user who owns it,
    which is the same person as the campaign's owner until #31 lets a game master
    invite players to their table.

    There is deliberately no class and no level: this app gathers material for a game
    master, it does not compute anything from a character sheet. Whatever matters about
    a character goes in the description, which can hold the things two D&D columns
    could not.
    """

    name: str
    owner_id: UserId
    campaign_id: CampaignId
    description: str | None = None
    id: CharacterId = field(default_factory=lambda: CharacterId(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def revise(self, name: str, description: str | None) -> None:
        """Rewrite the sheet, and record that it was rewritten.

        The same shape as `Campaign.revise`, and for the same reason: a timestamp that
        depends on every caller remembering to set it is a timestamp that is wrong as
        soon as someone does not.
        """
        self.name = name
        self.description = description
        self.updated_at = datetime.now(UTC)
