import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.source.adapters.secondary.persistence.source_model import SourceModel
from app.contexts.source.adapters.secondary.persistence.source_repository import SqlAlchemySourceRepository
from app.contexts.source.domain.source import Source


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemySourceRepository:
    return SqlAlchemySourceRepository(db)


@pytest.fixture
def owner_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def someone_else() -> uuid.UUID:
    return uuid.uuid4()


class TestSave:
    async def test_returns_the_saved_source(self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID):
        source = Source(title="SRD 5.1", owner_id=owner_id)

        result = await repository.save(source)

        assert result == source

    async def test_persists_source(self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID):
        source = Source(title="SRD 5.1", owner_id=owner_id)
        await repository.save(source)

        found = await repository.find_by_id_for(source.id, owner_id)

        assert found is not None
        assert found.title == "SRD 5.1"
        assert found.owner_id == owner_id

    async def test_updates_a_source_that_was_already_saved(
        self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID
    ):
        source = Source(title="SRD 5.0", owner_id=owner_id)
        await repository.save(source)

        source.title = "SRD 5.1"
        await repository.save(source)

        found = await repository.find_by_id_for(source.id, owner_id)
        assert found is not None
        assert found.title == "SRD 5.1"


class TestFindByIdFor:
    async def test_returns_source_when_found(self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID):
        source = Source(title="Fen Wardens notes", owner_id=owner_id)
        await repository.save(source)

        result = await repository.find_by_id_for(source.id, owner_id)

        assert result is not None
        assert result.id == source.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID):
        result = await repository.find_by_id_for(uuid.uuid4(), owner_id)

        assert result is None

    async def test_returns_none_when_owned_by_someone_else(
        self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID, someone_else: uuid.UUID
    ):
        source = Source(title="Xanathars Guide", owner_id=owner_id)
        await repository.save(source)

        result = await repository.find_by_id_for(source.id, someone_else)

        assert result is None


class TestFindAllFor:
    async def test_returns_the_sources_of_that_owner(self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID):
        await repository.save(Source(title="SRD 5.1", owner_id=owner_id))
        await repository.save(Source(title="Dragon Magazine issue 4", owner_id=owner_id))

        results = await repository.find_all_for(owner_id)
        titles = [s.title for s in results]

        assert "SRD 5.1" in titles
        assert "Dragon Magazine issue 4" in titles

    async def test_leaves_out_the_sources_of_other_owners(
        self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID, someone_else: uuid.UUID
    ):
        await repository.save(Source(title="SRD 5.1", owner_id=owner_id))
        await repository.save(Source(title="Xanathars Guide", owner_id=someone_else))

        results = await repository.find_all_for(owner_id)

        assert [s.title for s in results] == ["SRD 5.1"]


class TestDeleteFor:
    async def test_removes_the_source(self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID):
        source = Source(title="SRD 5.1", owner_id=owner_id)
        await repository.save(source)

        await repository.delete_for(source.id, owner_id)

        assert await repository.find_by_id_for(source.id, owner_id) is None

    async def test_leaves_the_rest_of_the_library_alone(
        self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID
    ):
        doomed = Source(title="SRD 5.1", owner_id=owner_id)
        await repository.save(doomed)
        await repository.save(Source(title="Monster Manual", owner_id=owner_id))

        await repository.delete_for(doomed.id, owner_id)

        assert [s.title for s in await repository.find_all_for(owner_id)] == ["Monster Manual"]

    async def test_deleting_an_unknown_id_is_not_an_error(
        self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID
    ):
        await repository.delete_for(uuid.uuid4(), owner_id)

    async def test_leaves_a_source_owned_by_someone_else_standing(
        self, repository: SqlAlchemySourceRepository, owner_id: uuid.UUID, someone_else: uuid.UUID
    ):
        source = Source(title="Xanathars Guide", owner_id=someone_else)
        await repository.save(source)

        await repository.delete_for(source.id, owner_id)

        assert await repository.find_by_id_for(source.id, someone_else) is not None


class TestTheQueryAgreesWithTheDomainRule:
    """Holds `find_all_for` and `Source.is_visible_to` to the same answer.

    The campaign context has the twin of this test, and for the same reason: the rule is
    written once in SQL and once in Python, and only this holds the two together.
    """

    async def test_returns_exactly_the_rows_the_domain_rule_accepts(
        self,
        repository: SqlAlchemySourceRepository,
        db: AsyncSession,
        owner_id: uuid.UUID,
        someone_else: uuid.UUID,
    ):
        await repository.save(Source(title="SRD 5.1", owner_id=owner_id))
        await repository.save(Source(title="Monster Manual", owner_id=owner_id))
        await repository.save(Source(title="Xanathars Guide", owner_id=someone_else))

        queried = await repository.find_all_for(owner_id)
        every_row = (await db.execute(select(SourceModel))).scalars().all()
        allowed = [m for m in every_row if Source(title=m.title, owner_id=m.owner_id, id=m.id).is_visible_to(owner_id)]

        assert sorted(s.id for s in queried) == sorted(m.id for m in allowed)
