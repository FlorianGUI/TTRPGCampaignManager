from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar
from uuid import uuid4

from app.common.access import Access, Unsafe
from app.common.errors import NotAvailable
from app.common.ids import CampaignId, UserId
from app.contexts.campaign.domain.character_access import CharacterAccess


class CampaignNotReachable(NotAvailable):
    """A campaign that is not there, or not this viewer's to reach.

    One exception for both, so a caller holding a real id learns exactly as much as one
    guessing. It travels untouched to the HTTP boundary, where one handler turns it into
    the 404 that a campaign which never existed would also get.
    """

    detail = "Campaign not found"


@dataclass
class Campaign:
    """A game master's table: the thing play happens around.

    Data and nothing else. Who may see or change a campaign is not a property of the
    campaign, it is a relationship between a viewer and a record — so it lives on
    `CampaignAccess`, the object that models exactly that. `Character` has been shaped
    this way from the start; this is the entity catching up.
    """

    name: str
    owner_id: UserId
    description: str | None = None
    id: CampaignId = field(default_factory=lambda: CampaignId(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def revise(self, name: str, description: str | None) -> None:
        """Change what the campaign says, and record that it changed.

        A method rather than two assignments at the call site, and that is the whole
        reason it exists: `updated_at` is only true if nothing can edit a campaign
        without moving it. Written as `campaign.name = name` in a service, the timestamp
        is something the next service has to remember — and #80 adds three more entities
        for it to be forgotten in.
        """
        self.name = name
        self.description = description
        self.updated_at = datetime.now(UTC)


@dataclass(frozen=True)
class CampaignAccess(Access[Campaign]):
    """What a viewer may do with a campaign, and the door to what is inside it.

    Not a capability: anyone may build one around any viewer id, and it proves nothing on
    its own — the rule is checked against the record, not against the fact that you are
    holding this. `CharacterAccess` is the opposite, which is why only this class can
    hand one out.

    The three rules give the same answer today and are written out separately anyway,
    because #31 is expected to part them and nothing should have to be discovered when
    it does.
    """

    viewer_id: UserId

    not_available: ClassVar[type[NotAvailable]] = CampaignNotReachable

    def may_read(self, record: Campaign) -> bool:
        """#31: or the viewer is a member of this campaign.

        `find_all_for` states this same rule in SQL, because a list cannot afford to load
        rows it will discard. A contract test holds the two to the same answer.
        """
        return record.owner_id == self.viewer_id

    def may_edit(self, record: Campaign) -> bool:
        """#31: a co-GM may qualify; a player invited to play never should. Renaming a
        table out from under the game master running it is the thing to prevent."""
        return record.owner_id == self.viewer_id

    def may_delete(self, record: Campaign) -> bool:
        """Closing a table takes every sheet at it, so if these ever diverge this is the
        stricter one. #31: owner only, most likely, even where `may_edit` widens."""
        return record.owner_id == self.viewer_id

    def characters_at(self, campaign: Unsafe[Campaign]) -> CharacterAccess:
        """Hand out the right to work with the sheets at this table.

        The one door into everything inside a campaign, and the only thing anywhere that
        builds a `CharacterAccess`. Reaching the table is checked first and by the same
        method every other read goes through, so there is no second copy of the rule to
        drift. #52 and #29 add a sibling each.
        """
        return CharacterAccess(campaign_id=self.readable(campaign).id, viewer_id=self.viewer_id)
