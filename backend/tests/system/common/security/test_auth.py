import uuid

from httpx import AsyncClient

from app.common.security.security import create_access_token


class TestGetCurrentUser:
    """Any authenticated route will do — /campaigns/ is one that sits at the top level
    rather than under a path parameter, so a rejected token is the only reason it can
    answer 401."""

    async def test_malformed_token_returns_401(self, client: AsyncClient):
        response = await client.get("/campaigns/", headers={"Authorization": "Bearer not-a-valid-token"})

        assert response.status_code == 401

    async def test_token_for_unknown_user_returns_401(self, client: AsyncClient):
        token = create_access_token(subject=str(uuid.uuid4()))

        response = await client.get("/campaigns/", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
