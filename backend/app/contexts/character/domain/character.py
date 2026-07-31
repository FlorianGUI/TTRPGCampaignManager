from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Character:
    """A character sheet, linked both to the user who owns it and to at most one campaign.

    Those two links are what decides who may read and write it: its owner, and the game
    master running the campaign it sits in. `campaign_id` is nullable because a character
    can exist outside any campaign — someone rolls one up before there is a table to
    bring it to.
    """

    name: str
    character_class: str
    owner_id: UUID
    level: int = 1
    campaign_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
