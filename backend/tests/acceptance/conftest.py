import asyncio
import uuid

import pytest
from httpx import AsyncClient
from pytest_bdd import given


@pytest.fixture
def context():
    return {}


@given("I am logged in as a player")
@given("I am logged in as a game master")
def log_in(client: AsyncClient, context: dict):
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
    context["token"] = response.json()["access_token"]
