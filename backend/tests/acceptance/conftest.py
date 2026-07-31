import asyncio
import uuid

import pytest
from httpx import AsyncClient
from pytest_bdd import given, then


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


# The three answers every context gives the same way. They live here rather than in each
# feature's step definitions so that "not found" cannot come to mean one thing for
# characters and another for campaigns.


@then("I should get a not found error")
def get_not_found_error(context: dict):
    assert context["response"].status_code == 404


@then("I should get a validation error")
def get_validation_error(context: dict):
    assert context["response"].status_code == 422


@then("I should be told I am not authenticated")
def get_unauthenticated_error(context: dict):
    assert context["response"].status_code == 401
