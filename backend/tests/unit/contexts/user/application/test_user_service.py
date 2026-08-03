import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.common.ids import RefreshTokenId, SessionId, UserId
from app.common.security.security import create_access_token, decode_access_token, hash_refresh_token
from app.contexts.user.application.user_service import (
    InvalidCredentialsError,
    SessionNotRenewableError,
    UsernameAlreadyExistsError,
    UserService,
)
from app.contexts.user.domain.ports.refresh_token_repository import RefreshTokenRepository
from app.contexts.user.domain.ports.user_repository import UserRepository
from app.contexts.user.domain.refresh_token import RefreshToken
from app.contexts.user.domain.user import User


class FakeUserRepository(UserRepository):
    def __init__(self):
        self._store: dict[UUID, User] = {}

    async def save(self, user: User) -> User:
        self._store[user.id] = user
        return user

    async def find_by_id(self, id: UUID) -> User | None:
        return self._store.get(id)

    async def find_by_username(self, username: str) -> User | None:
        return next((u for u in self._store.values() if u.username == username), None)


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self):
        self._store: dict[RefreshTokenId, RefreshToken] = {}

    async def save(self, token: RefreshToken) -> RefreshToken:
        self._store[token.id] = token
        return token

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self._store.values() if t.token_hash == token_hash), None)

    async def revoke_session(self, session_id: SessionId, at: datetime) -> None:
        for token in self._store.values():
            if token.session_id == session_id:
                token.revoke(at)


@pytest.fixture
def users():
    return FakeUserRepository()


@pytest.fixture
def sessions():
    return FakeRefreshTokenRepository()


@pytest.fixture
def service(users: FakeUserRepository, sessions: FakeRefreshTokenRepository):
    return UserService(users, sessions)


async def stored(sessions: FakeRefreshTokenRepository, secret: str) -> RefreshToken:
    """The row behind a refresh token, found the way the service finds it."""
    token = await sessions.find_by_hash(hash_refresh_token(secret))
    assert token is not None
    return token


class TestRegister:
    async def test_saves_a_user_with_the_given_fields(self, service: UserService):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        user = await service.get_by_token(session.access_token)
        assert user.username == "aragorn"
        assert user.email == "aragorn@gondor.test"

    async def test_hashes_the_password(self, service: UserService):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        user = await service.get_by_token(session.access_token)
        assert user.hashed_password != "strider123"

    async def test_returns_a_token_that_signs_the_new_user_in(self, service: UserService):
        """The point of #33: no second call between signing up and being signed in."""
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        elsewhere = await service.authenticate("aragorn", "strider123")

        assert await service.get_by_token(session.access_token) == await service.get_by_token(elsewhere.access_token)

    async def test_starts_a_session_that_can_be_refreshed(self, service: UserService):
        """Signing up leaves the same thing behind as signing in, refresh token included.

        Without this, a brand new account would be the one session that could not survive
        a page reload — and it would be found by a person, not a test.
        """
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        renewed = await service.refresh(session.refresh_token)

        assert decode_access_token(renewed.access_token) == decode_access_token(session.access_token)

    async def test_raises_when_username_already_exists(self, service: UserService):
        await service.register("aragorn", "aragorn@gondor.test", "strider123")

        with pytest.raises(UsernameAlreadyExistsError):
            await service.register("aragorn", "other@gondor.test", "otherpass")


class TestAuthenticate:
    async def test_returns_a_valid_token_for_correct_credentials(self, service: UserService):
        registered = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        user = await service.get_by_token(registered.access_token)

        session = await service.authenticate("aragorn", "strider123")

        assert decode_access_token(session.access_token) == str(user.id)

    async def test_starts_a_session_of_its_own(self, service: UserService, sessions: FakeRefreshTokenRepository):
        """Signing in on a second device must not join the session the first one holds.

        If they shared one, logging out anywhere would log out everywhere — which somebody
        might want as a feature, but not one that should arrive by accident because two
        sign-ins were indistinguishable.
        """
        first = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        second = await service.authenticate("aragorn", "strider123")

        assert (await stored(sessions, first.refresh_token)).session_id != (
            await stored(sessions, second.refresh_token)
        ).session_id

    async def test_raises_for_wrong_password(self, service: UserService):
        await service.register("aragorn", "aragorn@gondor.test", "strider123")

        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("aragorn", "wrongpass")

    async def test_raises_for_unknown_username(self, service: UserService):
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("unknown", "whatever")


class TestWhatIsStored:
    async def test_the_token_itself_is_never_written_down(
        self, service: UserService, sessions: FakeRefreshTokenRepository
    ):
        """A database dump should not be a drawer full of live sessions."""
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        held = [token.token_hash for token in sessions._store.values()]

        assert session.refresh_token not in held
        assert held == [hash_refresh_token(session.refresh_token)]

    async def test_the_session_carries_the_deadline_it_was_stored_with(
        self, service: UserService, sessions: FakeRefreshTokenRepository
    ):
        """The cookie's lifetime comes from this, so the two have to be the same date."""
        issued_at = datetime.now(UTC)

        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        assert (await stored(sessions, session.refresh_token)).expires_at == session.expires_at
        assert session.expires_at > issued_at


class TestRefresh:
    async def test_returns_a_working_access_token_for_the_same_user(self, service: UserService):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        renewed = await service.refresh(session.refresh_token)

        assert (await service.get_by_token(renewed.access_token)).username == "aragorn"

    async def test_hands_out_a_different_refresh_token(self, service: UserService):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        renewed = await service.refresh(session.refresh_token)

        assert renewed.refresh_token != session.refresh_token

    async def test_the_replacement_stays_in_the_same_session(
        self, service: UserService, sessions: FakeRefreshTokenRepository
    ):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        renewed = await service.refresh(session.refresh_token)

        assert (await stored(sessions, renewed.refresh_token)).session_id == (
            await stored(sessions, session.refresh_token)
        ).session_id

    async def test_the_deadline_does_not_move(self, service: UserService):
        """The thirty days run from signing in, not from the last thing that happened.

        A sliding window would keep a stolen session alive for as long as the thief kept
        refreshing it, which is the one thing an absolute window is there to stop.
        """
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        renewed = await service.refresh(session.refresh_token)

        assert renewed.expires_at == session.expires_at

    async def test_the_spent_token_stops_working(self, service: UserService):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        await service.refresh(session.refresh_token)

        with pytest.raises(SessionNotRenewableError):
            await service.refresh(session.refresh_token)

    async def test_replaying_a_spent_token_kills_the_whole_session(self, service: UserService):
        """The security-critical path, and the reason rotation is worth having at all.

        Holding a token that has already been spent means the secret reached two pairs of
        hands. Refusing only the replay would leave whoever else has a copy refreshing
        happily from the token the first use produced, so the session goes in its entirety
        and both parties have to sign in again.
        """
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        renewed = await service.refresh(session.refresh_token)

        with pytest.raises(SessionNotRenewableError):
            await service.refresh(session.refresh_token)

        with pytest.raises(SessionNotRenewableError):
            await service.refresh(renewed.refresh_token)

    async def test_a_replay_leaves_other_sessions_alone(self, service: UserService):
        """The blast radius is one session, not the account.

        Revoking everything on a replay would hand anyone able to steal a single token the
        power to sign the user out of every device they own — a denial of service delivered
        by the defence itself.
        """
        leaked = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        elsewhere = await service.authenticate("aragorn", "strider123")
        await service.refresh(leaked.refresh_token)

        with pytest.raises(SessionNotRenewableError):
            await service.refresh(leaked.refresh_token)

        assert await service.refresh(elsewhere.refresh_token)

    async def test_raises_for_a_token_nobody_issued(self, service: UserService):
        with pytest.raises(SessionNotRenewableError):
            await service.refresh("not-a-token-anyone-issued")

    async def test_raises_for_an_expired_token(self, service: UserService, sessions: FakeRefreshTokenRepository):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        expiring = await stored(sessions, session.refresh_token)
        expiring.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with pytest.raises(SessionNotRenewableError):
            await service.refresh(session.refresh_token)

    async def test_raises_when_the_user_is_gone(self, service: UserService, sessions: FakeRefreshTokenRepository):
        """A session outliving its account renews nothing, rather than failing on the way out."""
        await sessions.save(
            RefreshToken(
                user_id=UserId(uuid.uuid4()),
                session_id=SessionId(uuid.uuid4()),
                token_hash=hash_refresh_token("orphaned-secret"),
                expires_at=datetime.now(UTC) + timedelta(days=30),
            )
        )

        with pytest.raises(SessionNotRenewableError):
            await service.refresh("orphaned-secret")


class TestLogOut:
    async def test_the_refresh_token_stops_working(self, service: UserService):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        await service.log_out(session.refresh_token)

        with pytest.raises(SessionNotRenewableError):
            await service.refresh(session.refresh_token)

    async def test_the_rest_of_the_session_goes_with_it(self, service: UserService):
        """Logging out ends the session, not whichever token the browser happened to hold."""
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        renewed = await service.refresh(session.refresh_token)

        await service.log_out(session.refresh_token)

        with pytest.raises(SessionNotRenewableError):
            await service.refresh(renewed.refresh_token)

    async def test_other_sessions_survive(self, service: UserService):
        here = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        elsewhere = await service.authenticate("aragorn", "strider123")

        await service.log_out(here.refresh_token)

        assert await service.refresh(elsewhere.refresh_token)

    async def test_a_token_nobody_issued_is_ignored(self, service: UserService):
        """Signing out is not a place to find out whether a token was real."""
        await service.log_out("not-a-token-anyone-issued")


class TestGet:
    async def test_returns_user_when_found(self, service: UserService):
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        created = await service.get_by_token(session.access_token)

        found = await service.get(created.id)

        assert found == created

    async def test_returns_none_when_not_found(self, service: UserService):
        result = await service.get(UserId(uuid.uuid4()))

        assert result is None


class TestGetByToken:
    async def test_returns_user_for_valid_token(self, service: UserService):
        registered = await service.register("aragorn", "aragorn@gondor.test", "strider123")
        created = await service.get_by_token(registered.access_token)
        token = create_access_token(subject=str(created.id))

        found = await service.get_by_token(token)

        assert found == created

    async def test_raises_for_malformed_token(self, service: UserService):
        with pytest.raises(InvalidCredentialsError):
            await service.get_by_token("not-a-valid-token")

    async def test_raises_when_user_no_longer_exists(self, service: UserService):
        token = create_access_token(subject=str(UserId(uuid.uuid4())))

        with pytest.raises(InvalidCredentialsError):
            await service.get_by_token(token)
