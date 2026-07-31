from fastapi import APIRouter, Depends

from app.common.ids import CampaignId
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.dependencies import get_campaign_service
from app.contexts.campaign.adapters.primary.api.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
)
from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.user.domain.user import User

# A campaign the caller does not own raises CampaignNotReachable exactly as one that
# does not exist, and one handler turns that into a 404.
router = APIRouter(prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(get_current_user)])


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    body: CampaignCreate,
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_campaign_service),
):
    campaign = await service.create(body.name, user.id, body.description)
    return CampaignResponse(**campaign.__dict__)


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_campaign_service),
):
    return [CampaignResponse(**c.__dict__) for c in await service.list_for(user.id)]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: CampaignId,
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_campaign_service),
):
    campaign = await service.get_for(campaign_id, user.id)
    return CampaignResponse(**campaign.__dict__)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: CampaignId,
    body: CampaignUpdate,
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_campaign_service),
):
    campaign = await service.update(campaign_id, user.id, body.name, body.description)
    return CampaignResponse(**campaign.__dict__)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: CampaignId,
    user: User = Depends(get_current_user),
    service: CampaignService = Depends(get_campaign_service),
):
    # Takes the characters at the table with it. See CampaignService.delete.
    await service.delete(campaign_id, user.id)
