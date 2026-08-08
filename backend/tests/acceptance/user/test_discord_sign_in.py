from httpx import AsyncClient, ConnectError
from pytest_bdd import given, parsers, scenarios, when

from app.contexts.user.domain.ports.identity_provider import IdentityProviderError, ProviderProfile
from tests.acceptance.user.conftest import (
    AUTHORIZATION_CODE,
    DISCORD_SUBJECT,
    come_back,
    sign_in,
    sign_in_and_remember,
    start,
    who_am_i,
)
from tests.conftest import FakeIdentityProvider

"""The Discord sign-in, driven the way a browser drives it.

Only the leg that happens at discord.com is faked (`FakeIdentityProvider`, in the root
conftest). Everything this app is responsible for is real and under test: the redirect out,
the state cookie, the PKCE pair, the `state` comparison on the way back, which account the
sign-in reaches, and the session it leaves behind.

Redirects are deliberately not followed. The interesting part of this feature *is* the
redirect — where it points, what it carries in the query string, and which cookies ride on
it — and a client that followed them would assert on the destination instead.

Everything shared with the Google feature — signing in, being signed in, being turned away
— lives in this package's conftest. What is here is what is Discord's alone.
"""

scenarios("features/discord_sign_in.feature")

PROVIDER = "discord"

# The subject itself lives in the conftest, with the shared "Discord knows me as …" step.
SUBJECT = DISCORD_SUBJECT


@given(parsers.parse('Discord knows me as "{name}" with the unconfirmed address "{email}"'))
def discord_knows_me_unverified(sso_provider: FakeIdentityProvider, name: str, email: str):
    sso_provider.answer = ProviderProfile(subject=SUBJECT, email=email, email_verified=False, display_name=name)


@given(parsers.parse('Discord knows me as "{name}" with no address'))
def discord_knows_me_without_an_address(sso_provider: FakeIdentityProvider, name: str):
    """A Discord account can exist without one, and `email` comes back null.

    The case that has no Google counterpart at all, which is most of why these are two
    feature files rather than one with an Examples table.
    """
    sso_provider.answer = ProviderProfile(subject=SUBJECT, email=None, email_verified=False, display_name=name)


@given("Discord is unreachable")
def discord_is_unreachable(sso_provider: FakeIdentityProvider):
    sso_provider.answer = IdentityProviderError(f"Could not reach Discord: {ConnectError.__name__}")


@when("I sign in with Discord again")
def sign_in_with_discord_again(client: AsyncClient, context: dict):
    context["first_account"] = context["account"]
    sign_in_and_remember(client, context, PROVIDER)


@when(parsers.parse('Discord starts calling me "{name}"'))
def discord_renames_me(sso_provider: FakeIdentityProvider, name: str):
    assert isinstance(sso_provider.answer, ProviderProfile)
    sso_provider.answer = ProviderProfile(
        subject=sso_provider.answer.subject,
        email=sso_provider.answer.email,
        email_verified=sso_provider.answer.email_verified,
        display_name=name,
    )


@when(parsers.parse('Discord starts using the address "{email}" for me'))
def discord_changes_my_address(sso_provider: FakeIdentityProvider, email: str):
    assert isinstance(sso_provider.answer, ProviderProfile)
    sso_provider.answer = ProviderProfile(
        subject=sso_provider.answer.subject,
        email=email,
        email_verified=True,
        display_name=sso_provider.answer.display_name,
    )


@when("someone else signs in with their own Discord account")
def another_discord_account(client: AsyncClient, context: dict, sso_provider: FakeIdentityProvider):
    context["first_account"] = context["account"]
    sso_provider.answer = ProviderProfile(
        subject="99999999999999999",
        email="legolas@mirkwood.com",
        email_verified=True,
        display_name="Legolas",
    )
    sign_in(client, context, PROVIDER)
    context["account"] = who_am_i(client)


@when("I refuse to authorise the app at Discord")
def refuse_at_discord(client: AsyncClient, context: dict):
    """Pressing "Cancel" arrives as `?error=access_denied` with no code at all."""
    state = start(client, context, PROVIDER)
    come_back(client, context, PROVIDER, error="access_denied", state=state)


@when("a callback arrives with no state")
def callback_without_state(client: AsyncClient, context: dict):
    come_back(client, context, PROVIDER, code=AUTHORIZATION_CODE)


@when("the callback comes back with a state I did not send")
def callback_with_a_foreign_state(client: AsyncClient, context: dict):
    come_back(client, context, PROVIDER, code=AUTHORIZATION_CODE, state="a-state-from-somewhere-else")


@when("the callback comes back")
def callback_comes_back(client: AsyncClient, context: dict):
    come_back(client, context, PROVIDER, code=AUTHORIZATION_CODE, state=context["state"])


@when("the callback comes back a second time")
def callback_comes_back_again(client: AsyncClient, context: dict):
    """The cookie holding the verifier is cleared on the way out, so there is nothing left
    to check a replayed callback against — and nothing left to redeem a kept code with."""
    come_back(client, context, PROVIDER, **context["callback"])
