import asyncio

from httpx import AsyncClient
from pytest_bdd import given, parsers, when

from app.contexts.user.adapters.primary.api.refresh_cookie import REFRESH_COOKIE_NAME

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
