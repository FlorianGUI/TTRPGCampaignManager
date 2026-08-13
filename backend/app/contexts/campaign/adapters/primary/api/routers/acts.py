from fastapi import APIRouter, Depends

from app.common.error_handlers import not_available_responses
from app.common.ids import ActId
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.dependencies import get_act_service, get_narrative
from app.contexts.campaign.adapters.primary.api.schemas.act import (
    ActCreate,
    ActPlacement,
    ActResponse,
    ActUpdate,
)
from app.contexts.campaign.application.act_service import ActService
from app.contexts.campaign.domain.narrative_access import Narrative

# Nested and campaign-gated, as #43 established and #80 repeats. Every route asks for the
# tree's token rather than a campaign id, so the campaign is authorised before any handler
# body runs and an unreachable one answers "Campaign not found" before anything inside it
# is looked at.
NO_CAMPAIGN = not_available_responses("Campaign not found")
NOT_FOUND = not_available_responses("Campaign not found", "Act not found")

router = APIRouter(
    prefix="/campaigns/{campaign_id}/acts",
    tags=["acts"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=ActResponse, status_code=201, responses=NO_CAMPAIGN)
async def create_act(
    body: ActCreate,
    narrative: Narrative = Depends(get_narrative),
    service: ActService = Depends(get_act_service),
):
    act = await service.create(narrative.acts, body.title, body.description)
    return ActResponse(**act.__dict__)


@router.get("/", response_model=list[ActResponse], responses=NO_CAMPAIGN)
async def list_acts(
    narrative: Narrative = Depends(get_narrative),
    service: ActService = Depends(get_act_service),
):
    return [ActResponse(**a.__dict__) for a in await service.list_for(narrative.acts)]


@router.get("/{act_id}", response_model=ActResponse, responses=NOT_FOUND)
async def get_act(
    act_id: ActId,
    narrative: Narrative = Depends(get_narrative),
    service: ActService = Depends(get_act_service),
):
    act = await service.get_for(act_id, narrative.acts)
    return ActResponse(**act.__dict__)


@router.put("/{act_id}", response_model=ActResponse, responses=NOT_FOUND)
async def update_act(
    act_id: ActId,
    body: ActUpdate,
    narrative: Narrative = Depends(get_narrative),
    service: ActService = Depends(get_act_service),
):
    act = await service.update(act_id, narrative.acts, body.title, body.description)
    return ActResponse(**act.__dict__)


@router.put("/{act_id}/placement", response_model=ActResponse, responses=NOT_FOUND)
async def place_act(
    act_id: ActId,
    body: ActPlacement,
    narrative: Narrative = Depends(get_narrative),
    service: ActService = Depends(get_act_service),
):
    """Reorder the campaign's acts. One row written, unless the gap has run out."""
    act = await service.place(act_id, narrative.acts, ActId(body.after) if body.after else None)
    return ActResponse(**act.__dict__)


@router.delete("/{act_id}", status_code=204, responses=NOT_FOUND)
async def delete_act(
    act_id: ActId,
    narrative: Narrative = Depends(get_narrative),
    service: ActService = Depends(get_act_service),
):
    # A non-empty act rehomes rather than refusing: its sequences and direct scenes go
    # to the campaign, which is a real parent under skippable levels rather than a bin.
    # Scenes inside its sequences are untouched — the sequence survives and takes them.
    await service.delete(act_id, narrative)
