from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.character.adapters.primary.api.schemas.character import (
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
)
from app.contexts.character.adapters.secondary.campaign_access import CampaignServiceAccess
from app.contexts.character.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.character.application.character_service import CampaignNotAvailable, CharacterService
from app.contexts.user.domain.user import User
from app.database import get_db

router = APIRouter(prefix="/characters", tags=["characters"], dependencies=[Depends(get_current_user)])

# A character the caller can reach through neither link answers exactly as one that
# does not exist. The campaign case is worded differently because it is a different
# mistake — naming a table that is not yours — but it gives away no more than this one.
NOT_FOUND = HTTPException(status_code=404, detail="Character not found")
CAMPAIGN_NOT_FOUND = HTTPException(status_code=404, detail="Campaign not found")


def get_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(
        SqlAlchemyCharacterRepository(db),
        CampaignServiceAccess(CampaignService(SqlAlchemyCampaignRepository(db))),
    )


@router.post("/", response_model=CharacterResponse, status_code=201)
async def create_character(
    body: CharacterCreate,
    user: User = Depends(get_current_user),
    service: CharacterService = Depends(get_service),
):
    try:
        character = await service.create(body.name, body.character_class, user.id, body.campaign_id)
    except CampaignNotAvailable:
        raise CAMPAIGN_NOT_FOUND from None
    return CharacterResponse(**character.__dict__)


@router.get("/", response_model=list[CharacterResponse])
async def list_characters(
    user: User = Depends(get_current_user),
    service: CharacterService = Depends(get_service),
):
    return [CharacterResponse(**c.__dict__) for c in await service.list_for(user.id)]


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: UUID,
    user: User = Depends(get_current_user),
    service: CharacterService = Depends(get_service),
):
    character = await service.get_for(character_id, user.id)
    if character is None:
        raise NOT_FOUND
    return CharacterResponse(**character.__dict__)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: UUID,
    body: CharacterUpdate,
    user: User = Depends(get_current_user),
    service: CharacterService = Depends(get_service),
):
    try:
        character = await service.update(
            character_id,
            user.id,
            body.name,
            body.character_class,
            body.level,
            body.campaign_id,
        )
    except CampaignNotAvailable:
        raise CAMPAIGN_NOT_FOUND from None
    if character is None:
        raise NOT_FOUND
    return CharacterResponse(**character.__dict__)
