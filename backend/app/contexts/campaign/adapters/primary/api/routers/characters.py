from fastapi import APIRouter, Depends

from app.common.error_handlers import not_available_responses
from app.common.ids import CharacterId
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.dependencies import get_character_access, get_character_service
from app.contexts.campaign.adapters.primary.api.schemas.character import (
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
)
from app.contexts.campaign.application.character_service import CharacterService
from app.contexts.campaign.domain.character_access import CharacterAccess

# Characters are reached through their campaign, never on their own. Every route below
# asks for a CharacterAccess rather than a campaign id, so the table in the path is
# authorised before the handler body runs — and a handler that forgot to ask would have
# no token, and so nothing it could do with the repository.
#
# Whether the table or the sheet was the thing the caller could not have is answered by
# which exception comes back, not by anything decided here.
# Every route here can answer for the table as well as for the sheet: the campaign is
# authorised by a dependency, which raises before any handler body runs.
NO_CAMPAIGN = not_available_responses("Campaign not found")
NOT_FOUND = not_available_responses("Campaign not found", "Character not found")

router = APIRouter(
    prefix="/campaigns/{campaign_id}/characters",
    tags=["characters"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=CharacterResponse, status_code=201, responses=NO_CAMPAIGN)
async def create_character(
    body: CharacterCreate,
    access: CharacterAccess = Depends(get_character_access),
    service: CharacterService = Depends(get_character_service),
):
    character = await service.create(access, body.name, body.description)
    return CharacterResponse(**character.__dict__)


@router.get("/", response_model=list[CharacterResponse], responses=NO_CAMPAIGN)
async def list_characters(
    access: CharacterAccess = Depends(get_character_access),
    service: CharacterService = Depends(get_character_service),
):
    return [CharacterResponse(**c.__dict__) for c in await service.list_for(access)]


@router.get("/{character_id}", response_model=CharacterResponse, responses=NOT_FOUND)
async def get_character(
    character_id: CharacterId,
    access: CharacterAccess = Depends(get_character_access),
    service: CharacterService = Depends(get_character_service),
):
    character = await service.get_for(character_id, access)
    return CharacterResponse(**character.__dict__)


@router.put("/{character_id}", response_model=CharacterResponse, responses=NOT_FOUND)
async def update_character(
    character_id: CharacterId,
    body: CharacterUpdate,
    access: CharacterAccess = Depends(get_character_access),
    service: CharacterService = Depends(get_character_service),
):
    character = await service.update(character_id, access, body.name, body.description)
    return CharacterResponse(**character.__dict__)


@router.delete("/{character_id}", status_code=204, responses=NOT_FOUND)
async def delete_character(
    character_id: CharacterId,
    access: CharacterAccess = Depends(get_character_access),
    service: CharacterService = Depends(get_character_service),
):
    await service.delete(character_id, access)
