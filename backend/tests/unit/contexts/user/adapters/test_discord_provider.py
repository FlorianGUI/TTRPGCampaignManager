from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.contexts.user.adapters.secondary.sso.discord_provider import (
    AUTHORIZE_URL,
    PROFILE_URL,
    TOKEN_URL,
    DiscordIdentityProvider,
)
from app.contexts.user.domain.identity import Provider
from app.contexts.user.domain.ports.identity_provider import IdentityProviderError

"""The Discord adapter, against a transport that never leaves the process.

`httpx.MockTransport` rather than a hand-rolled fake client, because it exercises the real
`httpx.AsyncClient` — the request this code actually builds, encoded the way httpx encodes
it — and only replaces the socket. A fake with a `request()` method would pass while the
form encoding or the header names were wrong.
"""

PROFILE_PAYLOAD = {
    "id": "80351110224678912",
    "username": "aragorn",
    "global_name": "Aragorn Elessar",
    "email": "aragorn@gondor.test",
    "verified": True,
}


def responder(*, token=None, profile=None):
    """Answer the two calls the flow makes, in the order it makes them."""

    def handle(request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            return token if token is not None else httpx.Response(200, json={"access_token": "discord-access-token"})
        assert str(request.url) == PROFILE_URL
        return profile if profile is not None else httpx.Response(200, json=PROFILE_PAYLOAD)

    return handle


def provider_with(handle, **overrides) -> DiscordIdentityProvider:
    settings = {
        "client_id": "client-id",
        "client_secret": "client-secret",
        "redirect_uri": "https://api.example.test/auth/discord/callback",
    } | overrides
    return DiscordIdentityProvider(client=httpx.AsyncClient(transport=httpx.MockTransport(handle)), **settings)


@pytest.fixture
def provider() -> DiscordIdentityProvider:
    return provider_with(responder())


def recording(sent: list[httpx.Request], **kwargs):
    """The same responder, keeping every request so a test can read what was sent."""
    answer = responder(**kwargs)

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return answer(request)

    return handle


class TestProviderIdentity:
    def test_speaks_for_discord(self, provider: DiscordIdentityProvider):
        """Half of the `(provider, subject)` key. An adapter that named the wrong one would
        file Discord identities under Google and match a sign-in to the wrong account."""
        assert provider.provider is Provider.DISCORD


class TestAuthorizationUrl:
    def test_points_at_discord(self, provider: DiscordIdentityProvider):
        url = provider.authorization_url("state-value", "challenge-value")

        assert url.startswith(f"{AUTHORIZE_URL}?")

    def test_asks_for_an_authorization_code(self, provider: DiscordIdentityProvider):
        query = parse_qs(urlparse(provider.authorization_url("state-value", "challenge-value")).query)

        assert query["response_type"] == ["code"]
        assert query["client_id"] == ["client-id"]

    def test_asks_for_the_address_as_well_as_the_identity(self, provider: DiscordIdentityProvider):
        """`identify` alone returns no address, and without one there is nothing to key an
        account on."""
        query = parse_qs(urlparse(provider.authorization_url("state-value", "challenge-value")).query)

        assert query["scope"] == ["identify email"]

    def test_does_not_ask_for_the_servers_someone_is_in(self, provider: DiscordIdentityProvider):
        """`guilds` would make Discord-based campaign invites possible later (#31) and is a
        far broader consent prompt than signing in warrants. Not on a login screen."""
        query = parse_qs(urlparse(provider.authorization_url("state-value", "challenge-value")).query)

        assert "guilds" not in query["scope"][0]

    def test_carries_the_state_and_the_hashed_challenge(self, provider: DiscordIdentityProvider):
        query = parse_qs(urlparse(provider.authorization_url("state-value", "challenge-value")).query)

        assert query["state"] == ["state-value"]
        assert query["code_challenge"] == ["challenge-value"]
        # `plain` would make the challenge the verifier, which secures nothing — anyone who
        # intercepts the authorization request would hold everything needed to redeem it.
        assert query["code_challenge_method"] == ["S256"]

    def test_sends_the_configured_redirect_uri(self, provider: DiscordIdentityProvider):
        """From configuration, never from the request. A redirect URI a caller could
        influence is an open redirect with an authorization code attached."""
        query = parse_qs(urlparse(provider.authorization_url("state-value", "challenge-value")).query)

        assert query["redirect_uri"] == ["https://api.example.test/auth/discord/callback"]

    def test_never_carries_the_secret(self, provider: DiscordIdentityProvider):
        """This URL is a browser navigation: it lands in history, in a Referer header and in
        Discord's logs. The client secret belongs in the token exchange and nowhere else."""
        assert "client-secret" not in provider.authorization_url("state-value", "challenge-value")


class TestProfile:
    async def test_reads_the_identity_off_the_user_object(self, provider: DiscordIdentityProvider):
        profile = await provider.profile("auth-code", "verifier")

        assert profile.subject == "80351110224678912"
        assert profile.email == "aragorn@gondor.test"
        assert profile.email_verified

    async def test_prefers_the_display_name_over_the_handle(self, provider: DiscordIdentityProvider):
        profile = await provider.profile("auth-code", "verifier")

        assert profile.display_name == "Aragorn Elessar"

    async def test_falls_back_to_the_handle_when_no_display_name_is_set(self):
        """`global_name` is null for accounts that never chose one, which is why `username`
        sits behind it rather than beside it."""
        payload = PROFILE_PAYLOAD | {"global_name": None}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        assert (await provider.profile("auth-code", "verifier")).display_name == "aragorn"

    async def test_copes_with_neither_name_being_present(self):
        """An empty base still has to produce an account — `username.derive` falls back to
        "adventurer" rather than failing."""
        payload = {"id": "80351110224678912", "email": "aragorn@gondor.test", "verified": True}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        assert (await provider.profile("auth-code", "verifier")).display_name == ""

    async def test_reports_a_missing_address_rather_than_inventing_one(self):
        """A Discord account can exist without one. Reported as absent; what to do about it
        is the application's decision, not this adapter's."""
        payload = PROFILE_PAYLOAD | {"email": None}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        assert (await provider.profile("auth-code", "verifier")).email is None

    async def test_reads_verified_rather_than_email_verified(self):
        """Discord's name for the claim, not Google's. Reading the wrong key would make
        every address look unverified — or, worse in the other direction, every one look
        confirmed if the default went the other way."""
        payload = PROFILE_PAYLOAD | {"verified": False}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        assert not (await provider.profile("auth-code", "verifier")).email_verified

    async def test_an_absent_verified_flag_is_read_as_unverified(self):
        """The safe reading of a field we did not get is the one that refuses to link."""
        payload = {key: value for key, value in PROFILE_PAYLOAD.items() if key != "verified"}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        assert not (await provider.profile("auth-code", "verifier")).email_verified

    async def test_a_verified_flag_that_is_not_a_boolean_is_read_as_unverified(self):
        payload = PROFILE_PAYLOAD | {"verified": "true"}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        assert not (await provider.profile("auth-code", "verifier")).email_verified

    async def test_an_address_that_is_not_a_string_is_read_as_absent(self):
        payload = PROFILE_PAYLOAD | {"email": 42}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        assert (await provider.profile("auth-code", "verifier")).email is None


class TestTheTokenExchange:
    async def test_redeems_the_code_with_the_pkce_verifier(self):
        """The verifier never left this server, so a code intercepted in the browser cannot
        be redeemed by whoever intercepted it."""
        sent: list[httpx.Request] = []
        provider = provider_with(recording(sent))

        await provider.profile("auth-code", "the-verifier")

        body = parse_qs(sent[0].content.decode())
        assert body["grant_type"] == ["authorization_code"]
        assert body["code"] == ["auth-code"]
        assert body["code_verifier"] == ["the-verifier"]

    async def test_sends_the_same_redirect_uri_it_asked_with(self):
        """The token endpoint checks it against the one in the authorization request; a
        mismatch is a refusal rather than something to discover in production."""
        sent: list[httpx.Request] = []
        provider = provider_with(recording(sent))

        await provider.profile("auth-code", "verifier")

        assert parse_qs(sent[0].content.decode())["redirect_uri"] == ["https://api.example.test/auth/discord/callback"]

    async def test_carries_the_access_token_to_the_profile_call(self):
        """Discord is plain OAuth 2.0: there is no `id_token`, so identity comes from this
        second request and the token is the only thing authorising it."""
        sent: list[httpx.Request] = []
        provider = provider_with(recording(sent))

        await provider.profile("auth-code", "verifier")

        assert sent[1].headers["authorization"] == "Bearer discord-access-token"


class TestWhenDiscordWillNotCooperate:
    async def test_refuses_a_rejected_code(self):
        provider = provider_with(responder(token=httpx.Response(400, json={"error": "invalid_grant"})))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_says_nothing_about_the_request_it_sent(self):
        """The body of a token-endpoint failure quotes the request back, and the request
        carries the client secret and the code. Only the status may travel outward."""
        provider = provider_with(responder(token=httpx.Response(400, json={"error": "invalid_grant"})))

        with pytest.raises(IdentityProviderError) as raised:
            await provider.profile("auth-code", "verifier")

        assert "client-secret" not in str(raised.value)
        assert "auth-code" not in str(raised.value)

    async def test_refuses_a_token_response_with_no_token_in_it(self):
        provider = provider_with(responder(token=httpx.Response(200, json={"token_type": "Bearer"})))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_rejected_profile_request(self):
        provider = provider_with(responder(profile=httpx.Response(401, json={"message": "401: Unauthorized"})))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_profile_with_no_user_id(self):
        """Without `id` there is no stable subject, and nothing else in the payload may be
        substituted for one — usernames change hands."""
        payload = {key: value for key, value in PROFILE_PAYLOAD.items() if key != "id"}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_user_id_that_is_not_a_string(self):
        """Snowflakes arrive as strings precisely because they overflow a JSON number. One
        that arrived as an integer has already lost precision."""
        payload = PROFILE_PAYLOAD | {"id": 80351110224678912}
        provider = provider_with(responder(profile=httpx.Response(200, json=payload)))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_an_answer_that_is_not_json(self):
        """A gateway error page, most likely. It is not an identity and must not be read as
        an empty one."""
        provider = provider_with(responder(profile=httpx.Response(200, text="<html>502 Bad Gateway</html>")))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_json_that_is_not_an_object(self):
        provider = provider_with(responder(profile=httpx.Response(200, json=["not", "a", "user"])))

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_refuses_a_provider_it_cannot_reach(self):
        def unreachable(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route to host", request=request)

        provider = provider_with(unreachable)

        with pytest.raises(IdentityProviderError):
            await provider.profile("auth-code", "verifier")

    async def test_an_unreachable_provider_says_nothing_but_the_kind_of_failure(self):
        """httpx's exception can carry the whole request — headers, body, secret — into
        whatever logs it. Only the type name travels outward."""

        def unreachable(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route to host", request=request)

        provider = provider_with(unreachable)

        with pytest.raises(IdentityProviderError) as raised:
            await provider.profile("auth-code", "verifier")

        assert str(raised.value) == "Could not reach Discord: ConnectError"


class TestTheClientItBuildsForItself:
    async def test_gives_the_provider_a_deadline(self, monkeypatch: pytest.MonkeyPatch):
        """The path every real request takes, which the tests above replace wholesale.

        The timeout is the point of covering it. Somebody is sitting in front of a redirect
        waiting on this, and a client with no deadline turns a provider having a bad day
        into a request that never comes back.
        """
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
                    return httpx.Response(200, json={"access_token": "discord-access-token"})
                return httpx.Response(200, json=PROFILE_PAYLOAD)

        monkeypatch.setattr(
            "app.contexts.user.adapters.secondary.sso.discord_provider.httpx.AsyncClient", RecordingClient
        )

        provider = DiscordIdentityProvider(
            client_id="client-id",
            client_secret="client-secret",
            redirect_uri="https://api.example.test/auth/discord/callback",
        )
        profile = await provider.profile("auth-code", "verifier")

        assert opened["timeout"] == 10.0
        assert opened["urls"] == [TOKEN_URL, PROFILE_URL]
        assert profile.subject == "80351110224678912"


class TestBuildingItFromTheEnvironment:
    def test_reads_its_settings_from_the_environment(self, monkeypatch: pytest.MonkeyPatch):
        """The default construction path, which nothing else in the suite runs: every test
        above hands in settings so that none of them can reach discord.com."""
        monkeypatch.setenv("DISCORD_CLIENT_ID", "an-id")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "a-secret")
        monkeypatch.setenv("DISCORD_REDIRECT_URI", "https://api.example.test/auth/discord/callback")

        provider = DiscordIdentityProvider()

        assert provider.authorization_url("state", "challenge").startswith(AUTHORIZE_URL)

    def test_refuses_to_build_without_a_secret(self, monkeypatch: pytest.MonkeyPatch):
        """A deployment that forgot it should fail where it is obvious, rather than at the
        first person who presses the button."""
        monkeypatch.setenv("DISCORD_CLIENT_ID", "an-id")
        monkeypatch.delenv("DISCORD_CLIENT_SECRET", raising=False)
        monkeypatch.setenv("DISCORD_REDIRECT_URI", "https://api.example.test/auth/discord/callback")

        with pytest.raises(KeyError, match="DISCORD_CLIENT_SECRET"):
            DiscordIdentityProvider()
