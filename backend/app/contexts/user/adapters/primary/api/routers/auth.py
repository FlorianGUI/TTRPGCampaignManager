import os
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.contexts.user.adapters.primary.api import oauth_state
from app.contexts.user.adapters.primary.api.dependencies import get_user_service
from app.contexts.user.adapters.primary.api.oauth_state import STATE_COOKIE_NAME
from app.contexts.user.adapters.primary.api.refresh_cookie import set_refresh_cookie
from app.contexts.user.adapters.secondary.sso.discord_provider import DiscordIdentityProvider
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


@router.get(
    "/discord/authorize",
    status_code=status.HTTP_302_FOUND,
    responses={302: {"description": "Redirect to Discord's consent screen"}},
)
async def discord_authorize(provider: IdentityProvider = Depends(get_discord_provider)):
    """Start a Discord sign-in.

    A redirect rather than a JSON body holding a URL, because the browser has to arrive at
    Discord as a *top-level navigation* — a consent screen fetched by script is a consent
    screen nobody can read, and Discord will not be framed. It means the frontend's
    "Continue with Discord" is a link, not a fetch.

    Everything that has to survive the round trip is minted here and left in one httpOnly
    cookie: the `state` this callback will be checked against, and the PKCE verifier that
    proves the code coming back was requested by this browser. Neither ever reaches the page.
    """
    attempt = oauth_state.begin()
    response = RedirectResponse(
        provider.authorization_url(attempt.state, oauth_state.challenge(attempt)),
        status_code=status.HTTP_302_FOUND,
    )
    oauth_state.remember(response, attempt)
    return response


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
    """Where Discord sends the browser back, and where a session actually begins.

    **The `state` check is first and it is the only one answered with a status rather than a
    redirect.** Everything else here is a person whose sign-in did not work, and they should
    land in the app on a page that says so. A `state` that is missing or does not match is
    not that: it means this request did not come from a sign-in this server started, so
    there is nobody to send anywhere — and bouncing it onwards would render an
    attacker-triggered error state inside a victim's app. The honest cost is that a consent
    screen left open past the cookie's ten minutes ends on a plain 400, which is what
    `_STALE_SIGN_IN` explains.

    A missing `code` past that point is almost always someone pressing "Cancel" at Discord,
    which arrives as `?error=access_denied` with no code. It is not an error to explain in
    any detail — they changed their mind — so it becomes the mildest of the error codes.

    The session is issued through the application layer exactly as a password login is
    (#33, #35), so what a caller ends up holding here is indistinguishable downstream: same
    access token, same refresh cookie, same logout, same rotation.

    **The refresh cookie is `SameSite=Strict` and this response is a cross-site redirect**,
    which is worth being explicit about rather than assuming, since this is the one place in
    the app where a request originates off-site. Strict governs when a cookie is *sent*, not
    whether it may be set, so the `Set-Cookie` here lands. What follows is same-site in
    every environment — `api.lastdawn.fr` and `lastdawn.fr` share a registrable domain, and
    `localhost:8000` and `localhost:5173` differ only by port, which same-site ignores — so
    the SPA's call to /users/refresh carries it normally.
    """
    verifier = oauth_state.recall(sso, state)
    if verifier is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_STALE_SIGN_IN)

    if code is None:
        return _back_to_app(error=CANCELLED)

    try:
        profile = await provider.profile(code, verifier)
        session = await service.sign_in_with_provider(provider.provider, profile)
    except IdentityProviderError:
        return _back_to_app(error=PROVIDER_UNAVAILABLE)
    except ProviderAddressMissingError:
        return _back_to_app(error=NO_EMAIL)
    except ProviderAddressUnverifiedError:
        return _back_to_app(error=UNVERIFIED_EMAIL)
    except ProviderAccountUnlinkableError:
        return _back_to_app(error=EMAIL_IN_USE)
    except UsernameUnavailableError:
        return _back_to_app(error=NO_USERNAME)
    except InvalidCredentialsError:
        return _back_to_app(error=NO_ACCOUNT)

    response = _back_to_app()
    set_refresh_cookie(response, session.refresh_token, session.expires_at)
    return response


def _back_to_app(error: str | None = None) -> RedirectResponse:
    """Hand the browser back to the SPA, and drop the sign-in cookie on the way out.

    Every exit from the callback goes through here, success and failure alike, which is what
    guarantees the verifier is cleared. One left behind is a single-use secret with nothing
    left to protect, and an abandoned attempt that could still be resumed.
    """
    url = f"{SSO_REDIRECT_URL}?{urlencode({'error': error})}" if error else SSO_REDIRECT_URL
    response = RedirectResponse(url, status_code=status.HTTP_302_FOUND)
    oauth_state.forget(response)
    return response
