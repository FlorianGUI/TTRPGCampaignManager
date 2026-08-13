from app.common.ids import ActId
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.narrative_access import ActAccess, Narrative
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.position import (
    POSITION_GAP,
    index_after,
    position_after,
    position_between,
    renumbered,
)


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
    ) -> None:
        # The child repositories are here for `delete`, which rehomes rather than
        # cascades — the same reason CampaignService holds what it sweeps.
        self._repository = repository
        self._sequences = sequences
        self._scenes = scenes

    async def create(self, access: ActAccess, title: str, description: str = "") -> Act:
        act = Act(
            title=title,
            campaign_id=access.campaign_id,
            position=position_after(await self._repository.last_position_in(access)),
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

    async def place(self, id: ActId, access: ActAccess, after: ActId | None = None) -> Act:
        """Reorder the campaign's acts.

        The simplest of the three, because an act has no parent to resolve: the campaign is
        its only possible one, so placing an act is entirely a question of where among its
        siblings it goes.
        """
        act = access.editable(await self._repository.find_by_id(id))

        siblings = [a for a in await self._repository.find_under(access) if a.id != act.id]
        index = index_after(siblings, after, access.not_available)

        position = position_between(
            siblings[index - 1].position if index > 0 else None,
            siblings[index].position if index < len(siblings) else None,
        )
        if position is not None:
            act.reposition(position)
            return await self._repository.save(act)

        ordered = siblings[:index] + [act] + siblings[index:]
        for record, fresh in zip(ordered, renumbered(len(ordered)), strict=True):
            record.reposition(fresh)
            await self._repository.save(record)
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
        next_sequence = position_after(await self._sequences.last_position_under(narrative.sequences, None))
        for sequence in await self._sequences.find_under(narrative.sequences, act.id):
            sequence.move_under(None, next_sequence)
            await self._sequences.save(sequence)
            next_sequence += POSITION_GAP

        next_scene = position_after(await self._scenes.last_position_under(narrative.scenes, None, None))
        for scene in await self._scenes.find_under(narrative.scenes, act.id, None):
            scene.move_under(None, None, next_scene)
            await self._scenes.save(scene)
            next_scene += POSITION_GAP

        await self._repository.delete(act.id)
