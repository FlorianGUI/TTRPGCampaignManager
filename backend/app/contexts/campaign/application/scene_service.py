from app.common.ids import ActId, SceneId, SequenceId
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.position import index_after, position_after, position_between, renumbered
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

    async def place(
        self,
        id: SceneId,
        narrative: Narrative,
        act_id: ActId | None = None,
        sequence_id: SequenceId | None = None,
        after: SceneId | None = None,
    ) -> Scene:
        """Put the scene where the game master dropped it: a parent, and a place in it.

        **One operation rather than two**, and that is the point. A drag can cross acts and
        land mid-list in a single gesture, and splitting that into "reparent" then "reorder"
        would make it two requests, non-atomic, with a visible wrong order in between if the
        second failed.

        `after` names the sibling it was dropped below; `None` means first. It has to be a
        sibling *under the new parent* — anything else is refused as `Scene not found`,
        which covers an anchor from another campaign, another act, and one that never
        existed, without saying which.

        The scene appends when `after` names the last sibling, so PR 2's "move to the end"
        is this method with the obvious argument rather than a second code path.
        """
        scene = narrative.scenes.editable(await self._repository.find_by_id(id))
        act, sequence = await self._place_under(narrative, act_id, sequence_id)

        # The scene's current row is excluded: it is being placed, so it is not one of the
        # neighbours it is being placed between. Leaving it in would let a scene be dropped
        # "after itself" and compute a midpoint against its own position.
        siblings = [s for s in await self._repository.find_under(narrative.scenes, act, sequence) if s.id != scene.id]
        index = index_after(siblings, after, narrative.scenes.not_available)

        position = position_between(
            siblings[index - 1].position if index > 0 else None,
            siblings[index].position if index < len(siblings) else None,
        )
        if position is not None:
            scene.move_under(act, sequence, position)
            return await self._repository.save(scene)

        # No integer left between those two neighbours. Renumber this sibling list — and
        # only this one, which is #80's "reordering a sibling does not touch unrelated
        # rows" from the other side.
        scene.move_under(act, sequence, 0)
        ordered = siblings[:index] + [scene] + siblings[index:]
        for record, fresh in zip(ordered, renumbered(len(ordered)), strict=True):
            record.reposition(fresh)
            await self._repository.save(record)
        return scene

    async def delete(self, id: SceneId, narrative: Narrative) -> None:
        scene = narrative.scenes.deletable(await self._repository.find_by_id(id))
        await self._repository.delete(scene.id)
