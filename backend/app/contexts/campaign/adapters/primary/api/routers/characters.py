from uuid import UUID

from fastapi import APIRouter, Depends

from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.dependencies import get_campaign_access, get_character_service
from app.contexts.campaign.adapters.primary.api.schemas.character import (
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
)
from app.contexts.campaign.application.character_service import CharacterService
from app.contexts.campaign.domain.access import CampaignAccess

# Characters are reached through their campaign, never on their own. Every route below
# asks for a CampaignAccess rather than a campaign id, so the table in the path is
# authorised before the handler body runs — and a handler that forgot to ask would have
# no token, and so nothing it could do with the repository.
#
# Whether the table or the sheet was the thing the caller could not have is answered by
# which exception comes back, not by anything decided here.
router = APIRouter(
    prefix="/campaigns/{campaign_id}/characters",
    tags=["characters"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=CharacterResponse, status_code=201)
async def create_character(
    body: CharacterCreate,
    access: CampaignAccess = Depends(get_campaign_access),
    service: CharacterService = Depends(get_character_service),
):
    character = await service.create(access, body.name, body.description)
    return CharacterResponse(**character.__dict__)


@router.get("/", response_model=list[CharacterResponse])
async def list_characters(
    access: CampaignAccess = Depends(get_campaign_access),
    service: CharacterService = Depends(get_character_service),
):
    return [CharacterResponse(**c.__dict__) for c in await service.list_for(access)]


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: UUID,
    access: CampaignAccess = Depends(get_campaign_access),
    service: CharacterService = Depends(get_character_service),
):
    character = await service.get_for(character_id, access)
    return CharacterResponse(**character.__dict__)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: UUID,
    body: CharacterUpdate,
    access: CampaignAccess = Depends(get_campaign_access),
    service: CharacterService = Depends(get_character_service),
):
    character = await service.update(character_id, access, body.name, body.description)
    return CharacterResponse(**character.__dict__)


@router.delete("/{character_id}", status_code=204)
async def delete_character(
    character_id: UUID,
    access: CampaignAccess = Depends(get_campaign_access),
    service: CharacterService = Depends(get_character_service),
):
    await service.delete(character_id, access)
