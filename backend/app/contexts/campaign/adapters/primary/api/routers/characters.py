from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.schemas.character import (
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
)
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.application.character_service import CampaignNotAvailable, CharacterService
from app.contexts.user.domain.user import User
from app.database import get_db

# Characters are reached through their campaign, never on their own: the table in the
# path is authorised before any sheet at it is looked at.
router = APIRouter(
    prefix="/campaigns/{campaign_id}/characters",
    tags=["characters"],
    dependencies=[Depends(get_current_user)],
)

NOT_FOUND = HTTPException(status_code=404, detail="Character not found")
CAMPAIGN_NOT_FOUND = HTTPException(status_code=404, detail="Campaign not found")


def get_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(
        SqlAlchemyCharacterRepository(db),
        CampaignService(SqlAlchemyCampaignRepository(db)),
    )


@router.post("/", response_model=CharacterResponse, status_code=201)
async def create_character(
    campaign_id: UUID,
    body: CharacterCreate,
    user: User = Depends(get_current_user),
    service: CharacterService = Depends(get_service),
):
    try:
        character = await service.create(campaign_id, user.id, body.name, body.description)
    except CampaignNotAvailable:
        raise CAMPAIGN_NOT_FOUND from None
    return CharacterResponse(**character.__dict__)


@router.get("/", response_model=list[CharacterResponse])
async def list_characters(
    campaign_id: UUID,
    user: User = Depends(get_current_user),
    service: CharacterService = Depends(get_service),
):
    try:
        characters = await service.list_for(campaign_id, user.id)
    except CampaignNotAvailable:
        raise CAMPAIGN_NOT_FOUND from None
    return [CharacterResponse(**c.__dict__) for c in characters]


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    campaign_id: UUID,
    character_id: UUID,
    user: User = Depends(get_current_user),
    service: CharacterService = Depends(get_service),
):
    try:
        character = await service.get_for(character_id, campaign_id, user.id)
    except CampaignNotAvailable:
        raise CAMPAIGN_NOT_FOUND from None
    if character is None:
        raise NOT_FOUND
    return CharacterResponse(**character.__dict__)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    campaign_id: UUID,
    character_id: UUID,
    body: CharacterUpdate,
    user: User = Depends(get_current_user),
    service: CharacterService = Depends(get_service),
):
    try:
        character = await service.update(character_id, campaign_id, user.id, body.name, body.description)
    except CampaignNotAvailable:
        raise CAMPAIGN_NOT_FOUND from None
    if character is None:
        raise NOT_FOUND
    return CharacterResponse(**character.__dict__)
