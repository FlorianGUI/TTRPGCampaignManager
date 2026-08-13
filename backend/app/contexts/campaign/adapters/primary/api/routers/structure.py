from fastapi import APIRouter, Depends

from app.common.error_handlers import not_available_responses
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.dependencies import get_narrative, get_structure_service
from app.contexts.campaign.adapters.primary.api.schemas.structure import (
    StructureAct,
    StructureResponse,
    StructureScene,
    StructureSequence,
)
from app.contexts.campaign.application.structure_service import StructureService
from app.contexts.campaign.domain.narrative_access import Narrative

# The one read beyond the per-entity routes, and the only one #88 asks for. Campaign-gated
# like everything else in this context: an unreachable campaign answers "Campaign not
# found" before any of the three queries runs.
NO_CAMPAIGN = not_available_responses("Campaign not found")

router = APIRouter(
    prefix="/campaigns/{campaign_id}/structure",
    tags=["structure"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/", response_model=StructureResponse, responses=NO_CAMPAIGN)
async def get_structure(
    narrative: Narrative = Depends(get_narrative),
    service: StructureService = Depends(get_structure_service),
):
    """The whole tree, ordered, without scene bodies.

    Every campaign route in #88 reads this — the sidebar names the campaign's own children
    wherever you are — so it is worth caching in a store rather than fetching per page. A
    thin `GET .../acts` would have been the alternative and is deliberately not offered:
    two endpoints returning subsets of the same tree are two things to keep ordered
    identically.
    """
    structure = await service.of(narrative)
    return StructureResponse(
        acts=[StructureAct(**a.__dict__) for a in structure.acts],
        sequences=[StructureSequence(**s.__dict__) for s in structure.sequences],
        scenes=[StructureScene(**s.__dict__) for s in structure.scenes],
    )
