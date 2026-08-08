import os
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

from app.contexts.user.domain.identity import Provider
from app.contexts.user.domain.ports.identity_provider import (
    IdentityProvider,
    IdentityProviderError,
    ProviderProfile,
)

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
# Where Google publishes the public halves of the keys it signs id_tokens with.
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

# Google issues tokens under both spellings and has done for years. Accepting one is a
# sign-in that fails for some accounts and not others, which is the worst kind of bug to
# find in production.
ISSUERS = ("https://accounts.google.com", "accounts.google.com")

# `openid` is what makes this OpenID Connect rather than bare OAuth: without it there is no
# id_token at all. `email` carries the address and its verified flag, `profile` the display
# name a first sign-in derives a username from.
SCOPE = "openid email profile"

# The only algorithm Google signs with, and the list is the security control rather than a
# formality. Passing the algorithms Google *might* use — or worse, letting the token's own
# header choose — is the alg-confusion family: a token that nominates `none`, or nominates
# HMAC and gets verified with the public key as the shared secret.
ALGORITHMS = ["RS256"]

_TIMEOUT_SECONDS = 10.0


class GoogleIdentityProvider(IdentityProvider):
    """Google's half of the authorization-code flow.

    **Google is OpenID Connect, and that is the whole difference from Discord (#39).**
    Identity does not arrive from a profile request; it arrives inside the token response,
    as an `id_token` — a JWT Google signed. So there is no second call, and in exchange
    there is something to verify, which is the work `_claims` below does:

    - **signature**, against the public key Google publishes for the `kid` in the header;
    - **`alg`**, pinned to RS256 rather than read from the token, because a token that
      nominates its own algorithm can nominate `none`;
    - **`aud`**, which must be our client id — a valid Google token issued to a *different*
      application is still a valid Google token, and accepting one lets any developer with a
      Google app mint sign-ins here;
    - **`iss`**, one of Google's two spellings;
    - **`exp`**, which pyjwt checks as a matter of course.

    Miss any one of those and the id_token is decoration: an attacker who can produce a JWT
    is an attacker who can produce an identity.

    `sub` is the subject and is stable for the life of the Google account. The address is
    not — it can be changed, and at a Workspace domain it can be reassigned to a different
    person entirely — so it is never what a returning sign-in is matched on.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id if client_id is not None else os.environ["GOOGLE_CLIENT_ID"]
        self._client_secret = client_secret if client_secret is not None else os.environ["GOOGLE_CLIENT_SECRET"]
        self._redirect_uri = redirect_uri if redirect_uri is not None else os.environ["GOOGLE_REDIRECT_URI"]
        self._client = client

    @property
    def provider(self) -> Provider:
        return Provider.GOOGLE

    def authorization_url(self, state: str, code_challenge: str) -> str:
        """Where the browser goes to start a Google sign-in.

        `redirect_uri` comes from configuration and never from the request. Google checks it
        against the exact URIs registered in the Cloud console, but that check only helps if
        the value we send is one we chose.

        Deliberately no `access_type=offline` and no `prompt=consent`. Both exist to obtain a
        Google *refresh* token, which is for calling Google's APIs later — this feature calls
        nothing, it establishes who somebody is once. Asking for offline access on a login
        screen is asking for a standing grant nobody needs.
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
        return self._read(await self._claims(await self._exchange(code, code_verifier)))

    async def _exchange(self, code: str, code_verifier: str) -> str:
        """Trade the authorization code for the id_token, and take only that.

        The response also carries an `access_token` for calling Google's APIs. It is
        deliberately dropped on the floor: this feature calls nothing on the user's behalf,
        so holding a credential that could is a liability with no matching use.
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
            # The status and nothing else: the body of a token-endpoint failure quotes the
            # request back, and the request contains the client secret.
            raise IdentityProviderError(f"Google refused the authorization code: {response.status_code}")

        token = self._json(response).get("id_token")
        if not isinstance(token, str):
            raise IdentityProviderError("Google's token response carried no id_token")
        return token

    async def _claims(self, id_token: str) -> dict[str, Any]:
        """Verify the id_token and return what it says, or raise.

        Everything here is a check rather than a read. `jwt.decode` is given the key, the
        algorithm list and the audience, and refuses the token if any of them disagree; the
        issuer is checked afterwards against both of Google's spellings.
        """
        key = await self._signing_key(id_token)
        try:
            claims = jwt.decode(id_token, key, algorithms=ALGORITHMS, audience=self._client_id)
        except jwt.PyJWTError as error:
            # The type name only. A bad signature, a wrong audience and an expired token are
            # one answer to a caller — the sign-in did not happen — and the token itself must
            # not travel into a log on its way out.
            raise IdentityProviderError(f"Google's id_token did not verify: {type(error).__name__}") from None

        if claims.get("iss") not in ISSUERS:
            raise IdentityProviderError("Google's id_token came from an unexpected issuer")
        return claims

    async def _signing_key(self, id_token: str) -> Any:
        """The public key Google signed this particular token with.

        The `kid` comes from the token's own unverified header, which sounds worse than it
        is: it selects *which* published key to check against, and a token naming a key that
        does not exist is refused. It cannot name a key of its own — every candidate comes
        from Google's endpoint.

        Fetched per sign-in rather than cached. Google rotates these keys, and a cache is a
        window during which a freshly-rotated key is unknown here and every sign-in fails —
        so the simple thing is also the correct one, at the cost of one request on an
        operation that happens once per person per month. Worth revisiting only if sign-in
        volume ever makes that request worth saving.
        """
        try:
            kid = jwt.get_unverified_header(id_token).get("kid")
        except jwt.PyJWTError:
            raise IdentityProviderError("Google's id_token is not a well-formed JWT") from None

        if not isinstance(kid, str):
            # A token that names no key names nothing to check it against, and "try them
            # all" is the wrong instinct here: it turns a malformed token into a search.
            raise IdentityProviderError("Google's id_token names no signing key")

        response = await self._get(JWKS_URL)
        if response.status_code >= 400:
            raise IdentityProviderError(f"Could not fetch Google's signing keys: {response.status_code}")

        try:
            return jwt.PyJWKSet.from_dict(self._json(response))[kid].key
        except (jwt.PyJWKSetError, jwt.PyJWKError, KeyError, AttributeError):
            # No such key, or a key set we cannot read. Either way there is nothing to
            # verify against, and an unverifiable token is refused rather than trusted.
            raise IdentityProviderError("Google published no signing key for this id_token") from None

    @staticmethod
    def _read(claims: dict[str, Any]) -> ProviderProfile:
        """Turn verified claims into the four things a sign-in needs.

        `sub` is the only one that must be there. `email` is absent if the scope was somehow
        not granted, and `name` is absent for accounts that have never set one — which is why
        `given_name` sits behind it rather than beside it.
        """
        subject = claims.get("sub")
        if not isinstance(subject, str):
            raise IdentityProviderError("Google's id_token carried no subject")

        email = claims.get("email")

        return ProviderProfile(
            subject=subject,
            email=email if isinstance(email, str) else None,
            # `email_verified` here, where Discord says `verified` — the one claim name that
            # genuinely differs between the two. Anything that is not a true boolean reads as
            # unverified, because the safe reading of a field we did not understand is the
            # one that refuses to link.
            email_verified=claims.get("email_verified") is True,
            display_name=claims.get("name") or claims.get("given_name") or "",
        )

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            raise IdentityProviderError("Google answered with something that is not JSON") from None
        if not isinstance(body, dict):
            raise IdentityProviderError("Google answered with something that is not an object") from None
        return body

    async def _post(self, url: str, payload: dict[str, str]) -> httpx.Response:
        headers = {"content-type": "application/x-www-form-urlencoded"}
        return await self._send("POST", url, data=payload, headers=headers)

    async def _get(self, url: str) -> httpx.Response:
        return await self._send("GET", url)

    async def _send(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        try:
            if self._client is not None:
                return await self._client.request(method, url, **kwargs)
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                return await client.request(method, url, **kwargs)
        except httpx.HTTPError as error:
            # The type name only. httpx's exception can carry the request — headers, body,
            # and with them the client secret — into whatever logs this.
            raise IdentityProviderError(f"Could not reach Google: {type(error).__name__}") from None
