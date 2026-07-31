from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
)
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.user.domain.user import User
from app.database import get_db

router = APIRouter(prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(get_current_user)])

# A campaign the caller does not own answers exactly as one that does not exist.
NOT_FOUND = HTTPException(status_code=404, detail="Campaign not found")


def get_service(db: AsyncSession = Depends(get_db)) -> CampaignService:
    return CampaignService(SqlAlchemyCampaignRepository(db))


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    body: CampaignCreate,
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_service),
):
    campaign = await service.create(body.name, user.id, body.description)
    return CampaignResponse(**campaign.__dict__)


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_service),
):
    return [CampaignResponse(**c.__dict__) for c in await service.list_for(user.id)]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_service),
):
    campaign = await service.get_for(campaign_id, user.id)
    if campaign is None:
        raise NOT_FOUND
    return CampaignResponse(**campaign.__dict__)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: UUID,
    body: CampaignUpdate,
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_service),
):
    campaign = await service.update(campaign_id, user.id, body.name, body.description)
    if campaign is None:
        raise NOT_FOUND
    return CampaignResponse(**campaign.__dict__)
