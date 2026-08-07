from dataclasses import dataclass, field
from uuid import uuid4

from app.common.ids import UserId


@dataclass
class User:
    """An account, however its owner proves they are its owner.

    `hashed_password` is optional because an account reached through a provider (#36, #39)
    has never had one. That is the whole reason it is nullable rather than an empty string
    or a hash of something unguessable: those would be a password that exists and cannot be
    used, and every check would have to know the sentinel. `None` says the account has no
    password, which is a fact about it, and `authenticate` reads it as one.

    `email_verified` records whether anyone has ever proved this address belongs to its
    owner. It is deliberately not derived from anything: a provider asserting a verified
    address sets it, the flow in #38 sets it, and until one of those happens it stays
    false. Assuming it — for existing rows, or because a provider handed over an address at
    all — is the account-takeover route this column exists to close, since linking a
    provider identity to a local account on a matching address is only safe when both
    sides are verified.
    """

    username: str
    email: str
    hashed_password: str | None = None
    email_verified: bool = False
    id: UserId = field(default_factory=lambda: UserId(uuid4()))

    @property
    def has_password(self) -> bool:
        return self.hashed_password is not None
