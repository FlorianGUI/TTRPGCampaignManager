from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.contexts.user.adapters.secondary.sso.google_provider import (
    AUTHORIZE_URL,
    JWKS_URL,
    TOKEN_URL,
    GoogleIdentityProvider,
)
from app.contexts.user.domain.identity import Provider
from app.contexts.user.domain.ports.identity_provider import IdentityProviderError

"""The Google adapter, against a transport that never leaves the process.

The id_token here is a **real** RS256 JWT, signed by a key generated in the test and served
through a real JWKS document. That matters more than it does for Discord: the whole of
Google's identity assertion is the signature, so a test that handed the adapter a
pre-decoded payload would be testing nothing — every assertion below about a wrong
audience, a wrong issuer or a wrong key would pass against an adapter that verified none of
them.
"""

CLIENT_ID = "1234.apps.googleusercontent.com"
REDIRECT_URI = "https://api.example.test/auth/google/callback"
KID = "test-signing-key"

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
# A second key nobody publishes, for the token that claims a key it was not signed with.
_IMPOSTOR_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwks(key=_KEY, kid: str = KID) -> dict:
    published = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    return {"keys": [{**published, "kid": kid, "alg": "RS256", "use": "sig"}]}


def id_token(key=_KEY, kid: str = KID, algorithm: str = "RS256", **overrides) -> str:
    now = datetime.now(UTC)
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "110169484474386276334",
        "email": "aragorn@gondor.test",
        "email_verified": True,
        "name": "Aragorn Elessar",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    } | overrides
    # `None` in an override means "Google did not send this claim" rather than "sent it as
    # null", which is what the adapter has to cope with and what pyjwt will actually encode
    # — it refuses outright to write a null `iss`.
    return jwt.encode(
        {claim: value for claim, value in claims.items() if value is not None},
        key,
        algorithm=algorithm,
        headers={"kid": kid},
    )


def responder(*, token=None, keys=None):
    """Answer the two calls the flow makes: the token exchange, then the key set."""

    def handle(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            return token if token is not None else httpx.Response(200, json={"id_token": id_token()})
        assert str(request.url) == JWKS_URL
        return keys if keys is not None else httpx.Response(200, json=jwks())

    return handle


def provider_with(handle, **overrides) -> GoogleIdentityProvider:
    settings = {
        "client_id": CLIENT_ID,
        "client_secret": "client-secret",
        "redirect_uri": REDIRECT_URI,
    } | overrides
    return GoogleIdentityProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handle)), **settings)


def provider_for(token: str) -> GoogleIdentityProvider:
    """A provider whose token endpoint hands back exactly this id_token."""
    return provider_with(responder(token=httpx.Response(200, json={"id_token": token})))


@pytest.fixture
def provider() -> GoogleIdentityProvider:
    return provider_with(responder())


class TestProviderIdentity:
    def test_speaks_for_google(self, provider: GoogleIdentityProvider):
        assert provider.provider is Provider.GOOGLE


class TestAuthorizationUrl:
    def test_points_at_google(self, provider: GoogleIdentityProvider):
        assert provider.authorization_url("state-value", "challenge-value").startswith(f"{AUTHORIZE_URL}?")

    def test_asks_for_an_id_token_by_asking_for_openid(self, provider: GoogleIdentityProvider):
        """Without the `openid` scope there is no id_token at all, and the whole identity
        mechanism this adapter is built around simply does not happen."""
        query = parse_qs(urlparse(provider.authorization_url("s", "c")).query)

        assert query["scope"] == ["openid email profile"]

    def test_does_not_ask_for_offline_access(self, provider: GoogleIdentityProvider):
        """`access_type=offline` obtains a Google refresh token, for calling Google's APIs
        later. This feature calls nothing — it establishes who somebody is, once."""
        query = parse_qs(urlparse(provider.authorization_url("s", "c")).query)

        assert "access_type" not in query
        assert "prompt" not in query

    def test_carries_the_state_and_the_hashed_challenge(self, provider: GoogleIdentityProvider):
        query = parse_qs(urlparse(provider.authorization_url("state-value", "challenge-value")).query)

        assert query["state"] == ["state-value"]
        assert query["code_challenge"] == ["challenge-value"]
        assert query["code_challenge_method"] == ["S256"]

    def test_sends_the_configured_redirect_uri(self, provider: GoogleIdentityProvider):
        query = parse_qs(urlparse(provider.authorization_url("s", "c")).query)

        assert query["redirect_uri"] == [REDIRECT_URI]

    def test_never_carries_the_secret(self, provider: GoogleIdentityProvider):
        """This URL is a browser navigation: history, Referer, Google's logs."""
        assert "client-secret" not in provider.authorization_url("s", "c")


class TestProfile:
    async def test_reads_the_identity_out_of_the_id_token(self, provider: GoogleIdentityProvider):
        """No profile request at all — unlike Discord, the identity is in the token
        response, which is what OpenID Connect buys over bare OAuth."""
        profile = await provider.profile("auth-code", "verifier")

        assert profile.subject == "110169484474386276334"
        assert profile.email == "aragorn@gondor.test"
        assert profile.email_verified
        assert profile.display_name == "Aragorn Elessar"

    async def test_accepts_googles_other_issuer_spelling(self):
        """Google issues under both, and has for years. Accepting one is a sign-in that
        works for some accounts and not others."""
        provider = provider_for(id_token(iss="accounts.google.com"))

        assert (await provider.profile("auth-code", "verifier")).subject == "110169484474386276334"

    async def test_falls_back_to_the_given_name(self):
        """`name` is absent for accounts that never set one."""
        provider = provider_for(id_token(name=None, given_name="Aragorn"))

        assert (await provider.profile("auth-code", "verifier")).display_name == "Aragorn"

    async def test_copes_with_no_name_at_all(self):
        provider = provider_for(id_token(name=None))

        assert (await provider.profile("auth-code", "verifier")).display_name == ""

    async def test_reports_a_missing_address_rather_than_inventing_one(self):
        provider = provider_for(id_token(email=None))

        assert (await provider.profile("auth-code", "verifier")).email is None

    async def test_reads_email_verified_rather_than_verified(self):
        """Google's name for the claim, where Discord says `verified`. The one place the two
        adapters genuinely disagree, and the reason a shared claim mapping would be wrong."""
        provider = provider_for(id_token(email_verified=False))

        assert not (await provider.profile("auth-code", "verifier")).email_verified

    async def test_an_absent_verified_claim_is_read_as_unverified(self):
        provider = provider_for(id_token(email_verified=None))

        assert not (await provider.profile("auth-code", "verifier")).email_verified

    async def test_a_verified_claim_that_is_not_a_boolean_is_read_as_unverified(self):
        """Google has historically sent this as the string "true". Reading a truthy string
        as confirmation would let a claim we did not understand authorise a link."""
        provider = provider_for(id_token(email_verified="true"))

        assert not (await provider.profile("auth-code", "verifier")).email_verified

    async def test_an_address_that_is_not_a_string_is_read_as_absent(self):
        provider = provider_for(id_token(email=42))

        assert (await provider.profile("auth-code", "verifier")).email is None


class TestTheTokenExchange:
    async def test_redeems_the_code_with_the_pkce_verifier(self):
        sent: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            sent.append(request)
            return responder()(request)

        await provider_with(handle).profile("auth-code", "the-verifier")

        body = parse_qs(sent[0].content.decode())
        assert body["grant_type"] == ["authorization_code"]
        assert body["code"] == ["auth-code"]
        assert body["code_verifier"] == ["the-verifier"]
        assert body["redirect_uri"] == [REDIRECT_URI]


class TestVerifyingTheIdToken:
    """The heart of it. Every one of these is a token Google did not issue for us, and
    every one has to be refused — an id_token that is not verified is not an assertion, it
    is a string an attacker chose."""

    async def test_refuses_a_signature_from_a_key_google_never_published(self):
        """The impostor signs with its own key and labels it with the published `kid`, which
        is exactly what someone forging a token would do."""
        provider = provider_for(id_token(key=_IMPOSTOR_KEY))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_token_for_another_application(self):
        """A valid Google token issued to a different `aud` is still a perfectly valid
        Google token. Accepting one lets anybody with a Google app mint sign-ins here."""
        provider = provider_for(id_token(aud="99999.apps.googleusercontent.com"))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_token_from_another_issuer(self):
        provider = provider_for(id_token(iss="https://accounts.evil.example"))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_token_with_no_issuer(self):
        provider = provider_for(id_token(iss=None))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_an_expired_token(self):
        past = datetime.now(UTC) - timedelta(hours=1)
        provider = provider_for(id_token(exp=past, iat=past - timedelta(minutes=5)))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_an_unsigned_token(self):
        """`alg: none` is the oldest trick there is, and pinning the algorithm list rather
        than trusting the header is what closes it."""
        # `None` is what pyjwt wants as the key for `alg: none`, and what its own type hints
        # decline to describe — the signature is the point of the test.
        unsigned = jwt.encode({"sub": "1", "aud": CLIENT_ID}, None, algorithm="none")  # type: ignore[arg-type]
        provider = provider_for(unsigned)

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_token_naming_a_key_that_does_not_exist(self):
        provider = provider_for(id_token(kid="some-other-key"))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_token_naming_no_key_at_all(self):
        token = jwt.encode({"sub": "1", "aud": CLIENT_ID}, _KEY, algorithm="RS256")

        with pytest.raises(IdentityProviderError):
            await provider_for(token).profile("auth-code", "verifier")

    async def test_refuses_a_token_with_no_subject(self):
        """Without `sub` there is nothing stable to key an account on, and no other claim
        may stand in for it — an address can be reassigned."""
        provider = provider_for(id_token(sub=None))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_something_that_is_not_a_jwt(self):
        provider = provider_for("not-a-jwt-at-all")

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_says_nothing_about_the_token_it_refused(self):
        """A failed verification must not be how a token ends up in a log."""
        token = id_token(key=_IMPOSTOR_KEY)

        with pytest.raises(IdentityProviderError) as raised:
            await provider_for(token).profile("auth-code", "verifier")

        assert token not in str(raised.value)
        assert "client-secret" not in str(raised.value)


class TestWhenGoogleWillNotCooperate:
    async def test_refuses_a_rejected_code(self):
        provider = provider_with(responder(token=httpx.Response(400, json={"error": "invalid_grant"})))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_says_nothing_about_the_request_it_sent(self):
        provider = provider_with(responder(token=httpx.Response(400, json={"error": "invalid_grant"})))

        with pytest.raises(IdentityProviderError) as raised:
            await provider.profile("auth-code", "verifier")

        assert "client-secret" not in str(raised.value)
        assert "auth-code" not in str(raised.value)

    async def test_refuses_a_token_response_with_no_id_token(self):
        """A bare OAuth response — an access token and nothing else — is not an identity."""
        provider = provider_with(responder(token=httpx.Response(200, json={"access_token": "ya29..."})))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_when_the_key_set_cannot_be_fetched(self):
        provider = provider_with(responder(keys=httpx.Response(503, text="unavailable")))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_key_set_that_is_not_json(self):
        provider = provider_with(responder(keys=httpx.Response(200, text="<html>502</html>")))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_key_set_that_is_not_an_object(self):
        provider = provider_with(responder(keys=httpx.Response(200, json=["not", "a", "key", "set"])))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_key_set_with_nothing_usable_in_it(self):
        provider = provider_with(responder(keys=httpx.Response(200, json={"keys": []})))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_provider_it_cannot_reach(self):
        def unreachable(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route to host", request=request)

        with pytest.raises(IdentityProviderError) as raised:
            await provider_with(unreachable).profile("auth-code", "verifier")

        assert str(raised.value) == "Could not reach Google: ConnectError"


class TestTheClientItBuildsForItself:
    async def test_gives_the_provider_a_deadline(self, monkeypatch: pytest.MonkeyPatch):
        """The path every real request takes, which the tests above replace wholesale."""
        opened: dict[str, object] = {}

        class RecordingClient:
            def __init__(self, timeout: float) -> None:
                opened["timeout"] = timeout

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc: object) -> None:
                return None

            async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
                opened.setdefault("urls", [])
                assert isinstance(opened["urls"], list)
                opened["urls"].append(url)
                if url == TOKEN_URL:
                    return httpx.Response(200, json={"id_token": id_token()})
                return httpx.Response(200, json=jwks())

        monkeypatch.setattr(
            "app.contexts.user.adapters.secondary.sso.google_provider.httpx.AsyncClient", RecordingClient
        )

        provider = GoogleIdentityProvider(client_id=CLIENT_ID, client_secret="client-secret", redirect_uri=REDIRECT_URI)
        profile = await provider.profile("auth-code", "verifier")

        assert opened["timeout"] == 10.0
        assert opened["urls"] == [TOKEN_URL, JWKS_URL]
        assert profile.subject == "110169484474386276334"


class TestBuildingItFromTheEnvironment:
    def test_reads_its_settings_from_the_environment(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "a-secret")
        monkeypatch.setenv("GOOGLE_REDIRECT_URI", REDIRECT_URI)

        assert GoogleIdentityProvider().authorization_url("s", "c").startswith(AUTHORIZE_URL)

    def test_refuses_to_build_without_a_secret(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", CLIENT_ID)
        monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
        monkeypatch.setenv("GOOGLE_REDIRECT_URI", REDIRECT_URI)

        with pytest.raises(KeyError, match="GOOGLE_CLIENT_SECRET"):
            GoogleIdentityProvider()
