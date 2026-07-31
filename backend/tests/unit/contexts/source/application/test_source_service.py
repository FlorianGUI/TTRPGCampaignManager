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

    async def find_by_id_for(self, id: UUID, owner_id: UUID) -> Source | None:
        source = self._store.get(id)
        if source is None or source.owner_id != owner_id:
            return None
        return source

    async def find_all_for(self, owner_id: UUID) -> list[Source]:
        return [s for s in self._store.values() if s.owner_id == owner_id]


@pytest.fixture
def service():
    return SourceService(FakeSourceRepository())


@pytest.fixture
def owner_id():
    return uuid.uuid4()


@pytest.fixture
def someone_else():
    return uuid.uuid4()


class TestCreate:
    async def test_returns_source_with_correct_fields(self, service: SourceService, owner_id: UUID):
        source = await service.create("SRD 5.1", owner_id)

        assert source.title == "SRD 5.1"
        assert source.owner_id == owner_id

    async def test_assigns_an_id(self, service: SourceService, owner_id: UUID):
        source = await service.create("SRD 5.1", owner_id)

        assert source.id is not None

    async def test_gives_each_source_its_own_id(self, service: SourceService, owner_id: UUID):
        first = await service.create("SRD 5.1", owner_id)
        second = await service.create("Fen Wardens notes", owner_id)

        assert first.id != second.id


class TestGetFor:
    async def test_returns_source_when_found(self, service: SourceService, owner_id: UUID):
        created = await service.create("SRD 5.1", owner_id)

        found = await service.get_for(created.id, owner_id)

        assert found == created

    async def test_returns_none_when_not_found(self, service: SourceService, owner_id: UUID):
        result = await service.get_for(uuid.uuid4(), owner_id)

        assert result is None

    async def test_returns_none_when_owned_by_someone_else(
        self, service: SourceService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("SRD 5.1", owner_id)

        result = await service.get_for(created.id, someone_else)

        assert result is None


class TestListFor:
    async def test_returns_empty_list_when_no_sources(self, service: SourceService, owner_id: UUID):
        result = await service.list_for(owner_id)

        assert result == []

    async def test_returns_the_sources_of_that_owner(self, service: SourceService, owner_id: UUID):
        await service.create("SRD 5.1", owner_id)
        await service.create("Fen Wardens notes", owner_id)

        result = await service.list_for(owner_id)

        assert len(result) == 2

    async def test_leaves_out_the_sources_of_other_owners(
        self, service: SourceService, owner_id: UUID, someone_else: UUID
    ):
        await service.create("SRD 5.1", owner_id)
        await service.create("Xanathars Guide", someone_else)

        result = await service.list_for(owner_id)

        assert [s.title for s in result] == ["SRD 5.1"]


class TestRename:
    async def test_returns_the_source_with_its_new_title(self, service: SourceService, owner_id: UUID):
        created = await service.create("SRD 5.0", owner_id)

        renamed = await service.rename(created.id, owner_id, "SRD 5.1")

        assert renamed is not None
        assert renamed.title == "SRD 5.1"

    async def test_keeps_the_new_title(self, service: SourceService, owner_id: UUID):
        created = await service.create("SRD 5.0", owner_id)

        await service.rename(created.id, owner_id, "SRD 5.1")

        found = await service.get_for(created.id, owner_id)
        assert found is not None
        assert found.title == "SRD 5.1"

    async def test_returns_none_when_not_found(self, service: SourceService, owner_id: UUID):
        result = await service.rename(uuid.uuid4(), owner_id, "SRD 5.1")

        assert result is None

    async def test_returns_none_when_owned_by_someone_else(
        self, service: SourceService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("SRD 5.0", owner_id)

        result = await service.rename(created.id, someone_else, "SRD 5.1")

        assert result is None

    async def test_leaves_a_source_owned_by_someone_else_untouched(
        self, service: SourceService, owner_id: UUID, someone_else: UUID
    ):
        created = await service.create("SRD 5.0", owner_id)

        await service.rename(created.id, someone_else, "SRD 5.1")

        found = await service.get_for(created.id, owner_id)
        assert found is not None
        assert found.title == "SRD 5.0"
