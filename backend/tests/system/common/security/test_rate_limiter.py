import uuid

import pytest
from httpx import AsyncClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.common.security.rate_limiter import (
    GLOBAL_RATE_LIMIT,
    TOO_MANY_LOGIN_ATTEMPTS,
    TOO_MANY_REFRESHES,
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
        absent cookie — what matters is that none of them is a 429, and that matters more
        since #68 rather than less: the frontend now ends the session on a 429 here, so
        every request this limit refuses is somebody signed out. The route carries the
        global number written out; if anyone ever swaps it for a tighter one, this fails.
        """
        for _ in range(11):
            response = await client.post("/users/refresh")
            assert response.status_code == 401


class TestRefreshRateLimit:
    """The global number, but not the global message.

    A 429 here is the one rate-limit answer a signed-in person reads, because it ends their
    session and they meet it on the login page they are then sent to (#68). Left on the
    inherited default slowapi has no sentence to give and answers `{"detail": "100 per 1
    minute"}` — unreadable, and the limit recited back to whoever just probed for it. This
    is what stops that quietly returning.
    """

    async def test_past_the_global_limit_it_answers_in_a_sentence(self, client: AsyncClient):
        # Every one of these is the plain "no cookie" 401 — the limiter counts attempts,
        # not sessions, so nothing here needs to be signed in to reach the limit.
        for _ in range(int(GLOBAL_RATE_LIMIT.split("/")[0])):
            assert (await client.post("/users/refresh")).status_code == 401

        response = await client.post("/users/refresh")

        assert response.status_code == 429
        assert response.json() == {"detail": TOO_MANY_REFRESHES}
        # The frontend tells the user how long to wait with this, and CORS exposes it for
        # exactly that (`cors.py`). A message with no number is a user retrying at once.
        assert "retry-after" in response.headers


class TestForgotPasswordRateLimit:
    """The limiter is *on* here, which is the whole point of these living in tests/system.

    Acceptance turns it off so scenarios cannot trip it, and that blindness has teeth: a
    `@limiter.limit` decorator does work on every call, not only on a throttled one, and
    an endpoint that does not satisfy it fails on the first request rather than the sixth.
    That is exactly what happened to `/users/forgot-password` — slowapi writes its headers
    into a `Response` parameter and raises when the signature has none, so every call was
    a 500 and no acceptance scenario could see it.
    """

    async def test_an_ordinary_request_is_answered_normally(self, client: AsyncClient):
        response = await client.post("/users/forgot-password", json={"identifier": "nobody-at-all"})

        assert response.status_code == 204

    async def test_still_answers_the_same_way_for_an_account_that_exists(self, client: AsyncClient):
        account = _new_account()
        await client.post("/users/register", json=account)

        response = await client.post("/users/forgot-password", json={"identifier": account["username"]})

        assert response.status_code == 204

    async def test_past_the_limit_it_says_so_without_saying_anything_else(self, rate_limited_client: AsyncClient):
        """Two calls is the whole budget for this client, so the third is refused — and the
        refusal says nothing about whether any of them matched an account."""
        await rate_limited_client.post("/users/forgot-password", json={"identifier": "nobody-at-all"})
        await rate_limited_client.post("/users/forgot-password", json={"identifier": "nobody-at-all"})

        response = await rate_limited_client.post("/users/forgot-password", json={"identifier": "nobody-at-all"})

        assert response.status_code == 429
        assert "nobody-at-all" not in response.text
