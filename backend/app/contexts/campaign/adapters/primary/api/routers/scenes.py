from fastapi import APIRouter, Depends

from app.common.error_handlers import not_available_responses
from app.common.ids import ActId, SceneId, SequenceId
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.primary.api.dependencies import get_narrative, get_scene_service
from app.contexts.campaign.adapters.primary.api.schemas.scene import (
    SceneCreate,
    ScenePlacement,
    SceneResponse,
    SceneUpdate,
)
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.domain.narrative_access import Narrative

# Scenes are reached through their campaign, never on their own — the shape #43 set for
# characters and #80 repeats. Every route asks for the tree's token rather than a campaign
# id, so the campaign in the path is authorised before any handler body runs, and a
# handler that forgot to ask would have no token and so nothing it could do.
#
# A scene may name an act or a sequence as its parent, so these routes can answer for
# three things, and all three answer alike: an unreachable campaign, a scene that is not
# yours, and a parent in someone else's campaign are told apart by nothing.
NO_CAMPAIGN = not_available_responses("Campaign not found", "Act not found", "Sequence not found")
NOT_FOUND = not_available_responses("Campaign not found", "Scene not found", "Act not found", "Sequence not found")

router = APIRouter(
    prefix="/campaigns/{campaign_id}/scenes",
    tags=["scenes"],
    dependencies=[Depends(get_current_user)],
)


def _act(value) -> ActId | None:
    return ActId(value) if value else None


def _sequence(value) -> SequenceId | None:
    return SequenceId(value) if value else None


@router.post("/", response_model=SceneResponse, status_code=201, responses=NO_CAMPAIGN)
async def create_scene(
    body: SceneCreate,
    narrative: Narrative = Depends(get_narrative),
    service: SceneService = Depends(get_scene_service),
):
    scene = await service.create(
        narrative,
        body.title,
        body.body,
        body.status,
        _act(body.act_id),
        _sequence(body.sequence_id),
    )
    return SceneResponse(**scene.__dict__)


@router.get("/", response_model=list[SceneResponse], responses=NO_CAMPAIGN)
async def list_scenes(
    narrative: Narrative = Depends(get_narrative),
    service: SceneService = Depends(get_scene_service),
):
    # In narrative order, decided by the query. See the port.
    return [SceneResponse(**s.__dict__) for s in await service.list_for(narrative)]


@router.get("/{scene_id}", response_model=SceneResponse, responses=NOT_FOUND)
async def get_scene(
    scene_id: SceneId,
    narrative: Narrative = Depends(get_narrative),
    service: SceneService = Depends(get_scene_service),
):
    scene = await service.get_for(scene_id, narrative)
    return SceneResponse(**scene.__dict__)


@router.put("/{scene_id}", response_model=SceneResponse, responses=NOT_FOUND)
async def update_scene(
    scene_id: SceneId,
    body: SceneUpdate,
    narrative: Narrative = Depends(get_narrative),
    service: SceneService = Depends(get_scene_service),
):
    scene = await service.update(scene_id, narrative, body.title, body.body, body.status)
    return SceneResponse(**scene.__dict__)


@router.put("/{scene_id}/placement", response_model=SceneResponse, responses=NOT_FOUND)
async def place_scene(
    scene_id: SceneId,
    body: ScenePlacement,
    narrative: Narrative = Depends(get_narrative),
    service: SceneService = Depends(get_scene_service),
):
    """Where it sits, in one call: its parent, and its place among that parent's scenes.

    *Scenes move between acts, get cut and come back* — #80's own words, and most of what
    this feature is for. One request rather than two, because a drag that crosses acts and
    lands mid-list is one gesture and splitting it would show a wrong order in between.

    Kept apart from the update so a body typed over an hour can never move a scene by
    carrying a parent it read before someone reorganised in another tab. Both parent ids
    null puts the scene on the campaign; `after` names the sibling it was dropped below.
    """
    scene = await service.place(
        scene_id,
        narrative,
        _act(body.act_id),
        _sequence(body.sequence_id),
        body.after,
    )
    return SceneResponse(**scene.__dict__)


@router.delete("/{scene_id}", status_code=204, responses=NOT_FOUND)
async def delete_scene(
    scene_id: SceneId,
    narrative: Narrative = Depends(get_narrative),
    service: SceneService = Depends(get_scene_service),
):
    # Reorganising is most of what this feature is for, so a structure you can only add
    # to was never going to do (#80). Same 404-not-403 treatment as everything else.
    await service.delete(scene_id, narrative)
