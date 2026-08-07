import os

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
from app.contexts.user.adapters.primary.api.schemas.user import Token, UserCreate, UserResponse, VerifyEmail
from app.contexts.user.adapters.secondary.email.brevo_email_sender import BrevoEmailSender
from app.contexts.user.adapters.secondary.persistence.email_verification_repository import (
    SqlAlchemyEmailVerificationRepository,
)
from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.email_verification_service import (
    EmailVerificationService,
    TooManyVerificationRequestsError,
    VerificationLinkUnusableError,
)
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

# Where the link in the message points: the SPA, not this router. A mail scanner that
# prefetches it loads a page and changes nothing, and the page then calls the endpoint
# above. Pointing it here would let a scanner spend the token before the person clicks.
VERIFY_EMAIL_URL = os.environ.get("VERIFY_EMAIL_URL") or "http://localhost:5173/verify-email"


def get_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(SqlAlchemyUserRepository(db), SqlAlchemyRefreshTokenRepository(db))


def get_verification_service(db: AsyncSession = Depends(get_db)) -> EmailVerificationService:
    return EmailVerificationService(
        SqlAlchemyUserRepository(db),
        SqlAlchemyEmailVerificationRepository(db),
        BrevoEmailSender(),
        verify_url=VERIFY_EMAIL_URL,
    )


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
async def register(
    request: Request,
    body: UserCreate,
    response: Response,
    service: UserService = Depends(get_service),
    verification: EmailVerificationService = Depends(get_verification_service),
):
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

    # Re-read rather than returned by `register`, which hands back tokens on purpose (#33).
    # One extra query at the one moment nobody is measuring, and it keeps the service's
    # contract as it was.
    registered = await service.get_by_token(session.access_token)
    # Composed here rather than inside `register` so that a provider outage cannot fail
    # account creation, and so every unit test of signing up does not need a mail fake.
    # `send_for_registration` swallows a delivery failure for the same reason: the account
    # and the link both exist, and re-send is the way back.
    await verification.send_for_registration(registered, session.session_id)

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


@router.post(
    "/verify-email",
    response_model=UserResponse,
    responses={400: {"description": "The link is unknown, expired, or already used"}},
)
async def verify_email(body: VerifyEmail, verification: EmailVerificationService = Depends(get_verification_service)):
    """Spend a verification token and mark the address verified.

    A POST, and the link in the message does not point here — it points at the SPA, which
    reads the token out of its own URL and calls this.

    That indirection is not architectural tidiness, it is the only way this survives
    contact with real mail. Security scanners fetch every URL in a message before a human
    sees it — Outlook Safe Links, corporate gateways, antivirus — and a GET that spends a
    single-use token is spent by the scanner. The person then clicks and is told the link
    is no longer valid, and re-sending does not help because the next one is eaten too.
    Pointing the link at a page means a prefetch loads a page and changes nothing.

    Unauthenticated on purpose. Someone who registers on a laptop and opens the mail on a
    phone is not signed in there, and requiring a session would fail the common case.

    One 400 for unknown, expired and already-used, matching how /users/refresh answers:
    nothing can be done differently between them — ask for another link — and separating
    them would confirm to whoever is guessing that a token existed.

    No rate limit of its own beyond the global one. Guessing is not the shape of attack
    here; the token is 256 bits of randomness, and the thing worth limiting is sending,
    which is limited where sending happens.
    """
    try:
        user = await verification.verify(body.token)
    except VerificationLinkUnusableError:
        raise HTTPException(status_code=400, detail="This link is no longer valid") from None
    return user


@router.post(
    "/verify-email/resend",
    status_code=204,
    responses={429: {"description": "Too many verification emails requested"}},
)
async def resend_verification(
    response: Response,
    current_user: User = Depends(get_current_user),
    refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    service: UserService = Depends(get_service),
    verification: EmailVerificationService = Depends(get_verification_service),
):
    """Send another link to the signed-in user's own address.

    Authenticated, and the address comes from the session rather than from the request.
    That is what keeps this from being a way to send mail to strangers — the worst thing a
    verification feature can turn into — and it is why nothing here has to be careful about
    disclosing whether an address is registered.

    Two limits, and they are not redundant (#38). The count of three is per session, so
    signing in starts it again; the cooldown is per account and resets for nothing, which
    is what stops a script cycling sign-in to keep sending. The cap alone would be
    decoration.

    The session comes from the refresh cookie, because an access token carries only a
    subject and cannot say which session is asking. A caller holding a valid access token
    but no cookie is answered 401 rather than allowed through uncounted.

    204 whether or not a message went out — an already-verified account is answered the
    same as a fresh send, since there is nothing to tell and nothing to do.
    """
    if refresh is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_CANNOT_RENEW)
    try:
        session_id = await service.session_of(refresh)
    except SessionNotRenewableError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_CANNOT_RENEW) from None

    try:
        await verification.resend(current_user, session_id)
    except TooManyVerificationRequestsError as error:
        if error.retry_after is not None:
            response.headers["Retry-After"] = str(error.retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification emails requested. Try again shortly.",
            headers={"Retry-After": str(error.retry_after)} if error.retry_after else None,
        ) from None
