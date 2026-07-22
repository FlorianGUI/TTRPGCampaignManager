import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db


class TestGetDb:
    async def test_yields_a_working_session_and_closes_it_afterwards(self):
        gen = get_db()
        session = await anext(gen)

        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1 AS value"))
        assert result.one().value == 1

        with pytest.raises(StopAsyncIteration):
            await anext(gen)
