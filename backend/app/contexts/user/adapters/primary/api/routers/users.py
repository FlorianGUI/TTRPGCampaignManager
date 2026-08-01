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


@router.post(
    "/register",
    response_model=Token,
    status_code=201,
    responses={409: {"description": "Username already exists"}},
)
async def register(body: UserCreate, service: UserService = Depends(get_service)):
    """Create an account and sign it in, in one call.

    Registration is open: anyone reaching this endpoint can create an account. That is a
    deliberate "for now" — an invite-only campaign manager is a plausible destination, and
    it is cheaper to decide before there are accounts to migrate.

    The 409 is the sign-up form's; a taken username belongs on the username field rather
    than in a banner. It needs no error code to be told apart, because this endpoint has
    exactly one way to conflict — but that is only true while that stays so, so a second
    conflicting condition here has to arrive with a machine-readable discriminator.
    """
    try:
        access_token = await service.register(body.username, body.email, body.password)
    except UsernameAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Username already exists") from None
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), service: UserService = Depends(get_service)):
    """Sign in with a username and password.

    This one takes `application/x-www-form-urlencoded`, not JSON, and deliberately stays
    that way. `OAuth2PasswordBearer(tokenUrl="/users/login")` in `app/common/security/auth.py`
    declares this endpoint as the OAuth2 password flow's token URL, which is what makes
    Swagger's **Authorize** button sign in against the real endpoint. Switching to JSON
    for consistency would break that, and the inconsistency is one documented special case
    in the frontend HTTP client (#34) against a working Authorize button here.
    """
    try:
        access_token = await service.authenticate(form_data.username, form_data.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Incorrect username or password") from None
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, username=user.username, email=user.email)
