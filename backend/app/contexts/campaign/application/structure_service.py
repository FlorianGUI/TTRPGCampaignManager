from dataclasses import dataclass

from app.contexts.campaign.application.act_service import ActService
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.application.sequence_service import SequenceService
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.placement import NarrativeKind, Placement
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
        act_service: ActService,
        sequence_service: SequenceService,
        scene_service: SceneService,
    ) -> None:
        self._acts = acts
        self._sequences = sequences
        self._scenes = scenes
        # The three services, because `place` is one gesture over a tree whose rules live
        # one level down. Nothing here reimplements them.
        self._act_service = act_service
        self._sequence_service = sequence_service
        self._scene_service = scene_service

    async def of(self, narrative: Narrative) -> Structure:
        return Structure(
            acts=await self._acts.find_all_in(narrative.acts),
            sequences=await self._sequences.find_all_in(narrative.sequences),
            scenes=await self._scenes.find_summaries_in(narrative.scenes),
        )

    async def place(self, narrative: Narrative, placement: Placement) -> Structure:
        """Move one row of the outline, and answer with the whole tree.

        **The rules are not here.** Each level already knows how to place its own kind —
        resolve the parent, find the sibling list, take the midpoint, renumber when the gap
        runs out — and all three were written and tested under #80. This dispatches on the
        kind the client sent and hands the work to whichever service owns it, so a fourth
        level would add a branch rather than a second copy of the algorithm.

        What it adds is the answer. The three per-level routes return the row they moved,
        which leaves the client to guess what happened to everything around it — and a
        renumber moves every sibling. Returning the tree makes the outline's next render
        the server's truth rather than an optimistic guess, which is the half of #111 that
        a status code alone cannot fix.

        `narrative` is threaded through rather than trusted from the body: every id below
        is resolved against this campaign's tokens, so an id belonging to another campaign
        is "not found" here exactly as it is on the routes this replaces.
        """
        match placement.item.kind:
            case NarrativeKind.ACT:
                await self._act_service.place(
                    placement.item.as_act(),
                    narrative.acts,
                    placement.after.as_act() if placement.after else None,
                )
            case NarrativeKind.SEQUENCE:
                await self._sequence_service.place(
                    placement.item.as_sequence(),
                    narrative,
                    placement.parent.as_act() if placement.parent else None,
                    placement.after.as_sequence() if placement.after else None,
                )
            case NarrativeKind.SCENE:
                parent = placement.parent
                await self._scene_service.place(
                    placement.item.as_scene(),
                    narrative,
                    parent.as_act() if parent and parent.kind is NarrativeKind.ACT else None,
                    parent.as_sequence() if parent and parent.kind is NarrativeKind.SEQUENCE else None,
                    placement.after.as_scene() if placement.after else None,
                )

        return await self.of(narrative)
