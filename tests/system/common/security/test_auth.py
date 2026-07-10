import uuid

from httpx import AsyncClient

from app.contexts.user.application.security import create_access_token


class TestGetCurrentUser:
    async def test_malformed_token_returns_401(self, client: AsyncClient):
        response = await client.get("/characters/", headers={"Authorization": "Bearer not-a-valid-token"})

        assert response.status_code == 401

    async def test_token_for_unknown_user_returns_401(self, client: AsyncClient):
        token = create_access_token(subject=str(uuid.uuid4()))

        response = await client.get("/characters/", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
