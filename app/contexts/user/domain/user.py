from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class User:
    username: str
    email: str
    hashed_password: str
    id: UUID = field(default_factory=uuid4)