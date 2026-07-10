from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.security import decode_access_token
from app.contexts.user.application.user_service import UserService
from app.contexts.user.domain.user import User
from app.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(SqlAlchemyUserRepository(db))


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: UserService = Depends(get_user_service),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = UUID(decode_access_token(token))
    except (PyJWTError, ValueError):
        raise credentials_error
    user = await service.get(user_id)
    if user is None:
        raise credentials_error
    return user