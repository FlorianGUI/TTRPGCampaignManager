import asyncio

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.contexts.user.adapters.primary.api.refresh_cookie import REFRESH_COOKIE_NAME

scenarios("features/user_management.feature")

# The refresh cookie is never touched by hand in these scenarios: the client keeps a
# cookie jar, so it arrives at /users/refresh the same way a browser would send it, and
# the tests exercise the round trip rather than a header we assembled ourselves. The one
# exception is the stolen copy, which has to be presented deliberately — that is the whole
# point of it.


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


@given("someone takes a copy of my refresh cookie")
def copy_refresh_cookie(client: AsyncClient, context: dict):
    context["stolen"] = held_refresh_cookie(client)


@when("the copy is presented")
def present_the_copy(client: AsyncClient, context: dict):
    """Sent as an explicit header so the jar's own, newer cookie stays out of the way."""
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/users/refresh", headers={"Cookie": f"{REFRESH_COOKIE_NAME}={context['stolen']}"})
    )
    context["response"] = response


@when("I log out")
def log_out(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(client.post("/users/logout"))


@when("I request my profile")
def request_profile(client: AsyncClient, context: dict):
    headers = {"Authorization": f"Bearer {context['token']}"}
    response = asyncio.get_event_loop().run_until_complete(client.get("/users/me", headers=headers))
    context["response"] = response


@when("I request my profile without a token")
def request_profile_without_token(client: AsyncClient, context: dict):
    response = asyncio.get_event_loop().run_until_complete(client.get("/users/me"))
    context["response"] = response


@then(parsers.parse('I should see a user named "{username}" with email "{email}"'))
def see_user(context: dict, username: str, email: str):
    body = context["response"].json()
    assert body["username"] == username
    assert body["email"] == email


@then("I should get a conflict error")
def get_conflict_error(context: dict):
    assert context["response"].status_code == 409


@then("I should receive an access token")
def receive_access_token(context: dict):
    assert context["response"].status_code == 200
    assert "access_token" in context["response"].json()


@then("my account is created and I receive an access token")
def account_created_with_access_token(context: dict):
    assert context["response"].status_code == 201
    assert context["response"].json()["token_type"] == "bearer"
    assert context["response"].json()["access_token"]


@then("I should not receive an access token")
def no_access_token(context: dict):
    assert "access_token" not in context["response"].json()


@then("I should get an unauthorized error")
def get_unauthorized_error(context: dict):
    assert context["response"].status_code == 401


@then("the refresh cookie is httpOnly, secure, same-site and scoped to /users")
def refresh_cookie_is_protected(context: dict):
    """All four attributes, because three of them are worth very little on their own.

    httpOnly is what an XSS runs into, Secure is what a downgraded connection runs into,
    SameSite is what a cross-site request runs into, and the path keeps the cookie off
    every request that has no business carrying a thirty-day credential.
    """
    header = context["response"].headers["set-cookie"]

    assert header.startswith(f"{REFRESH_COOKIE_NAME}=")
    assert "HttpOnly" in header
    assert "Secure" in header
    assert "SameSite=strict" in header
    assert "Path=/users" in header


@then("I should hold a different refresh token")
def refresh_token_was_replaced(client: AsyncClient, context: dict):
    now_held = held_refresh_cookie(client)
    assert now_held is not None
    assert now_held != context["refresh"]


@then("my session can no longer be refreshed")
def session_is_dead(client: AsyncClient, context: dict):
    """The token the replay was racing is gone too, which is the point of the family sweep.

    The cookie in the jar here is the *legitimate* one, handed out by the refresh that
    happened before the copy was presented. It stops working because the replay condemned
    the whole session, not just the token that was replayed.
    """
    response = asyncio.get_event_loop().run_until_complete(client.post("/users/refresh"))
    assert response.status_code == 401


@then("I should no longer hold a refresh cookie")
def refresh_cookie_is_gone(client: AsyncClient):
    assert held_refresh_cookie(client) is None


@then("I should be told nothing about whether there was one")
def logout_says_nothing(context: dict):
    assert context["response"].status_code == 204
    assert context["response"].content == b""
