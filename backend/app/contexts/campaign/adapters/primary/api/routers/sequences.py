from fastapi import APIRouter, Depends

from app.common.error_handlers import not_available_responses
from app.common.ids import ActId, SequenceId
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.dependencies import get_narrative, get_sequence_service
from app.contexts.campaign.adapters.primary.api.schemas.sequence import (
    SequenceCreate,
    SequenceResponse,
    SequenceUpdate,
)
from app.contexts.campaign.application.sequence_service import SequenceService
from app.contexts.campaign.domain.narrative_access import Narrative

# A sequence names an act, so this router can answer for three things rather than two: the
# campaign, the sequence, and the act it was told to sit under. All three answer 404 in
# the same words they would if they had never existed.
NO_CAMPAIGN = not_available_responses("Campaign not found", "Act not found")
NOT_FOUND = not_available_responses("Campaign not found", "Sequence not found", "Act not found")

router = APIRouter(
    prefix="/campaigns/{campaign_id}/sequences",
    tags=["sequences"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=SequenceResponse, status_code=201, responses=NO_CAMPAIGN)
async def create_sequence(
    body: SequenceCreate,
    narrative: Narrative = Depends(get_narrative),
    service: SequenceService = Depends(get_sequence_service),
):
    sequence = await service.create(
        narrative, body.title, body.description, ActId(body.act_id) if body.act_id else None
    )
    return SequenceResponse(**sequence.__dict__)


@router.get("/", response_model=list[SequenceResponse], responses=NO_CAMPAIGN)
async def list_sequences(
    narrative: Narrative = Depends(get_narrative),
    service: SequenceService = Depends(get_sequence_service),
):
    return [SequenceResponse(**s.__dict__) for s in await service.list_for(narrative)]


@router.get("/{sequence_id}", response_model=SequenceResponse, responses=NOT_FOUND)
async def get_sequence(
    sequence_id: SequenceId,
    narrative: Narrative = Depends(get_narrative),
    service: SequenceService = Depends(get_sequence_service),
):
    sequence = await service.get_for(sequence_id, narrative)
    return SequenceResponse(**sequence.__dict__)


@router.put("/{sequence_id}", response_model=SequenceResponse, responses=NOT_FOUND)
async def update_sequence(
    sequence_id: SequenceId,
    body: SequenceUpdate,
    narrative: Narrative = Depends(get_narrative),
    service: SequenceService = Depends(get_sequence_service),
):
    sequence = await service.update(sequence_id, narrative, body.title, body.description)
    return SequenceResponse(**sequence.__dict__)


@router.delete("/{sequence_id}", status_code=204, responses=NOT_FOUND)
async def delete_sequence(
    sequence_id: SequenceId,
    narrative: Narrative = Depends(get_narrative),
    service: SequenceService = Depends(get_sequence_service),
):
    await service.delete(sequence_id, narrative)
