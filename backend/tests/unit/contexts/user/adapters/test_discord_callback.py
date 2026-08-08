from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException, Response

from app.contexts.user.adapters.primary.api import oauth_state
from app.contexts.user.adapters.primary.api.routers.auth import (
    NO_ACCOUNT,
    NO_USERNAME,
    discord_callback,
    get_discord_provider,
)
from app.contexts.user.adapters.secondary.sso.discord_provider import DiscordIdentityProvider
from app.contexts.user.application.user_service import InvalidCredentialsError, UsernameUnavailableError
from app.contexts.user.domain.identity import Provider
from app.contexts.user.domain.ports.identity_provider import IdentityProvider, ProviderProfile

"""The callback's remaining answers, reached by calling the route rather than the app.

Everything a person can actually cause is covered by the acceptance feature, which drives
the whole flow through HTTP. These two are the ones a scenario cannot stage without a
contrivance: fifty usernames colliding, and an identity row that outlived the account it
named. Both are real branches with a real answer, and the answer is the point — they must
come back as an error the app can explain, not as a 500.
"""


class StubProvider(IdentityProvider):
    @property
    def provider(self) -> Provider:
        return Provider.DISCORD

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


def a_started_sign_in() -> tuple[str, str]:
    """The `state` and the cookie a real /auth/discord/authorize would have left behind.

    Built through `remember` rather than by formatting the cookie here, so this test knows
    only what a browser knows: the value of the header it was sent.
    """
    attempt = oauth_state.begin()
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


class TestBuildingTheProvider:
    def test_composes_the_real_thing_from_the_environment(self, monkeypatch: pytest.MonkeyPatch):
        """The composition root, which nothing else runs.

        The whole suite replaces this dependency so that no test can reach discord.com,
        which leaves the wiring itself unexercised — and wiring that nothing runs is wiring
        that breaks on deploy.
        """
        monkeypatch.setenv("DISCORD_CLIENT_ID", "an-id")
        monkeypatch.setenv("DISCORD_CLIENT_SECRET", "a-secret")
        monkeypatch.setenv("DISCORD_REDIRECT_URI", "https://api.example.test/auth/discord/callback")

        assert isinstance(get_discord_provider(), DiscordIdentityProvider)

    def test_refuses_to_build_without_the_settings(self, monkeypatch: pytest.MonkeyPatch):
        """A deployment that forgot them should fail where it is obvious, rather than at the
        first person who presses the button."""
        monkeypatch.delenv("DISCORD_CLIENT_ID", raising=False)

        with pytest.raises(KeyError, match="DISCORD_CLIENT_ID"):
            get_discord_provider()
