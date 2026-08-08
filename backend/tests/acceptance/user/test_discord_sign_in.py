import asyncio
from urllib.parse import parse_qs, urlparse

from httpx import AsyncClient, ConnectError, Response
from pytest_bdd import given, parsers, scenarios, then, when

from app.contexts.user.adapters.primary.api.oauth_state import STATE_COOKIE_NAME
from app.contexts.user.adapters.primary.api.refresh_cookie import REFRESH_COOKIE_NAME
from app.contexts.user.domain.ports.identity_provider import IdentityProviderError, ProviderProfile
from tests.conftest import FakeIdentityProvider

"""The whole Discord sign-in, driven the way a browser drives it.

Only the leg that happens at discord.com is faked (`FakeIdentityProvider`, in the root
conftest). Everything this app is responsible for is real and under test: the redirect out,
the state cookie, the PKCE pair, the `state` comparison on the way back, which account the
sign-in reaches, and the session it leaves behind.

Redirects are deliberately not followed. The interesting part of this feature *is* the
redirect — where it points, what it carries in the query string, and which cookies ride on
it — and a client that followed them would assert on the destination instead.

"I register as …", "I log in as …" and "I refresh my session" come from this package's
conftest.
"""

scenarios("features/discord_sign_in.feature")

# Any string will do: the fake provider never inspects it, and the real one would have got
# it from Discord. What matters is that the *verifier* it is redeemed with came out of the
# cookie rather than out of the request.
AUTHORIZATION_CODE = "an-authorization-code"


def run(coroutine):
    return asyncio.get_event_loop().run_until_complete(coroutine)


def start(client: AsyncClient, context: dict) -> str:
    """Press "Continue with Discord" and read the `state` off the redirect.

    The browser would follow this to discord.com. Here it is the value the callback will be
    checked against, which is the whole reason a test needs to see it.
    """
    response = run(client.get("/auth/discord/authorize"))
    assert response.status_code == 302
    context["state"] = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    return context["state"]


def come_back(client: AsyncClient, context: dict, **query: str) -> Response:
    context["response"] = run(client.get("/auth/discord/callback", params=query))
    return context["response"]


def sign_in(client: AsyncClient, context: dict) -> Response:
    state = start(client, context)
    context["callback"] = {"code": AUTHORIZATION_CODE, "state": state}
    return come_back(client, context, **context["callback"])


def landed_on(response: Response) -> dict[str, list[str]]:
    return parse_qs(urlparse(response.headers["location"]).query)


def issued_a_session(response: Response) -> bool:
    """Whether this response handed the browser a refresh cookie.

    The test for "am I signed in", rather than calling /users/refresh, because several
    scenarios start by registering — those already hold a session, and a refresh would
    succeed on the strength of the *old* one while telling us nothing about the callback.
    """
    return any(
        header.startswith(f"{REFRESH_COOKIE_NAME}=") and not header.startswith(f'{REFRESH_COOKIE_NAME}=""')
        for header in response.headers.get_list("set-cookie")
    )


def token_for(client: AsyncClient) -> str:
    """What the SPA does on landing: turn the cookie it was just given into an access token."""
    response = run(client.post("/users/refresh"))
    assert response.status_code == 200
    return response.json()["access_token"]


def who_am_i(client: AsyncClient) -> dict:
    response = run(client.get("/users/me", headers={"Authorization": f"Bearer {token_for(client)}"}))
    assert response.status_code == 200
    return response.json()


@given(parsers.parse('Discord knows me as "{name}" with the confirmed address "{email}"'))
def discord_knows_me(sso_provider: FakeIdentityProvider, name: str, email: str):
    sso_provider.answer = ProviderProfile(
        subject="80351110224678912", email=email, email_verified=True, display_name=name
    )


@given(parsers.parse('Discord knows me as "{name}" with the unconfirmed address "{email}"'))
def discord_knows_me_unverified(sso_provider: FakeIdentityProvider, name: str, email: str):
    sso_provider.answer = ProviderProfile(
        subject="80351110224678912", email=email, email_verified=False, display_name=name
    )


@given(parsers.parse('Discord knows me as "{name}" with no address'))
def discord_knows_me_without_an_address(sso_provider: FakeIdentityProvider, name: str):
    """A Discord account can exist without one, and `email` comes back null."""
    sso_provider.answer = ProviderProfile(
        subject="80351110224678912", email=None, email_verified=False, display_name=name
    )


@given("Discord is unreachable")
def discord_is_unreachable(sso_provider: FakeIdentityProvider):
    sso_provider.answer = IdentityProviderError(f"Could not reach Discord: {ConnectError.__name__}")


@given("I confirm my address")
def confirm_my_address(client: AsyncClient, outbox: list[dict[str, str]]):
    """Follow the link registration sent, so the local half of the address is proved too.

    Linking needs both halves. This is the step that makes the difference between the
    scenario that links and the one that refuses.
    """
    token = next(word for word in outbox[-1]["text"].split() if "token=" in word).split("token=")[1]
    assert run(client.post("/users/verify-email", json={"token": token})).status_code == 200


@given("I sign in with Discord")
@when("I sign in with Discord")
def sign_in_with_discord(client: AsyncClient, context: dict):
    response = sign_in(client, context)
    if issued_a_session(response):
        context["account"] = who_am_i(client)


@when("I sign in with Discord again")
def sign_in_with_discord_again(client: AsyncClient, context: dict):
    context["first_account"] = context["account"]
    response = sign_in(client, context)
    if issued_a_session(response):
        context["account"] = who_am_i(client)


@given("I have started signing in with Discord")
def started_signing_in(client: AsyncClient, context: dict):
    start(client, context)


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
    sign_in(client, context)
    context["account"] = who_am_i(client)


@when("I refuse to authorise the app at Discord")
def refuse_at_discord(client: AsyncClient, context: dict):
    """Pressing "Cancel" arrives as `?error=access_denied` with no code at all."""
    state = start(client, context)
    come_back(client, context, error="access_denied", state=state)


@when("a callback arrives with no state")
def callback_without_state(client: AsyncClient, context: dict):
    come_back(client, context, code=AUTHORIZATION_CODE)


@when("the callback comes back with a state I did not send")
def callback_with_a_foreign_state(client: AsyncClient, context: dict):
    come_back(client, context, code=AUTHORIZATION_CODE, state="a-state-from-somewhere-else")


@when("the callback comes back")
def callback_comes_back(client: AsyncClient, context: dict):
    come_back(client, context, code=AUTHORIZATION_CODE, state=context["state"])


@when("the callback comes back a second time")
def callback_comes_back_again(client: AsyncClient, context: dict):
    """The cookie holding the verifier is cleared on the way out, so there is nothing left
    to check a replayed callback against — and nothing left to redeem a kept code with."""
    come_back(client, context, **context["callback"])


@given("my browser loses its sign-in cookie")
def lose_the_sign_in_cookie(client: AsyncClient):
    client.cookies.delete(STATE_COOKIE_NAME, path="/auth")


@when("I log out")
def log_out(client: AsyncClient, context: dict):
    context["response"] = run(client.post("/users/logout"))


@then("I should be signed in")
def signed_in(context: dict):
    response = context["response"]
    assert response.status_code == 302
    assert "error" not in landed_on(response)
    assert issued_a_session(response)


@then("I should not be signed in")
def not_signed_in(context: dict):
    """No new session came out of this callback.

    Stated as "the callback issued no refresh cookie" rather than "/users/refresh fails",
    because some of these scenarios registered first and are legitimately still signed in
    as somebody. What must not happen is the refused sign-in handing over a session.
    """
    assert not issued_a_session(context["response"])


@then(parsers.parse('my account should be named "{username}"'))
def account_named(client: AsyncClient, username: str):
    assert who_am_i(client)["username"] == username


@then("my address should already be confirmed")
def address_already_confirmed(client: AsyncClient):
    """Discord confirmed it and we checked the claim, so there is nothing left to prove —
    this is the one path that may set `email_verified` without a link being followed."""
    assert who_am_i(client)["email_verified"]


@then("it should be the same account as before")
def same_account(context: dict):
    assert context["account"]["id"] == context["first_account"]["id"]


@then("it should be a different account")
def different_account(context: dict):
    assert context["account"]["id"] != context["first_account"]["id"]


@then(parsers.parse('I should be sent back with the error "{code}"'))
def sent_back_with_error(context: dict, code: str):
    """Back into the app, carrying a stable code rather than a sentence.

    The wording belongs to the frontend, which owns the copy — and a code cannot leak a
    detail by being reworded.
    """
    response = context["response"]
    assert response.status_code == 302
    assert landed_on(response)["error"] == [code]


@then("the callback should be rejected")
def callback_rejected(context: dict):
    """A status rather than a redirect, and deliberately so: a callback whose `state` does
    not match did not come from a sign-in this server started, so there is nobody to send
    into the app — and bouncing it onwards would render an attacker-triggered error inside
    a victim's session."""
    assert context["response"].status_code == 400


@then("the page I land on should carry no token")
def no_token_in_the_url(context: dict):
    """The reason the flow ends in a cookie and a redirect. A URL lands in browser history,
    in a Referer header and in every proxy log on the way."""
    location = context["response"].headers["location"]
    assert "token" not in location.lower()
    assert not urlparse(location).fragment


@then("I should be able to ask who I am")
def able_to_ask_who_i_am(client: AsyncClient, context: dict):
    assert who_am_i(client)["username"]
