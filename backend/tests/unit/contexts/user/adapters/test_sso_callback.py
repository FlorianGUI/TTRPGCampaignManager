from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response

from app.common.ids import SessionId
from app.contexts.user.adapters.primary.api import oauth_state
from app.contexts.user.adapters.primary.api.routers.auth import (
    NO_ACCOUNT,
    NO_USERNAME,
    discord_callback,
    get_discord_provider,
    get_google_provider,
    google_callback,
)
from app.contexts.user.adapters.secondary.sso.discord_provider import DiscordIdentityProvider
from app.contexts.user.adapters.secondary.sso.google_provider import GoogleIdentityProvider
from app.contexts.user.application.user_service import InvalidCredentialsError, UsernameUnavailableError
from app.contexts.user.domain.identity import Provider
from app.contexts.user.domain.ports.identity_provider import IdentityProvider, ProviderProfile
from app.contexts.user.domain.session import Session

"""The callback's remaining answers, reached by calling the route rather than the app.

Everything a person can actually cause is covered by the two acceptance features, which
drive the whole flow through HTTP. These are the ones a scenario cannot stage without a
contrivance: fifty usernames colliding, and an identity row that outlived the account it
named. Both are real branches with a real answer, and the answer is the point — they must
come back as an error the app can explain, not as a 500.

Written against the Discord route because the flow behind both is one function; a copy of
each assertion under Google would assert the same lines twice. What *is* worth checking per
provider is that each route reaches its own adapter, which is the last class here.
"""


class StubProvider(IdentityProvider):
    def __init__(self, speaks_for: Provider = Provider.DISCORD) -> None:
        self._speaks_for = speaks_for

    @property
    def provider(self) -> Provider:
        return self._speaks_for

    def authorization_url(self, state: str, code_challenge: str) -> str:
        return "https://discord.test/oauth2/authorize"

    async def profile(self, code: str, code_verifier: str) -> ProviderProfile:
        return ProviderProfile(
            subject="80351110224678912",
            email="aragorn@gondor.com",
            email_verified=True,
            display_name="Aragorn Elessar",
        )


class RefusingService:
    """A user service that gets as far as the sign-in and then cannot finish it."""

    def __init__(self, failure: Exception) -> None:
        self._failure = failure

    async def sign_in_with_provider(self, provider: Provider, profile: ProviderProfile):
        raise self._failure


class RecordingService:
    """A user service that succeeds, and remembers which provider it was told about."""

    def __init__(self, seen: list[Provider]) -> None:
        self._seen = seen

    async def sign_in_with_provider(self, provider: Provider, profile: ProviderProfile) -> Session:
        self._seen.append(provider)
        return Session(
            access_token="an-access-token",
            refresh_token="a-refresh-token",
            expires_at=datetime.now(UTC) + timedelta(days=30),
            session_id=SessionId(uuid4()),
        )


def a_started_sign_in(provider: Provider = Provider.DISCORD) -> tuple[str, str]:
    """The `state` and the cookie a real /auth/<provider>/authorize would have left behind.

    Built through `remember` rather than by formatting the cookie here, so this test knows
    only what a browser knows: the value of the header it was sent.
    """
    attempt = oauth_state.begin(provider)
    response = Response()
    oauth_state.remember(response, attempt)
    cookie = response.headers["set-cookie"].split(";")[0].split("=", 1)[1]
    return attempt.state, cookie


async def callback_refusing_with(failure: Exception):
    state, cookie = a_started_sign_in()
    return await discord_callback(
        code="an-authorization-code",
        state=state,
        sso=cookie,
        provider=StubProvider(),
        service=RefusingService(failure),  # type: ignore[arg-type]
    )


def error_on(response) -> str:
    return parse_qs(urlparse(response.headers["location"]).query)["error"][0]


class TestWhenTheSignInCannotBeFinished:
    async def test_a_base_with_no_free_variant_is_sent_back_rather_than_crashing(self):
        """Fifty variants of one derived name all taken. Nobody's fault and nothing the
        person can choose differently, but it is still an answer rather than a 500."""
        response = await callback_refusing_with(UsernameUnavailableError("aragorn-elessar"))

        assert response.status_code == 302
        assert error_on(response) == NO_USERNAME

    async def test_an_identity_naming_no_account_is_sent_back_rather_than_crashing(self):
        """A row that outlived the account it pointed at. There is nothing to sign in to,
        and the person can do nothing about the inconsistency — so they land in the app
        being told the sign-in failed."""
        response = await callback_refusing_with(InvalidCredentialsError("80351110224678912"))

        assert response.status_code == 302
        assert error_on(response) == NO_ACCOUNT

    async def test_a_refusal_still_drops_the_sign_in_cookie(self):
        """Cleared on every exit, not just the successful one. A verifier left behind is a
        single-use secret with nothing left to protect."""
        response = await callback_refusing_with(InvalidCredentialsError("80351110224678912"))

        assert oauth_state.STATE_COOKIE_NAME in response.headers["set-cookie"]

    async def test_a_refusal_hands_over_no_session(self):
        response = await callback_refusing_with(InvalidCredentialsError("80351110224678912"))

        assert "refresh=" not in response.headers["set-cookie"]


class TestAStaleCallback:
    async def test_a_cookie_that_is_not_a_pair_is_rejected(self):
        """Not a shape `remember` can produce, so it did not come from here. Refused rather
        than parsed generously — a lenient split is one where the comparison could end up
        against the wrong half of the string."""
        with pytest.raises(HTTPException) as raised:
            await discord_callback(
                code="an-authorization-code",
                state="a-state",
                sso="no-separator-in-here",
                provider=StubProvider(),
                service=RefusingService(InvalidCredentialsError("x")),  # type: ignore[arg-type]
            )

        assert raised.value.status_code == 400


class TestEachRouteReachesItsOwnProvider:
    """The one thing that genuinely differs between the two callbacks, and the one thing a
    shared implementation could get wrong invisibly: a route wired to the other adapter
    would still redirect, still set a cookie, and file every identity under the wrong
    provider."""

    async def test_the_discord_callback_signs_in_through_discord(self):
        seen: list[Provider] = []
        state, cookie = a_started_sign_in(Provider.DISCORD)

        await discord_callback(
            code="an-authorization-code",
            state=state,
            sso=cookie,
            provider=StubProvider(Provider.DISCORD),
            service=RecordingService(seen),  # type: ignore[arg-type]
        )

        assert seen == [Provider.DISCORD]

    async def test_the_google_callback_signs_in_through_google(self):
        seen: list[Provider] = []
        state, cookie = a_started_sign_in(Provider.GOOGLE)

        await google_callback(
            code="an-authorization-code",
            state=state,
            sso=cookie,
            provider=StubProvider(Provider.GOOGLE),
            service=RecordingService(seen),  # type: ignore[arg-type]
        )

        assert seen == [Provider.GOOGLE]

    async def test_a_sign_in_begun_at_one_provider_cannot_finish_at_the_other(self):
        """The cookie records which provider began the sign-in, so the mix-up shape is
        turned away here rather than left to fail at somebody else's token endpoint."""
        state, cookie = a_started_sign_in(Provider.GOOGLE)

        with pytest.raises(HTTPException) as raised:
            await discord_callback(
                code="an-authorization-code",
                state=state,
                sso=cookie,
                provider=StubProvider(Provider.DISCORD),
                service=RecordingService([]),  # type: ignore[arg-type]
            )

        assert raised.value.status_code == 400


class TestBuildingTheProviders:
    """The composition roots, which nothing else runs.

    The whole suite replaces both dependencies so that no test can reach a provider, which
    leaves the wiring itself unexercised — and wiring that nothing runs is wiring that
    breaks on deploy.
    """

    def test_composes_discord_from_the_environment(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DISCORD_CLIENT_ID", "an-id")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "a-secret")
        monkeypatch.setenv("DISCORD_REDIRECT_URI", "https://api.example.test/auth/discord/callback")

        assert isinstance(get_discord_provider(), DiscordIdentityProvider)

    def test_composes_google_from_the_environment(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "an-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "a-secret")
        monkeypatch.setenv("GOOGLE_REDIRECT_URI", "https://api.example.test/auth/google/callback")

        assert isinstance(get_google_provider(), GoogleIdentityProvider)

    def test_refuses_to_build_discord_without_the_settings(self, monkeypatch: pytest.MonkeyPatch):
        """A deployment that forgot them should fail where it is obvious, rather than at the
        first person who presses the button."""
        monkeypatch.delenv("DISCORD_CLIENT_ID", raising=False)

        with pytest.raises(KeyError, match="DISCORD_CLIENT_ID"):
            get_discord_provider()

    def test_refuses_to_build_google_without_the_settings(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

        with pytest.raises(KeyError, match="GOOGLE_CLIENT_ID"):
            get_google_provider()
