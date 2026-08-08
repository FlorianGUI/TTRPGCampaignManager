import os
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.contexts.user.adapters.primary.api import oauth_state
from app.contexts.user.adapters.primary.api.dependencies import get_user_service
from app.contexts.user.adapters.primary.api.oauth_state import STATE_COOKIE_NAME
from app.contexts.user.adapters.primary.api.refresh_cookie import set_refresh_cookie
from app.contexts.user.adapters.secondary.sso.discord_provider import DiscordIdentityProvider
from app.contexts.user.adapters.secondary.sso.google_provider import GoogleIdentityProvider
from app.contexts.user.application.user_service import (
    InvalidCredentialsError,
    ProviderAccountUnlinkableError,
    ProviderAddressMissingError,
    ProviderAddressUnverifiedError,
    UsernameUnavailableError,
    UserService,
)
from app.contexts.user.domain.ports.identity_provider import IdentityProvider, IdentityProviderError

router = APIRouter(prefix="/auth", tags=["auth"])

# Where the callback hands the browser back to. The SPA, never this router: the person
# belongs in the app, and the page that lands here has one job — call /users/refresh and
# turn the cookie that was just set into an access token.
#
# Nothing sensitive travels in this URL, and that is the point of the arrangement rather
# than a happy accident. The access token stays out of it, so it never reaches browser
# history, a Referer header, or a proxy log; only the refresh cookie crosses, and a cookie
# is not part of the URL.
SSO_REDIRECT_URL = os.environ.get("SSO_REDIRECT_URL") or "http://localhost:5173/auth/callback"

# What the SPA is told when a sign-in does not finish. Stable, machine-readable, and
# deliberately not sentences: the wording belongs to the frontend, which owns the copy and
# the translations, and a code cannot accidentally leak a detail by being reworded.
CANCELLED = "cancelled"
PROVIDER_UNAVAILABLE = "provider-unavailable"
NO_EMAIL = "no-email"
UNVERIFIED_EMAIL = "unverified-email"
EMAIL_IN_USE = "email-in-use"
NO_ACCOUNT = "no-account"
NO_USERNAME = "no-username"

# What a callback that does not belong to a sign-in this server started is told. A sentence
# rather than a redirect — see the callback's docstring for why this one case is different.
_STALE_SIGN_IN = "This sign-in request has expired or did not come from here. Start again from the sign-in page."


def get_discord_provider() -> IdentityProvider:
    """The composition root for Discord, and the only place its secret is read.

    A dependency rather than a module-level instance so the whole suite can replace it with
    a fake: nothing in the tests may reach discord.com, for the same reason nothing in them
    may reach Brevo (see `no_real_mail` in tests/conftest.py).
    """
    return DiscordIdentityProvider()


def get_google_provider() -> IdentityProvider:
    """The same for Google. One provider, one secret, one place it is read."""
    return GoogleIdentityProvider()


@router.get(
    "/discord/authorize",
    status_code=status.HTTP_302_FOUND,
    responses={302: {"description": "Redirect to Discord's consent screen"}},
)
async def discord_authorize(provider: IdentityProvider = Depends(get_discord_provider)):
    return _leave_for(provider)


@router.get(
    "/google/authorize",
    status_code=status.HTTP_302_FOUND,
    responses={302: {"description": "Redirect to Google's consent screen"}},
)
async def google_authorize(provider: IdentityProvider = Depends(get_google_provider)):
    return _leave_for(provider)


@router.get(
    "/discord/callback",
    status_code=status.HTTP_302_FOUND,
    responses={
        302: {"description": "Redirect into the app, signed in — or carrying an `error` code if not"},
        400: {"description": "The callback does not belong to a sign-in this server started"},
    },
)
async def discord_callback(
    code: str | None = None,
    state: str | None = None,
    sso: str | None = Cookie(default=None, alias=STATE_COOKIE_NAME),
    provider: IdentityProvider = Depends(get_discord_provider),
    service: UserService = Depends(get_user_service),
):
    return await _come_back_from(provider, service, code=code, state=state, sso=sso)


@router.get(
    "/google/callback",
    status_code=status.HTTP_302_FOUND,
    responses={
        302: {"description": "Redirect into the app, signed in — or carrying an `error` code if not"},
        400: {"description": "The callback does not belong to a sign-in this server started"},
    },
)
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    sso: str | None = Cookie(default=None, alias=STATE_COOKIE_NAME),
    provider: IdentityProvider = Depends(get_google_provider),
    service: UserService = Depends(get_user_service),
):
    return await _come_back_from(provider, service, code=code, state=state, sso=sso)


"""Four routes, one flow.

The paths are spelled out per provider rather than collapsed into `/auth/{provider}/…`,
because an explicit route is what makes the OpenAPI schema name the two entrances a client
can actually use, and because a path parameter would turn a typo into a runtime lookup with
its own not-found branch. What must not be duplicated is the *flow* — the state check, the
error mapping, the cookie — so that lives once, below, and a third provider is a pair of
four-line routes.
"""


def _leave_for(provider: IdentityProvider) -> RedirectResponse:
    """Start a sign-in: send the browser to the provider, keep what has to come back.

    A redirect rather than a JSON body holding a URL, because the browser has to arrive at
    the provider as a *top-level navigation* — a consent screen fetched by script is a
    consent screen nobody can read, and neither Google nor Discord will be framed. It means
    the frontend's "Continue with …" is a link, not a fetch.

    Everything that has to survive the round trip is minted here and left in one httpOnly
    cookie: the `state` the callback will be checked against, and the PKCE verifier that
    proves the code coming back was requested by this browser. Neither ever reaches the page.
    """
    attempt = oauth_state.begin(provider.provider)
    response = RedirectResponse(
        provider.authorization_url(attempt.state, oauth_state.challenge(attempt)),
        status_code=status.HTTP_302_FOUND,
    )
    oauth_state.remember(response, attempt)
    return response


async def _come_back_from(
    provider: IdentityProvider,
    service: UserService,
    code: str | None,
    state: str | None,
    sso: str | None,
) -> RedirectResponse:
    """Where a provider sends the browser back, and where a session actually begins.

    **The `state` check is first and it is the only one answered with a status rather than a
    redirect.** Everything else here is a person whose sign-in did not work, and they should
    land in the app on a page that says so. A `state` that is missing or does not match is
    not that: it means this request did not come from a sign-in this server started, so
    there is nobody to send anywhere — and bouncing it onwards would render an
    attacker-triggered error state inside a victim's app. The honest cost is that a consent
    screen left open past the cookie's ten minutes ends on a plain 400, which is what
    `_STALE_SIGN_IN` explains.

    A missing `code` past that point is almost always someone pressing "Cancel" at the
    provider, which arrives as `?error=access_denied` with no code. It is not an error to
    explain in any detail — they changed their mind — so it becomes the mildest of the codes.

    The session is issued through the application layer exactly as a password login is
    (#33, #35), so what a caller ends up holding here is indistinguishable downstream: same
    access token, same refresh cookie, same logout, same rotation. Which provider it was is
    `provider.provider`, and it is the adapter's answer rather than the route's — a route
    that named its own provider could be wired to the wrong adapter and still look right.

    **The refresh cookie is `SameSite=Strict` and this response is a cross-site redirect**,
    which is worth being explicit about rather than assuming, since this is the one place in
    the app where a request originates off-site. Strict governs when a cookie is *sent*, not
    whether it may be set, so the `Set-Cookie` here lands. What follows is same-site in
    every environment — `api.lastdawn.fr` and `lastdawn.fr` share a registrable domain, and
    `localhost:8000` and `localhost:5173` differ only by port, which same-site ignores — so
    the SPA's call to /users/refresh carries it normally.
    """
    verifier = oauth_state.recall(sso, state, provider.provider)
    if verifier is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_STALE_SIGN_IN)

    if code is None:
        return _back_to_app(provider, error=CANCELLED)

    try:
        profile = await provider.profile(code, verifier)
        session = await service.sign_in_with_provider(provider.provider, profile)
    except IdentityProviderError:
        return _back_to_app(provider, error=PROVIDER_UNAVAILABLE)
    except ProviderAddressMissingError:
        return _back_to_app(provider, error=NO_EMAIL)
    except ProviderAddressUnverifiedError:
        return _back_to_app(provider, error=UNVERIFIED_EMAIL)
    except ProviderAccountUnlinkableError:
        return _back_to_app(provider, error=EMAIL_IN_USE)
    except UsernameUnavailableError:
        return _back_to_app(provider, error=NO_USERNAME)
    except InvalidCredentialsError:
        return _back_to_app(provider, error=NO_ACCOUNT)

    response = _back_to_app(provider)
    set_refresh_cookie(response, session.refresh_token, session.expires_at)
    return response


def _back_to_app(provider: IdentityProvider, error: str | None = None) -> RedirectResponse:
    """Hand the browser back to the SPA, and drop the sign-in cookie on the way out.

    Every exit from the callback goes through here, success and failure alike, which is what
    guarantees the verifier is cleared. One left behind is a single-use secret with nothing
    left to protect, and an abandoned attempt that could still be resumed.

    A failure names the provider alongside the code, and only a failure. The SPA has to
    write "Google did not answer" rather than "the provider did not answer", and by the time
    it lands here it has forgotten which button was pressed — the round trip left this
    origin. It is a provider's name, not a secret. On success nothing is added at all: the
    URL stays bare, which is what keeps a token out of history and every proxy log.
    """
    if error is None:
        url = SSO_REDIRECT_URL
    else:
        url = f"{SSO_REDIRECT_URL}?{urlencode({'error': error, 'provider': provider.provider.value})}"
    response = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    oauth_state.forget(response)
    return response
