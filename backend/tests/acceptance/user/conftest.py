import asyncio
from urllib.parse import parse_qs, urlparse

from httpx import AsyncClient, Response
from pytest_bdd import given, parsers, then, when

from app.contexts.user.adapters.primary.api.oauth_state import STATE_COOKIE_NAME
from app.contexts.user.adapters.primary.api.refresh_cookie import REFRESH_COOKIE_NAME
from app.contexts.user.domain.ports.identity_provider import ProviderProfile
from tests.conftest import FakeIdentityProvider

# Discord's snowflake for our fixture person. Here rather than in the Discord module because
# the step that uses it is shared: the Google feature signs somebody in with Discord first,
# to prove the two providers reach one account.
DISCORD_SUBJECT = "80351110224678912"

# Any string will do: the fake provider never inspects it, and a real one would have got it
# from the provider. What matters is that the *verifier* it is redeemed with came out of the
# cookie rather than out of the request.
AUTHORIZATION_CODE = "an-authorization-code"

"""Steps every user-facing feature in this package needs.

Registering and signing in are not the subject of any one feature — they are how a
scenario gets someone to be. pytest-bdd resolves steps from the module under collection
rather than from sibling files, so a step used by two features has to live here or be
written twice, and two copies of "I register as …" is two things it could mean.
"""


def held_refresh_cookie(client: AsyncClient) -> str | None:
    return client.cookies.get(REFRESH_COOKIE_NAME)


@given(parsers.parse('I register as "{username}" with email "{email}" and password "{password}"'))
@when(parsers.parse('I register as "{username}" with email "{email}" and password "{password}"'))
def register(client: AsyncClient, context: dict, username: str, email: str, password: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/users/register", json={"username": username, "email": email, "password": password})
    )
    context["response"] = response
    if response.status_code == 201:
        context["token"] = response.json()["access_token"]
        context["refresh"] = held_refresh_cookie(client)


@given(parsers.parse('I log in as "{username}" with password "{password}"'))
@when(parsers.parse('I log in as "{username}" with password "{password}"'))
def login(client: AsyncClient, context: dict, username: str, password: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/users/login", data={"username": username, "password": password})
    )
    context["response"] = response
    if response.status_code == 200:
        context["token"] = response.json()["access_token"]
        context["refresh"] = held_refresh_cookie(client)


@given("I refresh my session")
@when("I refresh my session")
def refresh_session(client: AsyncClient, context: dict):
    """No Authorization header, deliberately — the cookie is the whole credential here."""
    response = asyncio.get_event_loop().run_until_complete(client.post("/users/refresh"))
    context["response"] = response
    if response.status_code == 200:
        context["token"] = response.json()["access_token"]


@then("I should get an unauthorized error")
def get_unauthorized_error(context: dict):
    assert context["response"].status_code == 401


"""Everything a provider sign-in scenario needs that is not about one provider.

The flow is identical for Google (#36) and Discord (#39) — leave, come back, be signed in
or be told why not — so the sentences describing it are shared, and pytest-bdd resolves
steps from the module under collection or from here. Two copies of "I should be signed in"
would be two things it could mean.

What stays in each feature's own module is what genuinely differs: what that provider
knows about you, and how it fails.
"""


def run(coroutine):
    return asyncio.get_event_loop().run_until_complete(coroutine)


def start(client: AsyncClient, context: dict, provider: str) -> str:
    """Press "Continue with …" and read the `state` off the redirect.

    The browser would follow this to the provider. Here it is the value the callback will
    be checked against, which is the whole reason a test needs to see it.
    """
    response = run(client.get(f"/auth/{provider}/authorize"))
    assert response.status_code == 302
    context["state"] = parse_qs(urlparse(response.headers["location"]).query)["state"][0]
    return context["state"]


def come_back(client: AsyncClient, context: dict, provider: str, **query: str) -> Response:
    context["response"] = run(client.get(f"/auth/{provider}/callback", params=query))
    return context["response"]


def sign_in(client: AsyncClient, context: dict, provider: str) -> Response:
    state = start(client, context, provider)
    context["callback"] = {"code": AUTHORIZATION_CODE, "state": state}
    return come_back(client, context, provider, **context["callback"])


def sign_in_and_remember(client: AsyncClient, context: dict, provider: str) -> Response:
    """Sign in, and record which account it reached — if it reached one at all."""
    response = sign_in(client, context, provider)
    if issued_a_session(response):
        context["account"] = who_am_i(client)
    return response


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


@given("I confirm my address")
def confirm_my_address(client: AsyncClient, outbox: list[dict[str, str]]):
    """Follow the link registration sent, so the local half of the address is proved too.

    Linking needs both halves. This is the step that makes the difference between the
    scenario that links and the one that refuses.
    """
    token = next(word for word in outbox[-1]["text"].split() if "token=" in word).split("token=")[1]
    assert run(client.post("/users/verify-email", json={"token": token})).status_code == 200


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
    """The provider confirmed it and we checked the claim, so there is nothing left to
    prove — this is the one path that may set `email_verified` without a link followed."""
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


@then(parsers.parse('the page should know it was "{provider}"'))
def error_names_the_provider(context: dict, provider: str):
    """So the SPA can write "Google did not answer" rather than "a provider did not answer".

    It has forgotten which button was pressed by the time it lands — the round trip left the
    origin — and a provider's name is not a secret.
    """
    assert landed_on(context["response"])["provider"] == [provider]


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
def able_to_ask_who_i_am(client: AsyncClient):
    assert who_am_i(client)["username"]


@given(parsers.parse('Discord knows me as "{name}" with the confirmed address "{email}"'))
def discord_knows_me(sso_provider: FakeIdentityProvider, name: str, email: str):
    sso_provider.answer = ProviderProfile(subject=DISCORD_SUBJECT, email=email, email_verified=True, display_name=name)


@given("I sign in with Discord")
@when("I sign in with Discord")
def sign_in_with_discord(client: AsyncClient, context: dict):
    context["first_account"] = context.get("account")
    sign_in_and_remember(client, context, "discord")


@given("I have started signing in with Discord")
def started_signing_in_with_discord(client: AsyncClient, context: dict):
    start(client, context, "discord")
