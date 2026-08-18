from app.common.ids import ActId
from app.contexts.campaign.application.siblings import SiblingGroups
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.narrative_access import ActAccess, Narrative
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.position import POSITION_GAP, position_after
from app.contexts.campaign.domain.sequence import Sequence
from app.contexts.campaign.domain.siblings import SiblingId, place_among


class ActService:
    """The top of the tree, and the simplest of the three services.

    An act is always a direct child of the campaign, so it has no parent to resolve and
    nothing to check beyond what the token already answered. That makes this the plainest
    repetition of PR 1's pattern — which is what #80 predicted PR 2 would mostly be.
    """

    def __init__(
        self,
        repository: ActRepository,
        sequences: SequenceRepository,
        scenes: SceneRepository,
        siblings: SiblingGroups,
    ) -> None:
        # The child repositories are here for `delete`, which rehomes rather than
        # cascades — the same reason CampaignService holds what it sweeps.
        self._repository = repository
        self._sequences = sequences
        self._scenes = scenes
        self._siblings = siblings

    async def create(self, narrative: Narrative, title: str, description: str = "") -> Act:
        """Appended to the campaign's children — all of them, not just the acts.

        The whole group, because a campaign may hold loose scenes and sequences beside its
        acts. Counting only from the last act is how a new act was handed a position a
        campaign-level scene already had, and #101 is what that looked like on screen.
        """
        act = Act(
            title=title,
            campaign_id=narrative.campaign_id,
            position=position_after(await self._siblings.last_position(narrative, None, None)),
            description=description,
        )
        return await self._repository.save(act)

    async def get_for(self, id: ActId, access: ActAccess) -> Act:
        return access.readable(await self._repository.find_by_id(id))

    async def list_for(self, access: ActAccess) -> list[Act]:
        return await self._repository.find_all_in(access)

    async def update(self, id: ActId, access: ActAccess, title: str, description: str = "") -> Act:
        act = access.editable(await self._repository.find_by_id(id))
        act.revise(title, description)
        return await self._repository.save(act)

    async def place(self, id: ActId, narrative: Narrative, after: SiblingId | None = None) -> Act:
        """Reorder the campaign's children, of which this act is one.

        Still the simplest of the three, because an act has no parent to resolve: the
        campaign is its only possible one, so this is entirely a question of where among
        its siblings it goes.

        Its siblings are not only the other acts. A campaign may hold scenes and sequences
        that skip the levels below, they are drawn in one list with the acts, and so an act
        can be dropped above or below one of them. `after` may name any of the three.
        """
        act = narrative.acts.editable(await self._repository.find_by_id(id))

        siblings = [s for s in await self._siblings.under(narrative, None, None) if s.id != act.id]
        placement = place_among(siblings, act, after)

        if placement.position is not None:
            act.reposition(placement.position)
            return await self._repository.save(act)

        await self._siblings.renumber(placement.ordered)
        return act

    async def delete(self, id: ActId, narrative: Narrative) -> None:
        """Remove the act, and give what was inside it to the campaign.

        **Rehome, not refuse, and never cascade.** #80 left this open and ruled out only
        cascading, as the one answer that loses an evening's prep. Refusing was the
        alternative: safe, never surprising, and it makes a game master empty an act by
        hand before they may remove it — twelve drags of busywork, plus a "move these
        first" flow in the UI that rehoming does not need.

        Rehoming is safe here for a reason particular to this tree: **the campaign is a
        real parent**, not a bin. #80's skippable levels mean a scene sitting directly on
        the campaign is as legitimate as one three levels down, so children land somewhere
        that already exists in the model and is already visible in the outline.

        The act's sequences and its direct scenes both go up one level, to the campaign.
        Scenes *inside* those sequences are untouched: their parent is the sequence, which
        survives — this is the nearest surviving ancestor, not a flattening.
        """
        act = narrative.acts.deletable(await self._repository.find_by_id(id))

        # Appended to whatever the campaign already holds, rather than keeping positions
        # that meant something only inside the act — two rehomed scenes numbered 1024 and
        # 2048 would interleave with the campaign's own by accident.
        #
        # **One counter for both kinds**, walking on from the end of the campaign's whole
        # group. Two counters were the same mistake as #101 in miniature: a rehomed
        # sequence and a rehomed scene were each given 1024, and arrived at the campaign
        # already tied with each other. They come out of the act in the order they were in
        # inside it, which is the order a game master last put them in.
        next_position = position_after(await self._siblings.last_position(narrative, None, None))

        for child in await self._siblings.beneath(narrative, act.id):
            if isinstance(child, Sequence):
                child.move_under(None, next_position)
            else:
                child.move_under(None, None, next_position)
            await self._siblings.save(child)
            next_position += POSITION_GAP

        await self._repository.delete(act.id)
