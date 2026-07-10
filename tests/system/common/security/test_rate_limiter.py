import pytest
from httpx import AsyncClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.common.security.rate_limiter import _limiter
from app.main import app


@pytest.fixture
async def rate_limited_client(client: AsyncClient):
    app.state.limiter = Limiter(key_func=get_remote_address, default_limits=["2/minute"])  # type: ignore[attr-defined]
    yield client
    app.state.limiter = _limiter  # type: ignore[attr-defined]


class TestRateLimiter:
    async def test_requests_within_limit_succeed(self, rate_limited_client: AsyncClient):
        assert (await rate_limited_client.get("/health")).status_code == 200
        assert (await rate_limited_client.get("/health")).status_code == 200

    async def test_request_exceeding_limit_returns_429(self, rate_limited_client: AsyncClient):
        await rate_limited_client.get("/health")
        await rate_limited_client.get("/health")

        response = await rate_limited_client.get("/health")

        assert response.status_code == 429