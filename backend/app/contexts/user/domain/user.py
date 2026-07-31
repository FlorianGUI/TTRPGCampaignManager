from dataclasses import dataclass, field
from uuid import uuid4

from app.common.ids import UserId


@dataclass
class User:
    username: str
    email: str
    hashed_password: str
    id: UserId = field(default_factory=lambda: UserId(uuid4()))
