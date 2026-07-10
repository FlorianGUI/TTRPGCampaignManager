from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestHealthRoutes:
    async def test_root_responds(self, client: AsyncClient):
        response = await client.get("/")
        assert response.status_code == 200

    async def test_openapi_schema_available(self, client: AsyncClient):
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        assert response.json()["info"]["title"] == "D&D Character Sheet Creator"

    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "connected"}


class TestDbConnection:
    async def test_session_executes_query(self, db: AsyncSession):
        result = await db.execute(text("SELECT 1 AS value"))
        assert result.one().value == 1

    async def test_session_reuses_same_backend_connection(self, db: AsyncSession):
        pid_1 = (await db.execute(text("SELECT pg_backend_pid() AS pid"))).one().pid
        pid_2 = (await db.execute(text("SELECT pg_backend_pid() AS pid"))).one().pid
        assert pid_1 == pid_2
