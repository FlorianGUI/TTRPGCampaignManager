from app.common.ids import ActId
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.narrative_access import ActAccess
from app.contexts.campaign.domain.ports.act_repository import ActRepository
from app.contexts.campaign.domain.position import position_after


class ActService:
    """The top of the tree, and the simplest of the three services.

    An act is always a direct child of the campaign, so it has no parent to resolve and
    nothing to check beyond what the token already answered. That makes this the plainest
    repetition of PR 1's pattern — which is what #80 predicted PR 2 would mostly be.
    """

    def __init__(self, repository: ActRepository) -> None:
        self._repository = repository

    async def create(self, access: ActAccess, title: str, description: str = "") -> Act:
        act = Act(
            title=title,
            campaign_id=access.campaign_id,
            position=position_after(await self._repository.last_position_in(access)),
            description=description,
        )
        return await self._repository.save(act)

    async def get_for(self, id: ActId, access: ActAccess) -> Act:
        return access.readable(await self._repository.find_by_id(id))

    async def list_for(self, access: ActAccess) -> list[Act]:
        return await self._repository.find_all_in(access)

    async def update(self, id: ActId, access: ActAccess, title: str, description: str = "") -> Act:
        act = access.editable(await self._repository.find_by_id(id))
        act.revise(title, description)
        return await self._repository.save(act)

    async def delete(self, id: ActId, access: ActAccess) -> None:
        """Deletes the act and nothing else.

        #80 leaves open what should happen to a non-empty act — refuse, or rehome its
        children to the campaign — and is explicit that cascading is the one answer that
        loses work. Neither is implemented here: this removes one row, so today an act's
        scenes outlive it and become the campaign's, which is *accidentally* the rehome
        answer rather than a chosen one.

        PR 3 chooses. Until it does, nothing in the acceptance suite deletes a non-empty
        act, so no test is quietly blessing the current behaviour as intended.
        """
        act = access.deletable(await self._repository.find_by_id(id))
        await self._repository.delete(act.id)
