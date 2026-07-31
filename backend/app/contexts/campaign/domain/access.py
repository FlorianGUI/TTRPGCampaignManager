from dataclasses import dataclass
from uuid import UUID

from app.contexts.campaign.domain.character import Character


class CampaignNotReachable(Exception):
    """A viewer asked a campaign for access it cannot have.

    Raised by `Campaign.grant` rather than returned, because there is no useful token
    to hand back: the caller has nothing to do with a campaign it may not reach.
    """


@dataclass(frozen=True)
class CampaignAccess:
    """Proof that a viewer may reach a campaign, and the answer to what they may do there.

    `Campaign.grant` builds these and nothing else in the application does, while every
    repository method that touches something inside a campaign asks for one — so there
    is no bare `campaign_id` parameter left anywhere to pass unchecked. Skipping the
    authorisation stops being a thing you can forget and becomes a thing you cannot
    express, which is the trade #41 already made when it dropped the unscoped reads.

    Being exact about the strength of that: this is an ordinary dataclass, so nothing
    stops someone writing `CampaignAccess(...)` by hand. The bar worth clearing is that
    it cannot happen *by accident* — a hand-built token is a deliberate line that reads
    as strange in review, unlike a filter quietly left off a query.

    That matters more as the campaign grows: characters today, session notes (#52) and
    assets (#29) next. Each one is a new set of reads that would otherwise each have to
    remember to filter, and the filter is the same filter every time.

    What the answers are today is simple. A campaign is reachable only by its owner, so
    holding one of these means you are the game master and may do anything at your own
    table. The methods below exist so that #31 — which lets a game master invite players
    — has one place to become interesting, and they take the record rather than just the
    viewer because that is the shape the rule will need: "a player may edit their own
    sheet but not the one next to it" cannot be answered from the viewer alone.

    Call sites ask questions rather than reading a role or a set of grants off this
    object. #31 has not picked between those yet; keeping whatever it chooses on the
    inside means that decision lands in this file and touches nothing else.
    """

    campaign_id: UUID
    viewer_id: UUID

    def new_character(self, name: str, description: str | None = None) -> Character:
        """The only way to make a character: it is born at the table you proved you can reach.

        Going through the token is what keeps a sheet's owner and campaign honest — they
        are taken from the proof of access, never from a request body, so a caller cannot
        file a character at someone else's table or under someone else's name.

        #31: whether a subscriber may add a sheet at all is decided here.
        """
        return Character(
            name=name,
            owner_id=self.viewer_id,
            campaign_id=self.campaign_id,
            description=description,
        )

    def may_edit(self, character: Character) -> bool:
        """#31: co-GMs edit any sheet; a player only `character.owner_id == self.viewer_id`."""
        return True

    def may_delete(self, character: Character) -> bool:
        """#31: the same rule as editing, unless removing a sheet turns out to be stricter."""
        return True
