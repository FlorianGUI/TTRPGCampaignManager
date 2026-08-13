from dataclasses import dataclass

from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.ports.sequence_repository import SequenceRepository
from app.contexts.campaign.domain.scene import SceneSummary
from app.contexts.campaign.domain.sequence import Sequence


@dataclass(frozen=True)
class Structure:
    """One campaign's tree, as three ordered lists rather than a nest.

    **Flat, with parentage, and that is a decision.** A nested response would have to
    invent a bucket for the sequences that hang off no act and another for the scenes that
    hang off nothing — the "No act" column #88's board model was rejected for. Here the
    levels being skippable needs no special case: a null parent is a null parent, and the
    client groups by it.

    It also keeps depth one natural. The sidebar lists the campaign's own children — acts
    and loose scenes together, in `position` order — and that is a filter and a sort over
    two of these lists rather than a merge of a tree with a leftovers bucket.

    Adding a fourth level later would add a list, not restructure the response.
    """

    acts: list[Act]
    sequences: list[Sequence]
    scenes: list[SceneSummary]


class StructureService:
    """The whole tree in one request — #80's "read model", built at last.

    #80 anticipated this and was careful about what it is not: *the act view reads the
    whole tree, but that is a query — a read model — not evidence that the write side
    wants an object graph.* Nothing here loads an aggregate or hands anything back that
    can be written to. Three reads, no rules of their own, and the token was checked once
    before any of them ran.

    The scenes come back as `SceneSummary`, so a campaign of two hundred scenes costs
    their titles rather than their prose. That is the single property this endpoint exists
    for; everything else it does could be had from the three list routes.
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

    async def of(self, narrative: Narrative) -> Structure:
        return Structure(
            acts=await self._acts.find_all_in(narrative.acts),
            sequences=await self._sequences.find_all_in(narrative.sequences),
            scenes=await self._scenes.find_summaries_in(narrative.scenes),
        )
