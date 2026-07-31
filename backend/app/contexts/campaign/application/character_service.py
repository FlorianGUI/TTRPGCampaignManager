from uuid import UUID

from app.contexts.campaign.domain.character import Character
from app.contexts.campaign.domain.character_access import CharacterAccess
from app.contexts.campaign.domain.ports.character_repository import CharacterRepository


class CharacterService:
    """Characters are reached through the campaign they belong to, never on their own.

    Every method here takes a `CharacterAccess`, so authorisation has already happened by
    the time any of them run — resolved once at the edge, by the dependency that turns
    the campaign in the path into a token. That leaves this service as pure orchestration:
    it has no campaign to look up, no check to make, and nothing to raise.

    What the token permits is its own business, and so is what happens when it does not.
    `readable`, `editable` and `deletable` hand back the record or raise, which is why
    there is not a single conditional left below: this service never learns that a sheet
    was missing or forbidden, only which one it was given.
    """

    def __init__(self, repository: CharacterRepository) -> None:
        self._repository = repository

    async def create(self, access: CharacterAccess, name: str, description: str | None = None) -> Character:
        """Owner and campaign come off the token, never out of the request body.

        That is what stops a caller filing a sheet at someone else's table or under
        someone else's name: the two ids are taken from the proof of access, and the body
        supplies only what is genuinely the caller's to say.

        UNDECIDED — this method is the odd one out, and the choice is left open.

        The other four hand a record *to* the token and let it rule (`access.readable(x)`,
        `access.editable(x)`). This one reads two values *off* the token and builds the
        record itself, so it is the only method that asks the token nothing.

        Nothing is unsafe about that. A `CharacterAccess` cannot be obtained without
        `CampaignAccess.characters_at`, which refuses anyone who cannot read the campaign,
        so reaching this line already means the campaign was checked. Worth being equally
        clear that none of the other four re-check it either — `may_read` compares the
        record's campaign to the token's and never asks whether the viewer may reach that
        campaign. The whole context rests on `characters_at` being the only constructor.

        What the asymmetry does cost is a home for #31's "may a subscriber add a sheet at
        all?", which has nowhere obvious to go today. Three ways out, for whoever picks:

        1. Give `CharacterAccess` a `new_character` factory and call it here, so all five
           methods go through the token. It would sit beside `characters_at`, which is
           already a subclass-specific method, and #31's rule would raise from inside it.
           Note this method used to be exactly that and was moved here deliberately; the
           reason given was that it did not fit `Access[T]`, which `characters_at` shows
           is not really a constraint.
        2. Add a `may_add()` to `CharacterAccess` taking no record, since the question is
           about the viewer rather than about any sheet. Blocked today: the answer is
           always yes, so the guard's `raise` is unreachable and the 100% coverage gate
           rejects it. It becomes writable the moment #31 can answer no.
        3. Leave it as it is. The token parameter is itself the check, and one method
           reading differently is a small price.

        A separate question, worth keeping apart from this one: `CharacterAccess` is a
        plain dataclass, so it can be built by hand with any campaign id. Making that
        impossible (a private sentinel checked in `__post_init__`) would harden all five
        methods at once and is orthogonal to which option above is chosen.
        """
        character = Character(
            name=name,
            owner_id=access.viewer_id,
            campaign_id=access.campaign_id,
            description=description,
        )
        return await self._repository.save(character)

    async def get_for(self, id: UUID, access: CharacterAccess) -> Character:
        return access.readable(await self._repository.find_by_id(id))

    async def list_for(self, access: CharacterAccess) -> list[Character]:
        # No token method here: the filtering is the query's, not a per-record decision.
        # See CharacterAccess for what keeps the two halves saying the same thing.
        return await self._repository.find_all_in(access)

    async def update(
        self,
        id: UUID,
        access: CharacterAccess,
        name: str,
        description: str | None = None,
    ) -> Character:
        character = access.editable(await self._repository.find_by_id(id))
        character.name = name
        character.description = description
        return await self._repository.save(character)

    async def delete(self, id: UUID, access: CharacterAccess) -> None:
        character = access.deletable(await self._repository.find_by_id(id))
        await self._repository.delete(character.id)
