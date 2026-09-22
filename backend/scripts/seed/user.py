"""Seed the default game master account every other seed module signs its rows to."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.user.adapters.secondary.persistence.identity_repository import SqlAlchemyIdentityRepository
from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.user_service import UserService
from app.contexts.user.domain.user import User

USERNAME = "gm"
EMAIL = "gm@example.local"
PASSWORD = "DevPassword123!"


async def seed_user(db: AsyncSession) -> User:
    """Find the default user, creating it the first time only.

    `register()` also mints a session, which a seed script has no use for — the user is
    re-read afterwards rather than threading a `Session` through this for a value nobody
    here wants.
    """
    users = SqlAlchemyUserRepository(db)
    user = await users.find_by_username(USERNAME)
    if user is not None:
        return user

    service = UserService(users, SqlAlchemyRefreshTokenRepository(db), SqlAlchemyIdentityRepository(db))
    await service.register(USERNAME, EMAIL, PASSWORD)
    user = await users.find_by_username(USERNAME)
    assert user is not None
    return user
