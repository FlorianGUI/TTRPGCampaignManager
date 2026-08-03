from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.contexts.user.adapters.primary.api.refresh_cookie import set_refresh_cookie
from app.contexts.user.adapters.primary.api.schemas.user import Token, UserCreate, UserResponse
from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.user_service import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
    UserService,
)
from app.contexts.user.domain.session import Session
from app.contexts.user.domain.user import User
from app.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


def get_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(SqlAlchemyUserRepository(db), SqlAlchemyRefreshTokenRepository(db))


def _signed_in(response: Response, session: Session) -> Token:
    """Split one session across the two channels it travels on.

    Shared by both ways in, so neither can return an access token while forgetting the
    cookie that outlives it — which fails quietly, as a client that works right up
    until the moment it first reloads.
    """
    set_refresh_cookie(response, session.refresh_token, session.expires_at)
    return Token(access_token=session.access_token)


@router.post(
    "/register",
    response_model=Token,
    status_code=201,
    responses={409: {"description": "Username already exists"}},
)
async def register(body: UserCreate, response: Response, service: UserService = Depends(get_service)):
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
        session = await service.register(body.username, body.email, body.password)
    except UsernameAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Username already exists") from None
    return _signed_in(response, session)


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_service),
):
    """Sign in with a username and password.

    This one takes `application/x-www-form-urlencoded`, not JSON, and deliberately stays
    that way. `OAuth2PasswordBearer(tokenUrl="/users/login")` in `app/common/security/auth.py`
    declares this endpoint as the OAuth2 password flow's token URL, which is what makes
    Swagger's **Authorize** button sign in against the real endpoint. Switching to JSON
    for consistency would break that, and the inconsistency is one documented special case
    in the frontend HTTP client (#34) against a working Authorize button here.
    """
    try:
        session = await service.authenticate(form_data.username, form_data.password)
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Incorrect username or password") from None
    return _signed_in(response, session)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, username=user.username, email=user.email)
