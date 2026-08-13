from app.common.ids import ActId, SceneId, SequenceId
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.position import position_after
from app.contexts.campaign.domain.scene import Scene, SceneStatus


class SceneService:
    """Scenes are reached through the campaign they belong to, never on their own.

    Every method takes a `Narrative`, so authorisation has already happened by the time
    any of them run — resolved once at the edge by the dependency that turns the campaign
    in the path into the tree's token. `readable`, `editable` and `deletable` hand back
    the record or raise, which is why there is barely a conditional below: this service
    never learns that a scene was missing or forbidden, only which one it was given.

    It holds the act and sequence repositories because a scene may name either as its
    parent, and a parent has to be resolved before it can be trusted. What it does *not*
    hold is a rule: see `_place_under`.
    """

    def __init__(
        self,
        repository: SceneRepository,
        acts: ActRepository,
        sequences: SequenceRepository,
    ) -> None:
        self._repository = repository
        self._acts = acts
        self._sequences = sequences

    async def _place_under(
        self, narrative: Narrative, act_id: ActId | None, sequence_id: SequenceId | None
    ) -> tuple[ActId | None, SequenceId | None]:
        """Resolve whichever parent was named, and prove it belongs to this campaign.

        **#80's sharp rule, enforced without a line of rule anywhere.** "A parent must
        belong to the same campaign" is the question the tokens already answer about every
        row — *is this in the campaign I was reached through* — so resolving the id through
        `narrative.acts` or `narrative.sequences` **is** the check. Another game master's
        act comes back as `Act not found`: the same answer as one that never existed, and
        the same answer the scene itself would give, so probing reveals nothing.

        Both `None` is the campaign — a real parent under #80's skippable levels, and the
        whole of a one-shot. Both set raises in the domain; the boundary rejects it with a
        422 long before, so this method need not decide between them.
        """
        if act_id is not None:
            return narrative.acts.readable(await self._acts.find_by_id(act_id)).id, None
        if sequence_id is not None:
            return None, narrative.sequences.readable(await self._sequences.find_by_id(sequence_id)).id
        return None, None

    async def create(
        self,
        narrative: Narrative,
        title: str,
        body: str = "",
        status: SceneStatus = SceneStatus.PLANNED,
        act_id: ActId | None = None,
        sequence_id: SequenceId | None = None,
    ) -> Scene:
        """A new scene goes at the end of whatever it hangs off.

        Two round trips rather than one, and worth naming: asking for the last position and
        then writing is not atomic, so two scenes created in the same instant can be handed
        the same position. The consequence is a cosmetic tie in a list, not a lost or
        misplaced row, and `find_all_in`'s second sort key keeps even that stable. A
        campaign is one game master's prep, so the race needs one person in two tabs in the
        same millisecond, and PR 3's reorder can move either one anyway.
        """
        act, sequence = await self._place_under(narrative, act_id, sequence_id)
        scene = Scene(
            title=title,
            campaign_id=narrative.campaign_id,
            position=position_after(await self._repository.last_position_under(narrative.scenes, act, sequence)),
            body=body,
            status=status,
            act_id=act,
            sequence_id=sequence,
        )
        return await self._repository.save(scene)

    async def get_for(self, id: SceneId, narrative: Narrative) -> Scene:
        return narrative.scenes.readable(await self._repository.find_by_id(id))

    async def list_for(self, narrative: Narrative) -> list[Scene]:
        # No token method here: the filtering is the query's, not a per-record decision,
        # and so is the ordering. See the port for why.
        return await self._repository.find_all_in(narrative.scenes)

    async def update(
        self,
        id: SceneId,
        narrative: Narrative,
        title: str,
        body: str,
        status: SceneStatus,
    ) -> Scene:
        """Rewrites what the scene says. Where it sits is `move` below."""
        scene = narrative.scenes.editable(await self._repository.find_by_id(id))
        scene.revise(title, body, status)
        return await self._repository.save(scene)

    async def move(
        self,
        id: SceneId,
        narrative: Narrative,
        act_id: ActId | None = None,
        sequence_id: SequenceId | None = None,
    ) -> Scene:
        """Reparent, appending to the new parent's scenes.

        The operation #80 exists for — *scenes move between acts, get cut and come back* —
        and the one where getting the rule wrong would let a game master file a scene in a
        campaign that is not theirs. Both the scene and its new parent are resolved through
        the same `Narrative`, so that cannot happen, and neither refusal says which of the
        two was the problem.

        Moving to the campaign is `act_id=None, sequence_id=None`, which is not "no parent
        given" but a parent in its own right — a scene demoted out of an act is a scene of
        the campaign, exactly as if it had been written there.
        """
        scene = narrative.scenes.editable(await self._repository.find_by_id(id))
        act, sequence = await self._place_under(narrative, act_id, sequence_id)
        scene.move_under(
            act,
            sequence,
            position_after(await self._repository.last_position_under(narrative.scenes, act, sequence)),
        )
        return await self._repository.save(scene)

    async def delete(self, id: SceneId, narrative: Narrative) -> None:
        scene = narrative.scenes.deletable(await self._repository.find_by_id(id))
        await self._repository.delete(scene.id)
