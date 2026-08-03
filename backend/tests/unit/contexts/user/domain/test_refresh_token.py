import uuid
from datetime import UTC, datetime, timedelta

from app.common.ids import SessionId, UserId
from app.contexts.user.domain.refresh_token import RefreshToken


def a_token(expires_at: datetime, revoked_at: datetime | None = None) -> RefreshToken:
    return RefreshToken(
        user_id=UserId(uuid.uuid4()),
        session_id=SessionId(uuid.uuid4()),
        token_hash="0" * 64,
        expires_at=expires_at,
        revoked_at=revoked_at,
    )


NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


class TestExpiry:
    def test_a_token_past_its_deadline_has_expired(self):
        assert a_token(expires_at=NOW - timedelta(seconds=1)).has_expired(NOW)

    def test_a_token_before_its_deadline_has_not(self):
        assert not a_token(expires_at=NOW + timedelta(seconds=1)).has_expired(NOW)

    def test_the_deadline_itself_counts_as_expired(self):
        """Which way the boundary falls is arbitrary, but it should not drift by accident."""
        assert a_token(expires_at=NOW).has_expired(NOW)


class TestRevocation:
    def test_a_new_token_is_not_revoked(self):
        assert not a_token(expires_at=NOW).is_revoked

    def test_revoking_records_when(self):
        token = a_token(expires_at=NOW + timedelta(days=30))

        token.revoke(NOW)

        assert token.is_revoked
        assert token.revoked_at == NOW

    def test_revoking_twice_keeps_the_first_time(self):
        """Logging out revokes a whole session, including tokens rotation already retired.

        If the second revocation won, the moment a token stopped working would move
        forward every time something swept the session — and that moment is the only
        record of when the token was actually spent.
        """
        token = a_token(expires_at=NOW + timedelta(days=30))
        token.revoke(NOW)

        token.revoke(NOW + timedelta(hours=1))

        assert token.revoked_at == NOW
