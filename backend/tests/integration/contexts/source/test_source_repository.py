import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.source.adapters.secondary.persistence.source_repository import SqlAlchemySourceRepository
from app.contexts.source.domain.source import Source


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemySourceRepository:
    return SqlAlchemySourceRepository(db)


class TestSave:
    async def test_returns_the_saved_source(self, repository: SqlAlchemySourceRepository):
        source = Source(title="SRD 5.1", owner_id=uuid.uuid4())

        result = await repository.save(source)

        assert result == source

    async def test_persists_source(self, repository: SqlAlchemySourceRepository):
        owner_id = uuid.uuid4()
        source = Source(title="SRD 5.1", owner_id=owner_id)
        await repository.save(source)

        found = await repository.find_by_id(source.id)

        assert found is not None
        assert found.title == "SRD 5.1"
        assert found.owner_id == owner_id


class TestFindById:
    async def test_returns_source_when_found(self, repository: SqlAlchemySourceRepository):
        source = Source(title="Fen Wardens notes", owner_id=uuid.uuid4())
        await repository.save(source)

        result = await repository.find_by_id(source.id)

        assert result is not None
        assert result.id == source.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemySourceRepository):
        result = await repository.find_by_id(uuid.uuid4())

        assert result is None


class TestFindAll:
    async def test_returns_saved_sources(self, repository: SqlAlchemySourceRepository):
        owner_id = uuid.uuid4()
        await repository.save(Source(title="SRD 5.1", owner_id=owner_id))
        await repository.save(Source(title="Dragon Magazine issue 4", owner_id=owner_id))

        results = await repository.find_all()
        titles = [s.title for s in results]

        assert "SRD 5.1" in titles
        assert "Dragon Magazine issue 4" in titles
