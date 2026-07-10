from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.contexts.user.adapters.primary.api.schemas.user import Token, UserCreate, UserResponse
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.user_service import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
    UserService,
)
from app.contexts.user.domain.user import User
from app.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


def get_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(SqlAlchemyUserRepository(db))


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: UserCreate, service: UserService = Depends(get_service)):
    try:
        user = await service.register(body.username, body.email, body.password)
    except UsernameAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Username already exists") from None
    return UserResponse(id=user.id, username=user.username, email=user.email)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), service: UserService = Depends(get_service)):
    try:
        access_token = await service.authenticate(form_data.username, form_data.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Incorrect username or password") from None
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, username=user.username, email=user.email)
