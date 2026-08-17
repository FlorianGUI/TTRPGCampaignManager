from app.common.ids import ActId, SequenceId
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.position import renumbered
from app.contexts.campaign.domain.scene import Scene
from app.contexts.campaign.domain.sequence import Sequence
from app.contexts.campaign.domain.siblings import Sibling, in_narrative_order


class SiblingGroups:
    """Loads one parent's children out of the three tables, and writes them back.

    The database half of `domain/siblings.py`. A sibling group is everything under one
    parent whatever kind it is, and no single repository can answer that — which is
    exactly why #101 happened: each one counted its own table and nobody owned the
    question. This owns it, once, for all three services.

    It holds all three repositories, which reads like a lot until you notice it is the
    same three `StructureService` holds for the same reason: a question about the tree
    rather than about one level of it.
    """

    def __init__(
        self,
        acts: ActRepository,
        sequences: SequenceRepository,
        scenes: SceneRepository,
    ) -> None:
        self._acts = acts
        self._sequences = sequences
        self._scenes = scenes

    async def beneath(self, narrative: Narrative, act_id: ActId | None) -> list[Sequence | Scene]:
        """What an act — or the campaign — holds directly, minus any acts.

        Narrower than `under` on purpose. Rehoming walks this, and every member of it has
        a parent that can be reassigned, which an act does not: an act belongs to the
        campaign and to nothing else. Saying so in the type means the two-way dispatch in
        `ActService.delete` is exhaustive rather than carrying a third branch that can
        never run and could never be covered.
        """
        members: list[Sequence | Scene] = []
        members.extend(await self._sequences.find_under(narrative.sequences, act_id))
        members.extend(await self._scenes.find_under(narrative.scenes, act_id, None))

        return in_narrative_order(members)

    async def under(self, narrative: Narrative, act_id: ActId | None, sequence_id: SequenceId | None) -> list[Sibling]:
        """One parent's children, every kind, in narrative order.

        The parent is named the way the records themselves name it — the pair of nullable
        ids that a scene carries — so there is no third vocabulary for "which parent" to
        keep in step with the two that exist.

        A sequence holds only scenes, so that branch asks one table. Below it, the
        campaign and an act differ only in whether acts are among the children: an act may
        only ever be the campaign's, while sequences and scenes hang off whichever parent
        they name, including none.
        """
        if sequence_id is not None:
            return in_narrative_order(await self._scenes.find_under(narrative.scenes, None, sequence_id))

        members: list[Sibling] = list(await self.beneath(narrative, act_id))
        if act_id is None:
            members.extend(await self._acts.find_under(narrative.acts))

        return in_narrative_order(members)

    async def last_position(
        self, narrative: Narrative, act_id: ActId | None, sequence_id: SequenceId | None
    ) -> int | None:
        """The end of the group, for appending to it.

        Three cheap queries and a `max`, not a load of the group. The point of the sparse
        scheme is that placing a record is arithmetic, and appending still needs exactly
        one number — it is just that the number now has to come from every table the group
        draws on, or a scene appended to an act starts where one of its sequences already
        is. Which was #101.
        """
        if sequence_id is not None:
            return await self._scenes.last_position_under(narrative.scenes, None, sequence_id)

        ends = [
            await self._sequences.last_position_under(narrative.sequences, act_id),
            await self._scenes.last_position_under(narrative.scenes, act_id, None),
        ]
        if act_id is None:
            ends.append(await self._acts.last_position_in(narrative.acts))

        known = [end for end in ends if end is not None]
        return max(known) if known else None

    async def save(self, record: Sibling) -> None:
        """Write one member back, to whichever table it came from.

        Dispatch on the type rather than a `kind` passed alongside it: the record already
        knows what it is, and a parameter saying so again is a parameter that can disagree
        with it.
        """
        if isinstance(record, Act):
            await self._acts.save(record)
        elif isinstance(record, Sequence):
            await self._sequences.save(record)
        else:
            await self._scenes.save(record)

    async def renumber(self, ordered: list[Sibling]) -> None:
        """Space a whole group out again, across whatever tables it spans.

        The escape hatch the sparse scheme trades against, and now the one place it
        happens. It stays scoped to a single group — renumbering an act's children must
        not touch another act's, which is #80's "reordering a sibling does not touch
        unrelated rows" from the other side — but the group is a real group now, so a
        renumber that used to leave a neighbouring sequence on its own number line no
        longer can.
        """
        for record, fresh in zip(ordered, renumbered(len(ordered)), strict=True):
            record.reposition(fresh)
            await self.save(record)
