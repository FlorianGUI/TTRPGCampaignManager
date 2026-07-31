from dataclasses import dataclass
from typing import ClassVar, NewType
from uuid import UUID

from app.common.access import Access
from app.common.errors import NotAvailable
from app.contexts.campaign.domain.character import Character, CharacterNotAvailable

ReachedCampaign = NewType("ReachedCampaign", UUID)
"""A campaign id that a viewer has been shown to reach. The proof is the type itself.

`CampaignAccess.characters_at` mints these and nothing else does, so a value of this type
cannot exist unless the check ran. Note it has to be its own type rather than a merely
strongly-typed `CampaignId`: campaign ids arrive from path parameters and database rows
all day without anyone having been authorised, so the ordinary one proves nothing.

At runtime this is a plain UUID — `NewType` costs nothing and enforces nothing. The
enforcement is mypy, which this project gates in pre-commit and in CI. It cannot stop
someone determined, and is not meant to: writing `ReachedCampaign(some_id)` by hand is a
deliberate, greppable line. What it stops is the accident, which is the bar that matters.
"""


@dataclass(frozen=True)
class CharacterAccess(Access[Character]):
    """What a viewer may do with the sheets at one table.

    A capability, unlike the two root accesses: `CampaignAccess.characters_at` is the only
    thing that builds one, and it refuses unless the viewer can reach the campaign. So
    holding one is itself proof, and every repository method that touches a campaign's
    contents asks for one — there is no bare `campaign_id` parameter left anywhere to
    pass unchecked.

    The proof is carried by the type rather than by convention: `campaign_id` is a
    `ReachedCampaign`, minted only where the check happens. Constructing one of these
    around an ordinary campaign id does not typecheck, so the accident is closed. Writing
    `ReachedCampaign(some_id)` by hand still works, and is meant to — that is a
    deliberate, greppable line, which is the bar rather than a hole in it.

    `may_read` is the rule that used to be a WHERE clause in `find_by_id_in`. Having it
    here rather than in SQL is what makes it something you can read, test, and change in
    one place — and it is why fetching a sheet by id no longer needs the repository to
    know anything about who is asking. What guarantees these get *called* is the other
    half: a repository returns `Unsafe[Character]`, and there is no way to open one except
    through the three methods below.

    #31 is where these three stop agreeing, and they are written out separately so that
    parting them is an edit rather than a discovery. All of it lands here and nowhere
    else — `find_all_in` is the one other place the rule is stated, because a list cannot
    afford to load what it will discard.
    """

    campaign_id: ReachedCampaign
    viewer_id: UUID

    not_available: ClassVar[type[NotAvailable]] = CharacterNotAvailable

    def may_read(self, record: Character) -> bool:
        """#31: whether a player sees the sheets beside their own is undecided there."""
        return record.campaign_id == self.campaign_id

    def may_edit(self, record: Character) -> bool:
        """#31: a co-GM changes any sheet at the table; a player only their own, which is
        `record.owner_id == self.viewer_id`. That test goes here."""
        return record.campaign_id == self.campaign_id

    def may_delete(self, record: Character) -> bool:
        """#31: letting a player retire their own character is a different-sized thing to
        grant than letting them rewrite it, so this may not follow `may_edit`."""
        return record.campaign_id == self.campaign_id
