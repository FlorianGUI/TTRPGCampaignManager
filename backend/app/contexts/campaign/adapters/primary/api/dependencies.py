from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.application.character_service import CharacterService
from app.contexts.campaign.domain.access import CampaignAccess
from app.contexts.user.domain.user import User
from app.database import get_db

# A campaign the caller cannot reach answers exactly as one that does not exist.
CAMPAIGN_NOT_FOUND = HTTPException(status_code=404, detail="Campaign not found")


def get_campaign_service(db: AsyncSession = Depends(get_db)) -> CampaignService:
    # The character repository comes along because deleting a campaign takes the sheets
    # at it with it — the aggregate root owns the lifecycle of what lives inside it.
    return CampaignService(SqlAlchemyCampaignRepository(db), SqlAlchemyCharacterRepository(db))


def get_character_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(SqlAlchemyCharacterRepository(db))


async def get_campaign_access(
    campaign_id: UUID,
    user: User = Depends(get_current_user),
    campaigns: CampaignService = Depends(get_campaign_service),
) -> CampaignAccess:
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
    """
    access = await campaigns.access_to(campaign_id, user.id)
    if access is None:
        raise CAMPAIGN_NOT_FOUND
    return access
