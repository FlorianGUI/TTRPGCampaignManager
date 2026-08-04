import uuid

import pytest
from httpx import AsyncClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.common.security.rate_limiter import (
    TOO_MANY_LOGIN_ATTEMPTS,
    TOO_MANY_REGISTRATIONS,
    limiter,
)
from app.main import app


@pytest.fixture
async def rate_limited_client(client: AsyncClient):
    """A client whose global limit is two, so "past the default" is two calls rather than a hundred."""
    app.state.limiter = Limiter(key_func=get_remote_address, default_limits=["2/minute"], headers_enabled=True)
    yield client
    app.state.limiter = limiter


def _new_account() -> dict[str, str]:
    username = f"user-{uuid.uuid4().hex[:8]}"
    return {"username": username, "email": f"{username}@example.com", "password": "testpass123"}


class TestGlobalRateLimit:
    async def test_requests_within_limit_succeed(self, rate_limited_client: AsyncClient):
        assert (await rate_limited_client.get("/health")).status_code == 200
        assert (await rate_limited_client.get("/health")).status_code == 200

    async def test_request_exceeding_limit_returns_429(self, rate_limited_client: AsyncClient):
        await rate_limited_client.get("/health")
        await rate_limited_client.get("/health")

        response = await rate_limited_client.get("/health")

        assert response.status_code == 429


class TestLoginRateLimit:
    """Ten a minute, against the real limiter — no fixture lowers it.

    Every attempt here is wrong on purpose. The limit has to count attempts rather than
    failures: an attacker working a word list is not going to volunteer a correct password
    to reset the counter, and a limiter that only counted 401s would be one that stops
    counting the moment the guessing succeeds.
    """

    async def test_attempts_up_to_the_limit_are_answered_normally(self, client: AsyncClient):
        for _ in range(10):
            response = await client.post("/users/login", data={"username": "nobody", "password": "wrong"})
            assert response.status_code == 401

    async def test_the_attempt_past_the_limit_is_turned_away(self, client: AsyncClient):
        for _ in range(10):
            await client.post("/users/login", data={"username": "nobody", "password": "wrong"})

        response = await client.post("/users/login", data={"username": "nobody", "password": "wrong"})

        assert response.status_code == 429
        assert response.json() == {"detail": TOO_MANY_LOGIN_ATTEMPTS}
        assert "retry-after" in response.headers

    async def test_a_throttled_attempt_says_nothing_about_the_account(self, client: AsyncClient):
        """The 429 must not become the oracle the 401 above it refuses to be.

        Registering first means one of these usernames exists and the other does not. If
        being real changed the answer — a different message, or a limit that bit at a
        different point — then hitting the limit twice would tell an attacker which
        usernames are worth a word list.
        """
        real = _new_account()
        await client.post("/users/register", json=real)

        for _ in range(10):
            await client.post("/users/login", data={"username": real["username"], "password": "wrong"})
        for_real_account = await client.post("/users/login", data={"username": real["username"], "password": "wrong"})
        for_unknown_account = await client.post("/users/login", data={"username": "nobody", "password": "wrong"})

        assert for_real_account.status_code == for_unknown_account.status_code == 429
        assert for_real_account.json() == for_unknown_account.json()


class TestRegisterRateLimit:
    """Five an hour, against the real limiter.

    Sign-ups succeed all the way to the limit — unlike login there is no failure to lean
    on, and account spam is made of requests that work.
    """

    async def test_sign_ups_up_to_the_limit_are_answered_normally(self, client: AsyncClient):
        for _ in range(5):
            response = await client.post("/users/register", json=_new_account())
            assert response.status_code == 201

    async def test_the_sign_up_past_the_limit_is_turned_away(self, client: AsyncClient):
        for _ in range(5):
            await client.post("/users/register", json=_new_account())

        response = await client.post("/users/register", json=_new_account())

        assert response.status_code == 429
        assert response.json() == {"detail": TOO_MANY_REGISTRATIONS}
        assert "retry-after" in response.headers


class TestRefreshIsNotTightened:
    async def test_refresh_outlasts_the_login_limit(self, client: AsyncClient):
        """A browser on a timer must not be throttled like a person typing a password.

        Eleven refreshes is past the login limit and nowhere near the global one, which is
        roughly what a few tabs open for a couple of hours look like. Each 401 is only the
        absent cookie — what matters is that none of them is a 429, because the frontend
        signs a user out on a 401 from here and a limit would make that happen for being
        busy rather than for being signed out.
        """
        for _ in range(11):
            response = await client.post("/users/refresh")
            assert response.status_code == 401
