from dataclasses import dataclass, field
from uuid import UUID, uuid4

from app.contexts.campaign.domain.access import CampaignAccess, CampaignNotReachable


@dataclass
class Campaign:
    """A game master's table: the thing play happens around.

    A campaign has exactly one owner. Inviting other users to it is real and planned
    but lands in #31 through a membership table, so ownership is the whole of the
    access story for now.

    It is also the access boundary for everything that hangs off it: reaching a
    character, and later a session note (#52) or an asset (#29), means asking the
    campaign for a `CampaignAccess` first. The rules below are the single statement of
    who may do what — the repository queries mirror them, and a contract test holds the
    two together.
    """

    name: str
    owner_id: UUID
    description: str | None = None
    id: UUID = field(default_factory=uuid4)

    def is_visible_to(self, viewer_id: UUID) -> bool:
        """#31: or the viewer is a member of this campaign."""
        return self.owner_id == viewer_id

    def is_editable_by(self, viewer_id: UUID) -> bool:
        """Renaming or deleting the table itself stays with the game master who runs it.

        #31: a co-GM may well qualify, but a player invited to play never should.
        """
        return self.owner_id == viewer_id

    def grant(self, viewer_id: UUID) -> CampaignAccess:
        """Hand out proof that this viewer may reach this table.

        The one door into everything inside the campaign. Anything that wants to read or
        write a character has to come through here first, which is what makes the check
        impossible to route around rather than merely rude to skip.
        """
        if not self.is_visible_to(viewer_id):
            raise CampaignNotReachable
        return CampaignAccess(campaign_id=self.id, viewer_id=viewer_id)
