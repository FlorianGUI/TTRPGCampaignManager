from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.common.errors import NotAvailable
from app.common.ids import ActId, CampaignId


class ActNotAvailable(NotAvailable):
    """No such act in this campaign, or not one this viewer may touch."""

    detail = "Act not found"


@dataclass
class Act:
    """The major division of a campaign — "Act II: the war".

    Grouping and nothing else: the content is in the scenes. An act carries a title and a
    description, and the description is markdown of the same dialect a scene body is —
    `str` here, `CampaignMarkdown` at the boundary, and unread by anything in between.

    Always a direct child of the campaign. It is the top of the tree, so unlike a sequence
    or a scene it has no parentage to be nullable: #80's skippable levels are about what
    may be *left out* below an act, never about an act belonging to something else.
    """

    title: str
    campaign_id: CampaignId
    position: int
    description: str = ""
    id: ActId = field(default_factory=lambda: ActId(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def revise(self, title: str, description: str) -> None:
        """The fourth entity to carry this shape, and it still earns its place.

        `updated_at` is only true if nothing can edit a record without moving it — see
        `Campaign.revise` for the argument, which #78 made when there were three of these
        and predicted this PR would add two more.
        """
        self.title = title
        self.description = description
        self.updated_at = datetime.now(UTC)

    def reposition(self, position: int) -> None:
        """Take a new number in the same list, without claiming to have been edited.

        `updated_at` deliberately does not move. This is what a **neighbour** gets when
        someone else's drop exhausted the gap and the sibling list had to be renumbered —
        the record itself did not change, its surroundings did. Moving the timestamp on
        thirty rows because one scene was dragged past another would make "last changed"
        mean "was near something that moved", and every list ordered by it useless.

        The record being moved goes through `move_under` instead, which does move it.
        """
        self.position = position
