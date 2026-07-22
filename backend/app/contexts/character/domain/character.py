from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Character:
    name: str
    character_class: str
    level: int = 1
    id: UUID = field(default_factory=uuid4)
