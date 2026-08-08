from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.contexts.user.adapters.primary.api.dependencies import get_user_service
from app.contexts.user.application.user_service import InvalidCredentialsError, UserService
from app.contexts.user.domain.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


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
