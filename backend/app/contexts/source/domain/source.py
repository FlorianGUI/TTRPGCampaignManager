from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.common.errors import NotAvailable


class SourceNotAvailable(NotAvailable):
    """No such source, or not one this game master owns — indistinguishable on purpose."""

    detail = "Source not found"


@dataclass
class Source:
    """Where material was gathered from: a book, a magazine issue, homemade notes.

    A source belongs to the game master who added it; what they browse is simply the
    set of sources they own, so there is nothing above this entity to model.

    That flatness is why there is no access token here as there is for a campaign: with
    nothing hanging off a source, there is nothing to reach *through* it, and the rules
    below are the whole story. What #31 does to a shared campaign's library is an open
    question on that issue, and this is where the answer would go.
    """

    title: str
    owner_id: UUID
    id: UUID = field(default_factory=uuid4)

    def is_visible_to(self, viewer_id: UUID) -> bool:
        return self.owner_id == viewer_id

    def is_editable_by(self, viewer_id: UUID) -> bool:
        return self.owner_id == viewer_id
