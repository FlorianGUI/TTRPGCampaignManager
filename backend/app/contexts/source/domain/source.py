from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Source:
    """Where material was gathered from: a book, a magazine issue, homemade notes.

    A source belongs to the game master who added it; what they browse is simply the
    set of sources they own, so there is nothing above this entity to model.
    """

    title: str
    owner_id: UUID
    id: UUID = field(default_factory=uuid4)
