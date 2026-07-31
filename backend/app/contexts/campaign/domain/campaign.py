from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Campaign:
    """A game master's table: the thing play happens around.

    A campaign has exactly one owner. Inviting other users to it is real and planned
    but lands in #31 through a membership table, so ownership is the whole of the
    access story for now.
    """

    name: str
    owner_id: UUID
    description: str | None = None
    id: UUID = field(default_factory=uuid4)
