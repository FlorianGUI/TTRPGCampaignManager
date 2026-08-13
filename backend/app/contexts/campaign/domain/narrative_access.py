from dataclasses import dataclass
from typing import ClassVar, Protocol

from app.common.access import Access
from app.common.errors import NotAvailable
from app.common.ids import CampaignId, UserId
from app.contexts.campaign.domain.act import Act, ActNotAvailable
from app.contexts.campaign.domain.scene import Scene, SceneNotAvailable
from app.contexts.campaign.domain.sequence import Sequence, SequenceNotAvailable


class InCampaign(Protocol):
    """Anything in the narrative tree: it belongs to exactly one campaign.

    That single attribute is the entire surface the tree's rule needs, which is the
    point — acts, sequences and scenes differ in everything except the one thing being
    asked about, so the rule below can be written once against this and inherited by all
    three rather than restated per level.
    """

    campaign_id: CampaignId


@dataclass(frozen=True)
class NarrativeAccess[T: InCampaign](Access[T]):
    """What a viewer may do with one campaign's prep. One rule, for the whole tree.

    A capability, like `CharacterAccess` and unlike the two root accesses:
    `CampaignAccess.narrative_at` is the only thing that builds one and it refuses anyone
    who cannot reach the campaign, so holding one is itself proof.

    **Authorisation here is the campaign's and does not fork** (#80). If you may read the
    campaign you may read its scenes; if you may edit it you may edit them. There is no
    narrative-specific rule, now or under #31 — which is why the three methods below all
    ask the same small question and none of them mentions a viewer at all.

    Why this is generic rather than three classes with three copies of that question:
    PR 2 adds `Act` and `Sequence` above `Scene`, and the only thing that differs between
    the levels is which 404 they answer with. Subclassing to set `not_available` and
    nothing else keeps the rule in one place, and a subclass that overrode a rule would
    be visible as exactly the fork this issue rules out.

    **The reach rule is not restated here at all**, and that is the part that matters for
    #31. Whether a viewer may get at a campaign is asked once, in `CampaignAccess`, by
    `narrative_at` calling `self.readable(campaign)` — so widening it under #31 is one
    edit in one file and the whole tree follows, however many levels it has grown by then.
    What is left below is the only per-record question there is: *does this row belong to
    the campaign I was reached through*, which is the shape `CharacterAccess.may_read`
    already has.

    Characters are the exception and the reason is worth remembering when this is next
    read: a sheet has an owner who is not the game master, so #31 parts its three rules
    per person. Narrative is the game master's own prep — a scene has no owner distinct
    from the campaign, so there is no per-row question to ask about it. If a scene ever
    needs hiding from players until it has been played, that is a visibility field on the
    row and its own issue, not a second rule here.
    """

    campaign_id: CampaignId
    viewer_id: UserId

    def may_read(self, record: T) -> bool:
        return record.campaign_id == self.campaign_id

    def may_edit(self, record: T) -> bool:
        return record.campaign_id == self.campaign_id

    def may_delete(self, record: T) -> bool:
        return record.campaign_id == self.campaign_id


@dataclass(frozen=True)
class ActAccess(NarrativeAccess[Act]):
    """The tree's rule, answering as an act."""

    not_available: ClassVar[type[NotAvailable]] = ActNotAvailable


@dataclass(frozen=True)
class SequenceAccess(NarrativeAccess[Sequence]):
    """The tree's rule, answering as a sequence."""

    not_available: ClassVar[type[NotAvailable]] = SequenceNotAvailable


@dataclass(frozen=True)
class SceneAccess(NarrativeAccess[Scene]):
    """The tree's rule, answering as a scene.

    None of these three carries a rule of its own — only which 404 a refusal becomes, so
    that a missing scene and a scene in someone else's campaign are told apart from a
    missing act by their wording and from each other by nothing at all. A subclass here
    that overrode `may_read` would be visible as exactly the fork #80 rules out.
    """

    not_available: ClassVar[type[NotAvailable]] = SceneNotAvailable


@dataclass(frozen=True)
class Narrative:
    """One campaign's prep, and the right to work with all of it.

    This is #80's "one access token for the whole tree" as an object. `CampaignAccess`
    checks the reach **once** and hands this back; the three properties below are the same
    campaign and the same viewer wearing three 404s. Nothing here asks a question — every
    one of them was already answered on the line that built this.

    Why one object rather than three minting methods on `CampaignAccess`: the reach check
    is the thing that must not be repeated, and three methods would be three call sites
    that each have to remember to do it. Here it is structurally impossible to obtain a
    token for one level without having passed the check for all of them.

    Reparenting is what makes the three-in-one earn its keep rather than merely tidy.
    Moving a scene under an act needs the scene's token *and* the act's, and #80 calls
    that "the sharp one, since it is the difference between reparenting a scene and moving
    it under another game master's act". Holding both from one check is what makes that
    check a single `readable` call on the parent rather than a rule anybody had to write.
    """

    campaign_id: CampaignId
    viewer_id: UserId

    @property
    def acts(self) -> ActAccess:
        return ActAccess(campaign_id=self.campaign_id, viewer_id=self.viewer_id)

    @property
    def sequences(self) -> SequenceAccess:
        return SequenceAccess(campaign_id=self.campaign_id, viewer_id=self.viewer_id)

    @property
    def scenes(self) -> SceneAccess:
        return SceneAccess(campaign_id=self.campaign_id, viewer_id=self.viewer_id)
