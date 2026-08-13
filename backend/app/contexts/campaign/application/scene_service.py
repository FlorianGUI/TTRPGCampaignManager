from app.common.ids import SceneId
from app.contexts.campaign.domain.narrative_access import SceneAccess
from app.contexts.campaign.domain.ports.scene_repository import SceneRepository
from app.contexts.campaign.domain.position import position_after
from app.contexts.campaign.domain.scene import Scene, SceneStatus


class SceneService:
    """Scenes are reached through the campaign they belong to, never on their own.

    Every method takes a `SceneAccess`, so authorisation has already happened by the time
    any of them run — resolved once at the edge by the dependency that turns the campaign
    in the path into a token. `readable`, `editable` and `deletable` hand back the record
    or raise, which is why there is not a conditional anywhere below: this service never
    learns that a scene was missing or forbidden, only which one it was given.

    The one thing this service does that `CharacterService` does not is *place* a record.
    That is `create` below, and the rule it uses lives in `position.py` rather than here —
    PR 2 adds two more entities that place themselves the same way, and a service is the
    wrong home for a rule three of them share.
    """

    def __init__(self, repository: SceneRepository) -> None:
        self._repository = repository

    async def create(
        self,
        access: SceneAccess,
        title: str,
        body: str = "",
        status: SceneStatus = SceneStatus.PLANNED,
    ) -> Scene:
        """A new scene goes at the end, and the campaign comes off the token.

        Two round trips rather than one, and worth naming: asking for the last position
        and then writing is not atomic, so two scenes created in the same instant can be
        handed the same position. The consequence is that they come back in id order
        rather than creation order — a cosmetic tie in a list, not a lost or misplaced
        row — and `find_all_in`'s second sort key is what keeps even that stable. A
        campaign is one game master's prep, so the race needs one person in two tabs
        creating scenes in the same millisecond; a lock or a sequence per campaign would
        cost more than it buys, and PR 3's reorder can move either one anyway.

        `campaign_id` is taken from the proof of access and never out of the request body,
        which is what stops a caller filing a scene in someone else's campaign.
        """
        scene = Scene(
            title=title,
            campaign_id=access.campaign_id,
            position=position_after(await self._repository.last_position_in(access)),
            body=body,
            status=status,
        )
        return await self._repository.save(scene)

    async def get_for(self, id: SceneId, access: SceneAccess) -> Scene:
        return access.readable(await self._repository.find_by_id(id))

    async def list_for(self, access: SceneAccess) -> list[Scene]:
        # No token method here: the filtering is the query's, not a per-record decision,
        # and so is the ordering. See the port for why.
        return await self._repository.find_all_in(access)

    async def update(
        self,
        id: SceneId,
        access: SceneAccess,
        title: str,
        body: str,
        status: SceneStatus,
    ) -> Scene:
        scene = access.editable(await self._repository.find_by_id(id))
        scene.revise(title, body, status)
        return await self._repository.save(scene)

    async def delete(self, id: SceneId, access: SceneAccess) -> None:
        scene = access.deletable(await self._repository.find_by_id(id))
        await self._repository.delete(scene.id)
