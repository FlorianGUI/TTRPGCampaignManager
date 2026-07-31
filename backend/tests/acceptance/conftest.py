import asyncio
import uuid

import pytest
from httpx import AsyncClient
from pytest_bdd import given


@pytest.fixture
def context():
    return {}


@pytest.fixture
def register_user(client: AsyncClient):
    """Register a brand new user and return their access token.

    Scenarios that need a second person — someone whose data I must not be able to
    reach — take their token from here rather than through the login step, which
    would overwrite the one identifying "me".
    """

    def _register() -> str:
        username = f"user-{uuid.uuid4().hex[:8]}"
        password = "testpass123"
        asyncio.get_event_loop().run_until_complete(
            client.post(
                "/users/register",
                json={"username": username, "email": f"{username}@example.com", "password": password},
            )
        )
        response = asyncio.get_event_loop().run_until_complete(
            client.post("/users/login", data={"username": username, "password": password})
        )
        return response.json()["access_token"]

    return _register


@given("I am logged in as a player")
@given("I am logged in as a game master")
def log_in(context: dict, register_user):
    context["token"] = register_user()
