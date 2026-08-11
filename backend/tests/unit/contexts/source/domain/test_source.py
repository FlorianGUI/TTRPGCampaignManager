import uuid
from datetime import UTC, datetime

from app.common.ids import UserId
from app.contexts.source.domain.source import Source

LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)


class TestSource:
    def test_knows_when_it_was_made_the_moment_it_exists(self):
        source = Source(title="SRD 5.1", owner_id=UserId(uuid.uuid4()))

        assert source.created_at.tzinfo is not None
        assert source.updated_at.tzinfo is not None

    def test_revising_moves_the_updated_time(self):
        source = Source(title="SRD", owner_id=UserId(uuid.uuid4()))
        source.updated_at = LONG_AGO

        source.revise("SRD 5.1")

        assert source.updated_at > LONG_AGO

    def test_revising_leaves_the_created_time_alone(self):
        source = Source(title="SRD", owner_id=UserId(uuid.uuid4()))
        source.created_at = LONG_AGO

        source.revise("SRD 5.1")

        assert source.created_at == LONG_AGO

    def test_revising_retitles_the_source(self):
        source = Source(title="SRD", owner_id=UserId(uuid.uuid4()))

        source.revise("SRD 5.1")

        assert source.title == "SRD 5.1"
