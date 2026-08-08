from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.user.adapters.secondary.persistence.identity_repository import SqlAlchemyIdentityRepository
from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.user_service import UserService
from app.database import get_db


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """The one place a `UserService` is built.

    It used to be two — the users router had one, `common/security/auth.py` had another —
    and the comment on the second already said why that was a problem: two definitions of
    what a `UserService` is, with the less-used one free to rot. Adding a third repository
    for provider sign-in is exactly the change that would have proved it, so the definitions
    are now one and every entry point shares it.

    Wired with all three repositories everywhere, including on paths that only read a user
    out of an access token. A service assembled differently depending on who asked for it is
    a service whose behaviour depends on the caller, which is the thing this avoids.
    """
    return UserService(
        SqlAlchemyUserRepository(db),
        SqlAlchemyRefreshTokenRepository(db),
        SqlAlchemyIdentityRepository(db),
    )
