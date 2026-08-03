from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.user_service import InvalidCredentialsError, UserService
from app.contexts.user.domain.user import User
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    # Wired with both repositories although this path only ever reads a user from an
    # access token. Building the service one way here and another in the users router
    # would leave two definitions of what a `UserService` is, and the one that never
    # touches sessions would be the one to quietly rot.
    return UserService(SqlAlchemyUserRepository(db), SqlAlchemyRefreshTokenRepository(db))


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(get_user_service),
) -> User:
    try:
        return await service.get_by_token(token)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
