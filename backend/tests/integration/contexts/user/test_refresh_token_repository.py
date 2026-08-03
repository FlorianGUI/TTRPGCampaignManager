import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import SessionId, UserId
from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.contexts.user.domain.refresh_token import RefreshToken

NOW = datetime.now(UTC).replace(microsecond=0)


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemyRefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(db)


@pytest.fixture
def session_id() -> SessionId:
    return SessionId(uuid.uuid4())


def a_token(session_id: SessionId, hash: str, revoked_at: datetime | None = None) -> RefreshToken:
    return RefreshToken(
        user_id=UserId(uuid.uuid4()),
        session_id=session_id,
        token_hash=hash,
        expires_at=NOW + timedelta(days=30),
        revoked_at=revoked_at,
    )


class TestSave:
    async def test_returns_the_saved_token(self, repository: SqlAlchemyRefreshTokenRepository, session_id: SessionId):
        token = a_token(session_id, hash="a" * 64)

        result = await repository.save(token)

        assert result == token

    async def test_persists_every_field(self, repository: SqlAlchemyRefreshTokenRepository, session_id: SessionId):
        token = a_token(session_id, hash="b" * 64)
        await repository.save(token)

        found = await repository.find_by_hash("b" * 64)

        assert found == token

    async def test_the_deadline_comes_back_aware(
        self, repository: SqlAlchemyRefreshTokenRepository, session_id: SessionId
    ):
        """Expiry is compared against `datetime.now(UTC)`, and a naive value raises there.

        The column says `timezone=True`; this is the test that notices if it ever stops
        saying so, because nothing else would until a refresh blew up in production.
        """
        await repository.save(a_token(session_id, hash="c" * 64))

        found = await repository.find_by_hash("c" * 64)

        assert found is not None
        assert found.expires_at.tzinfo is not None
        assert found.expires_at == NOW + timedelta(days=30)

    async def test_saving_again_records_that_the_token_was_spent(
        self, repository: SqlAlchemyRefreshTokenRepository, session_id: SessionId
    ):
        """Rotation saves a token that already exists. An insert-only save would fail here."""
        token = a_token(session_id, hash="d" * 64)
        await repository.save(token)

        token.revoke(NOW)
        await repository.save(token)

        found = await repository.find_by_hash("d" * 64)
        assert found is not None
        assert found.revoked_at == NOW


class TestFindByHash:
    async def test_returns_none_for_a_hash_nobody_stored(self, repository: SqlAlchemyRefreshTokenRepository):
        assert await repository.find_by_hash("e" * 64) is None

    async def test_returns_a_revoked_token_rather_than_hiding_it(
        self, repository: SqlAlchemyRefreshTokenRepository, session_id: SessionId
    ):
        """Reuse detection depends on this. A repository that filtered the dead ones out
        would turn the one signal a leak gives off into an ordinary "no such token"."""
        await repository.save(a_token(session_id, hash="f" * 64, revoked_at=NOW))

        found = await repository.find_by_hash("f" * 64)

        assert found is not None
        assert found.is_revoked


class TestRevokeSession:
    async def test_revokes_every_token_in_the_session(
        self, repository: SqlAlchemyRefreshTokenRepository, session_id: SessionId
    ):
        await repository.save(a_token(session_id, hash="1" * 64))
        await repository.save(a_token(session_id, hash="2" * 64))

        await repository.revoke_session(session_id, NOW)

        for hash in ("1" * 64, "2" * 64):
            found = await repository.find_by_hash(hash)
            assert found is not None
            assert found.revoked_at == NOW

    async def test_leaves_other_sessions_alone(
        self, repository: SqlAlchemyRefreshTokenRepository, session_id: SessionId
    ):
        await repository.save(a_token(session_id, hash="3" * 64))
        await repository.save(a_token(SessionId(uuid.uuid4()), hash="4" * 64))

        await repository.revoke_session(session_id, NOW)

        untouched = await repository.find_by_hash("4" * 64)
        assert untouched is not None
        assert not untouched.is_revoked

    async def test_keeps_the_moment_an_already_revoked_token_stopped_working(
        self, repository: SqlAlchemyRefreshTokenRepository, session_id: SessionId
    ):
        """Sweeping a session must not rewrite when its rotated-away tokens were spent."""
        spent_at = NOW - timedelta(hours=2)
        await repository.save(a_token(session_id, hash="5" * 64, revoked_at=spent_at))

        await repository.revoke_session(session_id, NOW)

        found = await repository.find_by_hash("5" * 64)
        assert found is not None
        assert found.revoked_at == spent_at

    async def test_a_session_with_nothing_in_it_is_no_trouble(self, repository: SqlAlchemyRefreshTokenRepository):
        await repository.revoke_session(SessionId(uuid.uuid4()), NOW)
