from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.common.errors import NotAvailable
from app.common.ids import ActId, CampaignId, SequenceId


class SequenceNotAvailable(NotAvailable):
    """No such sequence in this campaign, or not one this viewer may touch."""

    detail = "Sequence not found"


@dataclass
class Sequence:
    """A run of scenes with a shape of its own — "Getting the dwarves to commit".

    The screenwriting term for exactly this level, chosen over `Chapter` for precision and
    over `Arc` deliberately: game masters use "arc" for threads that run *alongside* each
    other, which a strict tree cannot express, so naming a level `Arc` would invite people
    to model overlapping arcs in it and be quietly wrong. That word is reserved.

    It is jargon, and #80 says so — a game master who has not studied screenwriting will
    not arrive already using it, so the UI has to teach it once. Nothing here can do that;
    it is #88's empty state and its detail page.

    `act_id` is nullable because the levels are skippable: a sequence may sit under an act
    or directly under the campaign. What it may never sit under is another sequence, and
    that is structural rather than checked — there is no `sequence_id` column here to set.
    """

    title: str
    campaign_id: CampaignId
    position: int
    description: str = ""
    act_id: ActId | None = None
    id: SequenceId = field(default_factory=lambda: SequenceId(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def revise(self, title: str, description: str) -> None:
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

    def move_under(self, act_id: ActId | None, position: int) -> None:
        """Reparent, and take a place among its new siblings.

        Parent and position move together and cannot be set apart, because they are one
        fact: a position means nothing except among the children of one parent, and a
        record that changed parent while keeping its old number would land at an arbitrary
        point in the new list.

        That the act belongs to this campaign is not checked here and must not be. It is
        `ActAccess`'s question, asked by whoever resolved the id — see `NarrativeAccess`
        for why the tree has exactly one rule and this is not a second copy of it.
        """
        self.act_id = act_id
        self.position = position
        self.updated_at = datetime.now(UTC)
