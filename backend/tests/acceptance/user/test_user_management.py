import asyncio

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.contexts.user.adapters.primary.api.refresh_cookie import REFRESH_COOKIE_NAME

scenarios("features/user_management.feature")


@given(parsers.parse('I register as "{username}" with email "{email}" and password "{password}"'))
@when(parsers.parse('I register as "{username}" with email "{email}" and password "{password}"'))
def register(client: AsyncClient, context: dict, username: str, email: str, password: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/users/register", json={"username": username, "email": email, "password": password})
    )
    context["response"] = response
    if response.status_code == 201:
        context["token"] = response.json()["access_token"]


@given(parsers.parse('I log in as "{username}" with password "{password}"'))
@when(parsers.parse('I log in as "{username}" with password "{password}"'))
def login(client: AsyncClient, context: dict, username: str, password: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/users/login", data={"username": username, "password": password})
    )
    context["response"] = response
    if response.status_code == 200:
        context["token"] = response.json()["access_token"]


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
