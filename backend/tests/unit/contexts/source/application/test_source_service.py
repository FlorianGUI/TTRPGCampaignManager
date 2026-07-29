import uuid
from uuid import UUID

import pytest

from app.contexts.source.application.source_service import SourceService
from app.contexts.source.domain.ports.source_repository import SourceRepository
from app.contexts.source.domain.source import Source


class FakeSourceRepository(SourceRepository):
    def __init__(self):
        self._store: dict[UUID, Source] = {}

    async def save(self, source: Source) -> Source:
        self._store[source.id] = source
        return source

    async def find_by_id(self, id: UUID) -> Source | None:
        return self._store.get(id)

    async def find_all(self) -> list[Source]:
        return list(self._store.values())


@pytest.fixture
def service():
    return SourceService(FakeSourceRepository())


class TestCreate:
    async def test_returns_source_with_correct_fields(self, service: SourceService):
        owner_id = uuid.uuid4()

        source = await service.create("SRD 5.1", owner_id)

        assert source.title == "SRD 5.1"
        assert source.owner_id == owner_id

    async def test_assigns_an_id(self, service: SourceService):
        source = await service.create("SRD 5.1", uuid.uuid4())

        assert source.id is not None

    async def test_gives_each_source_its_own_id(self, service: SourceService):
        owner_id = uuid.uuid4()

        first = await service.create("SRD 5.1", owner_id)
        second = await service.create("Fen Wardens notes", owner_id)

        assert first.id != second.id


class TestGet:
    async def test_returns_source_when_found(self, service: SourceService):
        created = await service.create("SRD 5.1", uuid.uuid4())

        found = await service.get(created.id)

        assert found == created

    async def test_returns_none_when_not_found(self, service: SourceService):
        result = await service.get(uuid.uuid4())

        assert result is None


class TestListAll:
    async def test_returns_empty_list_when_no_sources(self, service: SourceService):
        result = await service.list_all()

        assert result == []

    async def test_returns_all_created_sources(self, service: SourceService):
        owner_id = uuid.uuid4()
        await service.create("SRD 5.1", owner_id)
        await service.create("Fen Wardens notes", owner_id)

        result = await service.list_all()

        assert len(result) == 2
