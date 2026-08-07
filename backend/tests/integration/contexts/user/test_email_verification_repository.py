import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import SessionId, UserId
from app.contexts.user.adapters.secondary.persistence.email_verification_repository import (
    SqlAlchemyEmailVerificationRepository,
)
from app.contexts.user.domain.email_verification import EmailVerification


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyEmailVerificationRepository:
    return SqlAlchemyEmailVerificationRepository(db)


def a_verification(
    user_id: UserId | None = None,
    session_id: SessionId | None = None,
    token_hash: str = "hash",
    created_at: datetime | None = None,
) -> EmailVerification:
    return EmailVerification(
        user_id=user_id or UserId(uuid.uuid4()),
        session_id=session_id or SessionId(uuid.uuid4()),
        token_hash=token_hash,
        created_at=created_at or datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )


class TestSave:
    async def test_round_trips(self, repository: SqlAlchemyEmailVerificationRepository):
        verification = a_verification(token_hash="round-trip")

        await repository.save(verification)
        found = await repository.find_by_hash("round-trip")

        assert found is not None
        assert found.id == verification.id
        assert found.user_id == verification.user_id
        assert found.session_id == verification.session_id
        assert found.used_at is None

    async def test_saving_again_records_the_use_rather_than_inserting(
        self, repository: SqlAlchemyEmailVerificationRepository
    ):
        """Spending a link saves the same row back. An insert-only save would collide on
        the primary key and turn following a valid link into a 500."""
        verification = a_verification(token_hash="spent")
        await repository.save(verification)

        verification.use(datetime.now(UTC))
        await repository.save(verification)

        found = await repository.find_by_hash("spent")
        assert found is not None
        assert found.is_used is True

    async def test_returns_none_for_an_unknown_hash(self, repository: SqlAlchemyEmailVerificationRepository):
        assert await repository.find_by_hash("never-issued") is None


class TestCountForSession:
    async def test_counts_only_this_session(self, repository: SqlAlchemyEmailVerificationRepository):
        """The re-send cap is this number, which is why nothing stores a counter."""
        mine = SessionId(uuid.uuid4())
        await repository.save(a_verification(session_id=mine, token_hash="a"))
        await repository.save(a_verification(session_id=mine, token_hash="b"))
        await repository.save(a_verification(token_hash="someone-else"))

        assert await repository.count_for_session(mine) == 2

    async def test_a_fresh_session_starts_at_zero(self, repository: SqlAlchemyEmailVerificationRepository):
        assert await repository.count_for_session(SessionId(uuid.uuid4())) == 0


class TestLastSentAt:
    async def test_returns_the_most_recent_send_for_the_account(
        self, repository: SqlAlchemyEmailVerificationRepository
    ):
        user = UserId(uuid.uuid4())
        older = datetime.now(UTC) - timedelta(hours=1)
        newer = datetime.now(UTC)
        await repository.save(a_verification(user_id=user, token_hash="older", created_at=older))
        await repository.save(a_verification(user_id=user, token_hash="newer", created_at=newer))

        found = await repository.last_sent_at(user)

        assert found is not None
        assert abs((found - newer).total_seconds()) < 1

    async def test_ignores_sessions_entirely(self, repository: SqlAlchemyEmailVerificationRepository):
        """Keyed on the account, not the session — otherwise signing out and back in would
        clear the cooldown as well as the cap, and the two together would stop nothing."""
        user = UserId(uuid.uuid4())
        await repository.save(a_verification(user_id=user, session_id=SessionId(uuid.uuid4()), token_hash="one"))

        assert await repository.last_sent_at(user) is not None

    async def test_returns_none_for_an_account_never_emailed(self, repository: SqlAlchemyEmailVerificationRepository):
        assert await repository.last_sent_at(UserId(uuid.uuid4())) is None
