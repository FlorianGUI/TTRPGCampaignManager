from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import CampaignId
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.secondary.persistence.act_repository import SqlAlchemyActRepository
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.campaign.adapters.secondary.persistence.scene_repository import SqlAlchemySceneRepository
from app.contexts.campaign.adapters.secondary.persistence.sequence_repository import SqlAlchemySequenceRepository
from app.contexts.campaign.application.act_service import ActService
from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.application.character_service import CharacterService
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.application.sequence_service import SequenceService
from app.contexts.campaign.domain.character_access import CharacterAccess
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.user.domain.user import User
from app.database import get_db


def get_campaign_service(db: AsyncSession = Depends(get_db)) -> CampaignService:
    # Every repository whose rows belong to a campaign comes along, because deleting a
    # campaign takes all of them with it — the aggregate root owns the lifecycle of what
    # lives inside it. PR 2 added two to this line rather than two more places that sweep,
    # which is what that comment predicted and is the whole point of the shape.
    return CampaignService(
        SqlAlchemyCampaignRepository(db),
        SqlAlchemyCharacterRepository(db),
        SqlAlchemySceneRepository(db),
        SqlAlchemySequenceRepository(db),
        SqlAlchemyActRepository(db),
    )


def get_character_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(SqlAlchemyCharacterRepository(db))


def get_act_service(db: AsyncSession = Depends(get_db)) -> ActService:
    # The child repositories come along because deleting an act rehomes what was in it.
    return ActService(
        SqlAlchemyActRepository(db),
        SqlAlchemySequenceRepository(db),
        SqlAlchemySceneRepository(db),
    )


def get_sequence_service(db: AsyncSession = Depends(get_db)) -> SequenceService:
    # The act repository comes along because a sequence may name one as its parent, and
    # a parent has to be resolved before it can be trusted.
    return SequenceService(
        SqlAlchemySequenceRepository(db),
        SqlAlchemyActRepository(db),
        SqlAlchemySceneRepository(db),
    )


def get_scene_service(db: AsyncSession = Depends(get_db)) -> SceneService:
    # Both parent repositories, for the same reason: a scene may hang off either.
    return SceneService(
        SqlAlchemySceneRepository(db),
        SqlAlchemyActRepository(db),
        SqlAlchemySequenceRepository(db),
    )


async def get_character_access(
    campaign_id: CampaignId,
    user: User = Depends(get_current_user),
    campaigns: CampaignService = Depends(get_campaign_service),
) -> CharacterAccess:
    """Turn the campaign in the path into proof that this caller may reach it.

    Every route under a campaign asks for this instead of doing the check itself, so
    authorisation resolves once at the edge and the services below become pure
    orchestration. #52 and #29 both hang off a campaign; they get authorisation by
    depending on this and writing nothing.

    It is worth being clear about what does and does not make this safe. A dependency is
    additive — a new route that forgets it simply does not have it, and nothing here
    complains. What stops that being a leak is the token: a route without one cannot
    call a single repository method that touches a campaign's contents, because none of
    them accept anything else. Forgetting this fails closed rather than open.

    Nothing is caught here. `characters_at` raises `CampaignNotReachable` for a campaign
    that is missing or not this viewer's, and it travels untouched to the handler that
    turns it into a 404 — the same answer, in the same words, for either reason.
    """
    return await campaigns.characters_at(campaign_id, user.id)


async def get_narrative(
    campaign_id: CampaignId,
    user: User = Depends(get_current_user),
    campaigns: CampaignService = Depends(get_campaign_service),
) -> Narrative:
    """The same door as `get_character_access`, for the campaign's prep.

    **One dependency for all three levels**, and that is the point rather than a
    convenience: the acts, sequences and scenes routers all ask for this, so the reach
    check happens once per request no matter which level is being touched, and a fourth
    level added later cannot arrive with its own copy.

    It is also what makes reparenting cheap. A route that moves a scene under an act needs
    tokens for both, and it already holds both — so the check that the act belongs to this
    campaign is one `readable` call rather than a rule anyone had to write.

    Nothing is caught here. `narrative_at` raises `CampaignNotReachable` for a campaign
    that is missing or not this viewer's, and it travels untouched to the handler that
    turns it into a 404 — the same answer, in the same words, for either reason.
    """
    return await campaigns.narrative_at(campaign_id, user.id)
