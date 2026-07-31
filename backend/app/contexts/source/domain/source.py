from dataclasses import dataclass, field
from typing import ClassVar
from uuid import uuid4

from app.common.access import Access
from app.common.errors import NotAvailable
from app.common.ids import SourceId, UserId


class SourceNotAvailable(NotAvailable):
    """No such source, or not one this game master owns — indistinguishable on purpose."""

    detail = "Source not found"


@dataclass
class Source:
    """Where material was gathered from: a book, a magazine issue, homemade notes.

    Data and nothing else, like `Campaign` and `Character`. The access rule is a
    relationship between a viewer and a record, so it lives on `SourceAccess`.
    """

    title: str
    owner_id: UserId
    id: SourceId = field(default_factory=lambda: SourceId(uuid4()))


@dataclass(frozen=True)
class SourceAccess(Access[Source]):
    """What a viewer may do with a source.

    Not a capability: anyone may build one, and it proves nothing by itself.

    There is no token below this one, because nothing hangs off a source — no
    `characters_at` equivalent, and nothing to reach *through* it. That flatness is the
    whole difference between this context and the campaign's.

    The three rules give the same answer today and are written out separately anyway.
    #31 asks whose library backs a shared campaign; if a member comes to read the owner's
    sources without owning them, `may_read` widens and the other two do not.
    """

    viewer_id: UserId

    not_available: ClassVar[type[NotAvailable]] = SourceNotAvailable

    def may_read(self, record: Source) -> bool:
        """`find_all_for` states this same rule in SQL, and a contract test holds them together."""
        return record.owner_id == self.viewer_id

    def may_edit(self, record: Source) -> bool:
        return record.owner_id == self.viewer_id

    def may_delete(self, record: Source) -> bool:
        return record.owner_id == self.viewer_id
