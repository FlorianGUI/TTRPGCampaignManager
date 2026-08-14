from app.common.ids import ActId, SequenceId
from app.contexts.campaign.application.siblings import SiblingGroups
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.position import POSITION_GAP, position_after
from app.contexts.campaign.domain.sequence import Sequence
from app.contexts.campaign.domain.siblings import SiblingId, place_among


class SequenceService:
    """The middle level, and the first thing in this context with a parent to resolve.

    Every method takes a `Narrative` rather than a `SequenceAccess`, because a sequence
    that names an act needs tokens for both levels and one reach check produced them all.
    Asking for the narrower token and then minting the other would be the second copy of
    the reach rule #80 spends a section forbidding.
    """

    def __init__(
        self,
        repository: SequenceRepository,
        acts: ActRepository,
        scenes: SceneRepository,
        siblings: SiblingGroups,
    ) -> None:
        self._repository = repository
        self._acts = acts
        # For `delete`, which hands the sequence's scenes to the act above it.
        self._scenes = scenes
        self._siblings = siblings

    async def _place_under(self, narrative: Narrative, act_id: ActId | None) -> ActId | None:
        """Resolve the parent, and prove it belongs to this campaign.

        **This is #80's sharp rule, and it needed no new code to enforce.** "A parent must
        belong to the same campaign" is the same question `ActAccess` already answers about
        every act — *is this row in the campaign I was reached through* — so resolving the
        id through the token is the check. An act belonging to another game master comes
        back as `Act not found`, indistinguishable from one that never existed.

        `None` is not a missing parent, it is the campaign, so it short-circuits: there is
        nothing to fetch and nothing to refuse.
        """
        if act_id is None:
            return None
        return narrative.acts.readable(await self._acts.find_by_id(act_id)).id

    async def create(
        self,
        narrative: Narrative,
        title: str,
        description: str = "",
        act_id: ActId | None = None,
    ) -> Sequence:
        parent = await self._place_under(narrative, act_id)
        sequence = Sequence(
            title=title,
            campaign_id=narrative.campaign_id,
            position=position_after(await self._siblings.last_position(narrative, parent, None)),
            description=description,
            act_id=parent,
        )
        return await self._repository.save(sequence)

    async def get_for(self, id: SequenceId, narrative: Narrative) -> Sequence:
        return narrative.sequences.readable(await self._repository.find_by_id(id))

    async def list_for(self, narrative: Narrative) -> list[Sequence]:
        return await self._repository.find_all_in(narrative.sequences)

    async def update(self, id: SequenceId, narrative: Narrative, title: str, description: str = "") -> Sequence:
        """Rewrites what the sequence says. Where it sits is `move` below.

        Split for the reason `Scene.revise` gives: an edit that also carried a parent would
        mean every rename sends one, and a stale value from a client that reorganised in
        another tab would silently move the sequence and everything under it.
        """
        sequence = narrative.sequences.editable(await self._repository.find_by_id(id))
        sequence.revise(title, description)
        return await self._repository.save(sequence)

    async def place(
        self, id: SequenceId, narrative: Narrative, act_id: ActId | None = None, after: SiblingId | None = None
    ) -> Sequence:
        """Put the sequence where it was dropped: an act, and a place among its siblings.

        The same shape as `SceneService.place` and for the same reasons — see it for why
        parent and position are one operation rather than two. Both the sequence and the
        act it is moving to are resolved through the same `Narrative`, so a game master
        cannot move their sequence under someone else's act, nor someone else's under
        their own, and neither refusal says which of the two was the problem.
        """
        sequence = narrative.sequences.editable(await self._repository.find_by_id(id))
        parent = await self._place_under(narrative, act_id)

        siblings = [s for s in await self._siblings.under(narrative, parent, None) if s.id != sequence.id]
        placement = place_among(siblings, sequence, after, narrative.sequences.not_available)

        if placement.position is not None:
            sequence.move_under(parent, placement.position)
            return await self._repository.save(sequence)

        sequence.move_under(parent, 0)
        await self._siblings.renumber(placement.ordered)
        return sequence

    async def delete(self, id: SequenceId, narrative: Narrative) -> None:
        """Remove the sequence, and give its scenes to the act above it.

        The same policy as an act, one level down, and this is where "nearest surviving
        ancestor" earns the phrase rather than just "the campaign": a sequence inside an
        act hands its scenes to **that act**, not to the campaign root. The act is still
        there and still the right place — sending its scenes past it would throw away a
        grouping the game master did not ask to lose.

        A sequence that was on the campaign has no act above it, so its scenes go to the
        campaign. That falls out of `sequence.act_id` being `None` rather than needing a
        branch, which is the same reason `None` is a parent everywhere else here.
        """
        sequence = narrative.sequences.deletable(await self._repository.find_by_id(id))

        next_position = position_after(await self._siblings.last_position(narrative, sequence.act_id, None))
        for scene in await self._scenes.find_under(narrative.scenes, None, sequence.id):
            scene.move_under(sequence.act_id, None, next_position)
            await self._scenes.save(scene)
            next_position += POSITION_GAP

        await self._repository.delete(sequence.id)
