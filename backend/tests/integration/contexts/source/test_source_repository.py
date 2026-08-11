import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import SourceId, UserId
from app.contexts.source.adapters.secondary.persistence.source_model import SourceModel
from app.contexts.source.adapters.secondary.persistence.source_repository import SqlAlchemySourceRepository
from app.contexts.source.domain.source import Source, SourceAccess


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemySourceRepository:
    return SqlAlchemySourceRepository(db)


@pytest.fixture
def owner_id() -> UserId:
    return UserId(uuid.uuid4())


@pytest.fixture
def someone_else() -> UserId:
    return UserId(uuid.uuid4())


class TestSave:
    async def test_returns_the_saved_source(self, repository: SqlAlchemySourceRepository, owner_id: UserId):
        source = Source(title="SRD 5.1", owner_id=owner_id)

        result = await repository.save(source)

        assert result == source

    async def test_persists_source(self, repository: SqlAlchemySourceRepository, owner_id: UserId):
        source = Source(title="SRD 5.1", owner_id=owner_id)
        await repository.save(source)

        found = (await repository.find_by_id(source.id)).unchecked

        assert found is not None
        assert found.title == "SRD 5.1"
        assert found.owner_id == owner_id

    async def test_updates_a_source_that_was_already_saved(
        self, repository: SqlAlchemySourceRepository, owner_id: UserId
    ):
        source = Source(title="SRD 5.0", owner_id=owner_id)
        await repository.save(source)

        source.title = "SRD 5.1"
        await repository.save(source)

        found = (await repository.find_by_id(source.id)).unchecked
        assert found is not None
        assert found.title == "SRD 5.1"


class TestFindById:
    async def test_returns_source_when_found(self, repository: SqlAlchemySourceRepository, owner_id: UserId):
        source = Source(title="Fen Wardens notes", owner_id=owner_id)
        await repository.save(source)

        result = (await repository.find_by_id(source.id)).unchecked

        assert result is not None
        assert result.id == source.id

    async def test_returns_none_for_unknown_id(self, repository: SqlAlchemySourceRepository):
        assert (await repository.find_by_id(SourceId(uuid.uuid4()))).unchecked is None

    async def test_finds_a_source_whoever_owns_it(self, repository: SqlAlchemySourceRepository, someone_else: UserId):
        """Ownership moved to `source.readable`; this method only reports existence."""
        source = Source(title="Xanathars Guide", owner_id=someone_else)
        await repository.save(source)

        assert (await repository.find_by_id(source.id)).unchecked is not None


class TestFindAllFor:
    async def test_returns_the_sources_of_that_owner(self, repository: SqlAlchemySourceRepository, owner_id: UserId):
        await repository.save(Source(title="SRD 5.1", owner_id=owner_id))
        await repository.save(Source(title="Dragon Magazine issue 4", owner_id=owner_id))

        results = await repository.find_all_for(owner_id)
        titles = [s.title for s in results]

        assert "SRD 5.1" in titles
        assert "Dragon Magazine issue 4" in titles

    async def test_leaves_out_the_sources_of_other_owners(
        self, repository: SqlAlchemySourceRepository, owner_id: UserId, someone_else: UserId
    ):
        await repository.save(Source(title="SRD 5.1", owner_id=owner_id))
        await repository.save(Source(title="Xanathars Guide", owner_id=someone_else))

        results = await repository.find_all_for(owner_id)

        assert [s.title for s in results] == ["SRD 5.1"]


class TestDelete:
    async def test_removes_the_source(self, repository: SqlAlchemySourceRepository, owner_id: UserId):
        source = Source(title="SRD 5.1", owner_id=owner_id)
        await repository.save(source)

        await repository.delete(source.id)

        assert (await repository.find_by_id(source.id)).unchecked is None

    async def test_leaves_the_rest_of_the_library_alone(self, repository: SqlAlchemySourceRepository, owner_id: UserId):
        doomed = Source(title="SRD 5.1", owner_id=owner_id)
        await repository.save(doomed)
        await repository.save(Source(title="Monster Manual", owner_id=owner_id))

        await repository.delete(doomed.id)

        assert [s.title for s in await repository.find_all_for(owner_id)] == ["Monster Manual"]

    async def test_deleting_an_unknown_id_is_not_an_error(self, repository: SqlAlchemySourceRepository):
        await repository.delete(SourceId(uuid.uuid4()))


class TestTheQueryAgreesWithTheDomainRule:
    """Holds `find_all_for` and `SourceAccess.may_read` to the same answer.

    The campaign context has the twin of this test, and for the same reason: the rule is
    written once in SQL and once in Python, and only this holds the two together.
    """

    async def test_returns_exactly_the_rows_the_domain_rule_accepts(
        self,
        repository: SqlAlchemySourceRepository,
        db: AsyncSession,
        owner_id: UserId,
        someone_else: UserId,
    ):
        await repository.save(Source(title="SRD 5.1", owner_id=owner_id))
        await repository.save(Source(title="Monster Manual", owner_id=owner_id))
        await repository.save(Source(title="Xanathars Guide", owner_id=someone_else))

        queried = await repository.find_all_for(owner_id)
        every_row = (await db.execute(select(SourceModel))).scalars().all()
        access = SourceAccess(owner_id)
        allowed = [
            m
            for m in every_row
            if access.may_read(Source(title=m.title, owner_id=UserId(m.owner_id), id=SourceId(m.id)))
        ]

        assert sorted(s.id for s in queried) == sorted(m.id for m in allowed)


class TestTimestamps:
    """The merge() hazard again, in the second of the three repositories that has it."""

    async def test_saving_a_second_time_does_not_erase_when_it_was_made(
        self, repository: SqlAlchemySourceRepository, owner_id: UserId
    ):
        source = Source(title="SRD", owner_id=owner_id)
        await repository.save(source)

        reloaded = (await repository.find_by_id(source.id)).unchecked
        assert reloaded is not None
        reloaded.revise("SRD 5.1")
        await repository.save(reloaded)

        found = (await repository.find_by_id(source.id)).unchecked

        assert found is not None
        assert found.created_at == source.created_at
        assert found.updated_at > source.updated_at


class TestOrdering:
    async def test_lists_the_most_recently_touched_source_first(
        self, repository: SqlAlchemySourceRepository, owner_id: UserId
    ):
        oldest = Source(title="Oldest", owner_id=owner_id, updated_at=datetime(2020, 1, 1, tzinfo=UTC))
        newest = Source(title="Newest", owner_id=owner_id, updated_at=datetime(2026, 1, 1, tzinfo=UTC))
        for source in (oldest, newest):
            await repository.save(source)

        found = await repository.find_all_for(owner_id)

        assert [s.title for s in found] == ["Newest", "Oldest"]

    async def test_breaks_a_tie_by_id(self, repository: SqlAlchemySourceRepository, owner_id: UserId):
        same_moment = datetime(2026, 1, 1, tzinfo=UTC)
        first = Source(id=SourceId(uuid.UUID(int=1)), title="First", owner_id=owner_id, updated_at=same_moment)
        second = Source(id=SourceId(uuid.UUID(int=2)), title="Second", owner_id=owner_id, updated_at=same_moment)
        await repository.save(second)
        await repository.save(first)

        found = await repository.find_all_for(owner_id)

        assert [s.title for s in found] == ["First", "Second"]
