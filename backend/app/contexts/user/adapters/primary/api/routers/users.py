from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.common.security.rate_limiter import (
    LOGIN_RATE_LIMIT,
    REGISTER_RATE_LIMIT,
    TOO_MANY_LOGIN_ATTEMPTS,
    TOO_MANY_REGISTRATIONS,
    limiter,
    too_many_requests_responses,
)
from app.contexts.user.adapters.primary.api.refresh_cookie import (
    REFRESH_COOKIE_NAME,
    clear_refresh_cookie,
    set_refresh_cookie,
)
from app.contexts.user.adapters.primary.api.schemas.user import Token, UserCreate, UserResponse
from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.user_service import (
    InvalidCredentialsError,
    SessionNotRenewableError,
    UsernameAlreadyExistsError,
    UserService,
)
from app.contexts.user.domain.session import Session
from app.contexts.user.domain.user import User
from app.database import get_db

router = APIRouter(prefix="/users", tags=["users"])

# What every endpoint that turns a refresh cookie away says, and it says the same thing for
# a missing cookie, an unknown token, an expired one and a replayed one. A caller can do
# nothing differently between them, and separating them would tell whoever stole a token
# which of those it was holding.
_CANNOT_RENEW = "Could not renew the session"


def get_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(SqlAlchemyUserRepository(db), SqlAlchemyRefreshTokenRepository(db))


def _signed_in(response: Response, session: Session) -> Token:
    """Split one session across the two channels it travels on.

    Shared by the three endpoints that start or continue a session, so none of them can
    return an access token while forgetting the cookie that outlives it — which fails
    quietly, as a client that works right up until the moment it first reloads.
    """
    set_refresh_cookie(response, session.refresh_token, session.expires_at)
    return Token(access_token=session.access_token)


@router.post(
    "/register",
    response_model=Token,
    status_code=201,
    responses={
        409: {"description": "Username already exists"},
        **too_many_requests_responses(TOO_MANY_REGISTRATIONS),
    },
)
@limiter.limit(REGISTER_RATE_LIMIT, error_message=TOO_MANY_REGISTRATIONS)
async def register(request: Request, body: UserCreate, response: Response, service: UserService = Depends(get_service)):
    """Create an account and sign it in, in one call.

    Registration is open: anyone reaching this endpoint can create an account. That is a
    deliberate "for now" — an invite-only campaign manager is a plausible destination, and
    it is cheaper to decide before there are accounts to migrate.

    Open, but not a faucet: `REGISTER_RATE_LIMIT` caps accounts per address per hour, which
    is the axis account spam actually runs along. Per hour rather than per minute because
    nobody signs up twice in a minute, and a per-minute cap loose enough to look harmless
    still adds up to hundreds of accounts an hour from one address.

    The `request` argument is unused here and is the limiter's — slowapi reads the caller's
    address off it, and refuses to decorate a function that has no way to hand it one.

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


@router.post("/login", response_model=Token, responses=too_many_requests_responses(TOO_MANY_LOGIN_ATTEMPTS))
@limiter.limit(LOGIN_RATE_LIMIT, error_message=TOO_MANY_LOGIN_ATTEMPTS)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    service: UserService = Depends(get_service),
):
    """Sign in with a username and password.

    `LOGIN_RATE_LIMIT` is what makes the 401 below cost something. A password check that
    can be repeated a hundred times a minute is a password check an attacker can run
    through a word list; ten is more than a person retyping a password they half remember
    needs. The key is the caller's address, never the username — one address guessing many
    passwords is the shape being defended, and keying on the username would let an attacker
    lock a victim out of their own account by failing to log in as them.

    The 429 says the same thing whatever was typed, for the same reason the 401 does: a
    limit that bit sooner for real usernames than unknown ones would be an account-existence
    oracle sitting directly on top of the answer the 401 refuses to give.

    The `request` argument is the limiter's, not this function's — see `register`.

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


@router.post(
    "/refresh",
    response_model=Token,
    responses={401: {"description": "The refresh cookie is missing, expired, revoked, or has already been spent"}},
)
async def refresh(
    response: Response,
    refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    service: UserService = Depends(get_service),
):
    """Get a new access token from the refresh cookie, with no `Authorization` header.

    Deliberately not behind `get_current_user`: the entire reason this endpoint exists is
    to be callable once the access token has expired, which is precisely when that
    dependency would turn it away. The cookie is the credential, and the browser attaches
    it on its own — a caller sends nothing.

    Every failure is a 401 rather than a 500, including the interesting one. A token that
    has already been spent revokes the whole session on its way out (see
    `UserService.refresh`), so a client that raced itself and lost is signed out and has
    to log in again. That is intended rather than a rough edge to soften: the alternative
    is leaving a leaked token working.

    Rate limiting is deliberately still the application-wide `GLOBAL_RATE_LIMIT`, and the
    tighter numbers #61 put on login and register must not be extended here. There is no
    guessing attack to slow down — the token is 256 bits of randomness, so this has none of
    the shape of credential stuffing — which leaves volume, and volume is what the global
    limit is for. The traffic is the wrong shape for a tight limit besides: login is a
    human typing a password a few times, this is a browser on a fifteen-minute timer, once
    per open tab plus once per page load.

    The client contract, which matters because this endpoint has two ways to fail and only
    one of them means anything: **a 429 here is not a dead session.** A 401 means the
    cookie is finished and the right response is to sign the user out and send them to
    /login. A 429 means the client asked too often, and signing someone out for being busy
    is a worse failure than the one the limit prevents — back off for `Retry-After` and try
    the same cookie again, which will still be good.
    """
    if refresh is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_CANNOT_RENEW)
    try:
        session = await service.refresh(refresh)
    except SessionNotRenewableError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_CANNOT_RENEW) from None
    return _signed_in(response, session)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    service: UserService = Depends(get_service),
) -> None:
    """End this session: revoke it server-side, then clear the cookie.

    Both halves matter. Clearing the cookie alone would leave a live token wherever else a
    copy of it had got to; revoking alone would leave the browser presenting a dead one on
    every reload. The row is what makes logging out mean something.

    Always 204, with no cookie or an unrecognised one just the same. Logging out is not a
    place to find out whether a token was real, and someone whose session the server has
    already revoked is trying to do the right thing — a 401 would fail them for it.

    This device only. Other browsers keep their sessions, which is the point of them being
    separate sessions.
    """
    if refresh is not None:
        await service.log_out(refresh)
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(id=user.id, username=user.username, email=user.email)
