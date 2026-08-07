from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4

from app.common.ids import IdentityId, UserId


class Provider(StrEnum):
    """The providers an account can be reached through.

    An enum rather than a free string, because `provider` is half of the unique key that
    decides which account a sign-in belongs to. "google" and "Google" would be two
    providers to the database and one to a reader, and the row that lost the argument would
    be a second account for the same person.

    StrEnum so the value stored and compared is the plain string, and adding the next
    provider stays a one-line change.
    """

    GOOGLE = "google"
    DISCORD = "discord"


@dataclass
class Identity:
    """One way into one account: a provider, and that provider's name for the person.

    `subject` is the provider's stable `sub` claim, and keying on it rather than on the
    email address is the whole point. A `sub` is permanent for the life of the provider
    account. An email address is not: addresses get reassigned, at company domains
    routinely, and joining on one means whoever receives the address next inherits the
    account it was attached to.

    Deliberately holds no profile — no display name, no avatar, no address. Those change at
    the provider and would be a stale copy the moment they did. This table answers exactly
    one question: which user is this sign-in?
    """

    user_id: UserId
    provider: Provider
    subject: str
    id: IdentityId = field(default_factory=lambda: IdentityId(uuid4()))
