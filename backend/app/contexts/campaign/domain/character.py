from dataclasses import dataclass, field
from uuid import UUID, uuid4


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
    owner_id: UUID
    campaign_id: UUID
    description: str | None = None
    id: UUID = field(default_factory=uuid4)
