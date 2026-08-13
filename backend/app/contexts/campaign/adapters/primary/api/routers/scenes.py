from fastapi import APIRouter, Depends

from app.common.error_handlers import not_available_responses
from app.common.ids import SceneId
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.dependencies import get_scene_access, get_scene_service
from app.contexts.campaign.adapters.primary.api.schemas.scene import SceneCreate, SceneResponse, SceneUpdate
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.domain.narrative_access import SceneAccess

# Scenes are reached through their campaign, never on their own — the shape #43 set for
# characters and #80 repeats. Every route asks for a SceneAccess rather than a campaign
# id, so the campaign in the path is authorised before any handler body runs, and a
# handler that forgot to ask would have no token and so nothing it could do with the
# repository.
#
# An unreachable campaign answers "Campaign not found" before anything inside it is
# looked at, so "not yours" and "not there" are indistinguishable at both levels.
NO_CAMPAIGN = not_available_responses("Campaign not found")
NOT_FOUND = not_available_responses("Campaign not found", "Scene not found")

router = APIRouter(
    prefix="/campaigns/{campaign_id}/scenes",
    tags=["scenes"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/", response_model=SceneResponse, status_code=201, responses=NO_CAMPAIGN)
async def create_scene(
    body: SceneCreate,
    access: SceneAccess = Depends(get_scene_access),
    service: SceneService = Depends(get_scene_service),
):
    scene = await service.create(access, body.title, body.body, body.status)
    return SceneResponse(**scene.__dict__)


@router.get("/", response_model=list[SceneResponse], responses=NO_CAMPAIGN)
async def list_scenes(
    access: SceneAccess = Depends(get_scene_access),
    service: SceneService = Depends(get_scene_service),
):
    # In narrative order, decided by the query. See the port.
    return [SceneResponse(**s.__dict__) for s in await service.list_for(access)]


@router.get("/{scene_id}", response_model=SceneResponse, responses=NOT_FOUND)
async def get_scene(
    scene_id: SceneId,
    access: SceneAccess = Depends(get_scene_access),
    service: SceneService = Depends(get_scene_service),
):
    scene = await service.get_for(scene_id, access)
    return SceneResponse(**scene.__dict__)


@router.put("/{scene_id}", response_model=SceneResponse, responses=NOT_FOUND)
async def update_scene(
    scene_id: SceneId,
    body: SceneUpdate,
    access: SceneAccess = Depends(get_scene_access),
    service: SceneService = Depends(get_scene_service),
):
    scene = await service.update(scene_id, access, body.title, body.body, body.status)
    return SceneResponse(**scene.__dict__)


@router.delete("/{scene_id}", status_code=204, responses=NOT_FOUND)
async def delete_scene(
    scene_id: SceneId,
    access: SceneAccess = Depends(get_scene_access),
    service: SceneService = Depends(get_scene_service),
):
    # Reorganising is most of what this feature is for, so a structure you can only add
    # to was never going to do (#80). Same 404-not-403 treatment as everything else.
    await service.delete(scene_id, access)
