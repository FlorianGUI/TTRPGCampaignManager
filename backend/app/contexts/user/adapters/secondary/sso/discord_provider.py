import os
from typing import Any
from urllib.parse import urlencode

import httpx

from app.contexts.user.domain.identity import Provider
from app.contexts.user.domain.ports.identity_provider import (
    IdentityProvider,
    IdentityProviderError,
    ProviderProfile,
)

AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
TOKEN_URL = "https://discord.com/api/oauth2/token"
PROFILE_URL = "https://discord.com/api/users/@me"

# `identify` alone returns no address, and without one there is nothing to key an account
# on — see `_account_for` in the user service. `email` is therefore not optional here.
#
# Deliberately nothing else, and `guilds` in particular. Reading someone's servers would
# make Discord-based campaign invites possible later (#31), but it is a far broader consent
# prompt than signing in warrants, and a login screen is the wrong place to ask for it.
SCOPE = "identify email"

# Short, like the mail sender's, and for the same reason: a person is sitting in front of a
# redirect waiting for this. A provider that has not answered in ten seconds is not about to.
_TIMEOUT_SECONDS = 10.0


class DiscordIdentityProvider(IdentityProvider):
    """Discord's half of the authorization-code flow, and nothing else.

    **Discord is plain OAuth 2.0, not OpenID Connect.** There is no `id_token`, so there is
    no signed assertion of identity to verify — which is the one real difference from Google
    (#36) rather than a naming detail. Identity comes from a second request to `/users/@me`
    carrying the access token, and the security of that call *is* the assurance: TLS to a
    pinned hostname, a token that was issued to us moments ago against a PKCE verifier only
    this server holds. There is no signature to check because there is no signature.

    What comes back is read narrowly:

    - **`id` is the subject.** A snowflake, permanent for the life of the account. `username`
      and `global_name` both change at the owner's whim and neither is unique; keying on
      either would hand one person's account to another the day they swapped handles.
    - **`verified` is the address's status**, not `email_verified` — Discord's name for the
      same idea as Google's, and the reason a shared claim-name mapping would be wrong here.
    - **`email` may be `null`**, for an account that has none. Reported as `None` rather than
      papered over; refusing it is the application's decision to make, not this adapter's.

    The client secret is read from the environment like `JWT_SECRET_KEY`, never reaches the
    frontend, and never appears in a message this class raises.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id if client_id is not None else os.environ["DISCORD_CLIENT_ID"]
        self._client_secret = client_secret if client_secret is not None else os.environ["DISCORD_CLIENT_SECRET"]
        self._redirect_uri = redirect_uri if redirect_uri is not None else os.environ["DISCORD_REDIRECT_URI"]
        self._client = client

    @property
    def provider(self) -> Provider:
        return Provider.DISCORD

    def authorization_url(self, state: str, code_challenge: str) -> str:
        """Where the browser goes to start a Discord sign-in.

        `redirect_uri` comes from configuration and is never taken from the request. Discord
        checks it against the exact URIs registered in the developer portal, but that check
        only helps if the value we send is one we chose — a redirect URI a caller could
        influence is an open redirect with an authorization code attached to it.
        """
        return f"{AUTHORIZE_URL}?" + urlencode(
            {
                "response_type": "code",
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "scope": SCOPE,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )

    async def profile(self, code: str, code_verifier: str) -> ProviderProfile:
        access_token = await self._exchange(code, code_verifier)
        return self._read(await self._fetch_profile(access_token))

    async def _exchange(self, code: str, code_verifier: str) -> str:
        """Trade the authorization code for an access token.

        Form-encoded rather than JSON, and the secret goes in the body: that is what
        Discord's token endpoint accepts. `code_verifier` is the other half of the challenge
        sent at the start, and it is what makes a stolen code useless — an attacker who
        intercepts the redirect cannot redeem it without a value that never left this server.
        """
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self._redirect_uri,
            "code_verifier": code_verifier,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        response = await self._post(TOKEN_URL, payload)
        if response.status_code >= 400:
            # The status and nothing else. The body of a token-endpoint failure quotes the
            # request back, and the request contains the client secret.
            raise IdentityProviderError(f"Discord refused the authorization code: {response.status_code}")

        token = self._json(response).get("access_token")
        if not isinstance(token, str):
            raise IdentityProviderError("Discord's token response carried no access token")
        return token

    async def _fetch_profile(self, access_token: str) -> dict[str, Any]:
        response = await self._get(PROFILE_URL, access_token)
        if response.status_code >= 400:
            raise IdentityProviderError(f"Discord refused the profile request: {response.status_code}")
        return self._json(response)

    @staticmethod
    def _read(payload: dict[str, Any]) -> ProviderProfile:
        """Turn Discord's user object into the four things a sign-in needs.

        `id` is the only field that must be there; an answer without one is not an identity
        and there is nothing to key an account on. Everything else has a defined absence:
        no address, an unconfirmed one, or no display name set — `global_name` is null for
        accounts that never chose one, which is why `username` is behind it rather than
        beside it.
        """
        subject = payload.get("id")
        if not isinstance(subject, str):
            raise IdentityProviderError("Discord's profile response carried no user id")

        email = payload.get("email")
        display_name = payload.get("global_name") or payload.get("username") or ""

        return ProviderProfile(
            subject=subject,
            email=email if isinstance(email, str) else None,
            # `verified`, not `email_verified` — Discord's name for it. Anything that is not
            # a true boolean is read as unverified, because the safe reading of a field we
            # did not understand is the one that refuses to link.
            email_verified=payload.get("verified") is True,
            display_name=display_name,
        )

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            raise IdentityProviderError("Discord answered with something that is not JSON") from None
        if not isinstance(body, dict):
            raise IdentityProviderError("Discord answered with something that is not an object")
        return body

    async def _post(self, url: str, payload: dict[str, str]) -> httpx.Response:
        headers = {"content-type": "application/x-www-form-urlencoded"}
        return await self._send("POST", url, data=payload, headers=headers)

    async def _get(self, url: str, access_token: str) -> httpx.Response:
        return await self._send("GET", url, headers={"authorization": f"Bearer {access_token}"})

    async def _send(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            if self._client is not None:
                return await self._client.request(method, url, **kwargs)
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                return await client.request(method, url, **kwargs)
        except httpx.HTTPError as error:
            # The type name only. The exception httpx raises can carry the request — headers,
            # body, and with them the client secret — into whatever logs this.
            raise IdentityProviderError(f"Could not reach Discord: {type(error).__name__}") from None
