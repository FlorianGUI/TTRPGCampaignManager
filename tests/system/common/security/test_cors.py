import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.common.security.cors import setup_cors


@pytest.fixture
async def cors_client():
    app = FastAPI()
    setup_cors(app)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


class TestCors:
    async def test_allowed_origin_preflight_is_approved(self, cors_client: AsyncClient):
        response = await cors_client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    async def test_disallowed_origin_preflight_is_rejected(self, cors_client: AsyncClient):
        response = await cors_client.options(
            "/",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers


class TestCorsCustomOrigins:
    async def test_env_var_overrides_default_origins(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://example.com")
        app = FastAPI()
        setup_cors(app)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            allowed = await ac.options(
                "/",
                headers={"Origin": "http://example.com", "Access-Control-Request-Method": "GET"},
            )
            default_no_longer_allowed = await ac.options(
                "/",
                headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
            )

        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == "http://example.com"
        assert default_no_longer_allowed.status_code == 400
