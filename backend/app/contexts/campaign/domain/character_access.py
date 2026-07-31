from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from app.common.access import Access
from app.common.errors import NotAvailable
from app.contexts.campaign.domain.character import Character, CharacterNotAvailable


@dataclass(frozen=True)
class CharacterAccess(Access[Character]):
    """What a viewer may do with the sheets at one table.

    A capability, unlike the two root accesses: `Campaign.characters_for` is the only
    thing in the application that builds one, and it refuses unless the viewer can reach
    the campaign. So holding one of these is itself proof, and every repository method
    that touches a campaign's contents asks for one — there is no bare `campaign_id`
    parameter left anywhere to pass unchecked.

    Being exact about the strength of that: this is an ordinary dataclass, so nothing
    stops someone writing `CharacterAccess(...)` by hand. The bar worth clearing is that
    it cannot happen *by accident* — a hand-built token is a deliberate line that reads
    as strange in review, unlike a filter quietly left off a query.

    `may_read` is the rule that used to be a WHERE clause in `find_by_id_in`. Having it
    here rather than in SQL is what makes it something you can read, test, and change in
    one place — and it is why fetching a sheet by id no longer needs the repository to
    know anything about who is asking.

    #31 is where these three stop agreeing, and they are written out separately so that
    parting them is an edit rather than a discovery. All of it lands here and nowhere
    else — `find_all_in` is the one other place the rule is stated, because a list cannot
    afford to load what it will discard.
    """

    campaign_id: UUID
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
