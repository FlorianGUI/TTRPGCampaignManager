from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import CampaignId
from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.application.character_service import CharacterService
from app.contexts.campaign.domain.character_access import CharacterAccess
from app.contexts.user.domain.user import User
from app.database import get_db


def get_campaign_service(db: AsyncSession = Depends(get_db)) -> CampaignService:
    # The character repository comes along because deleting a campaign takes the sheets
    # at it with it — the aggregate root owns the lifecycle of what lives inside it.
    return CampaignService(SqlAlchemyCampaignRepository(db), SqlAlchemyCharacterRepository(db))


def get_character_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(SqlAlchemyCharacterRepository(db))


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
