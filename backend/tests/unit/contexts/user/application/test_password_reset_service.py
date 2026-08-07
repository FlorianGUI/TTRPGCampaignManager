from datetime import UTC, datetime, timedelta

import pytest

from app.common.ids import PasswordResetId
from app.common.security.security import hash_opaque_token, hash_password, verify_password
from app.contexts.user.application.password_reset_service import (
    PasswordResetService,
    ResetLinkUnusableError,
)
from app.contexts.user.domain.password_reset import PasswordReset
from app.contexts.user.domain.ports.password_reset_repository import PasswordResetRepository
from app.contexts.user.domain.user import User
from tests.unit.contexts.user.application.test_email_verification_service import FakeEmailSender
from tests.unit.contexts.user.application.test_user_service import (
    FakeRefreshTokenRepository,
    FakeUserRepository,
)


class FakePasswordResetRepository(PasswordResetRepository):
    def __init__(self) -> None:
        self._store: dict[PasswordResetId, PasswordReset] = {}

    async def save(self, reset: PasswordReset) -> PasswordReset:
        self._store[reset.id] = reset
        return reset

    async def find_by_hash(self, token_hash: str) -> PasswordReset | None:
        return next((r for r in self._store.values() if r.token_hash == token_hash), None)


@pytest.fixture
def users():
    return FakeUserRepository()


@pytest.fixture
def resets():
    return FakePasswordResetRepository()


@pytest.fixture
def sessions():
    return FakeRefreshTokenRepository()


@pytest.fixture
def email():
    return FakeEmailSender()


@pytest.fixture
def service(users, resets, sessions, email):
    return PasswordResetService(users, resets, sessions, email, reset_url="https://lastdawn.fr/reset-password")


async def an_account(users: FakeUserRepository, password: str = "old-password") -> User:
    return await users.save(
        User(username="aragorn", email="aragorn@gondor.test", hashed_password=hash_password(password))
    )


class TestRequesting:
    async def test_emails_a_link_when_the_username_matches(self, service, users, email):
        await an_account(users)

        await service.request("aragorn")

        assert email.sent[0]["to"] == "aragorn@gondor.test"
        assert email.last_link.startswith("https://lastdawn.fr/reset-password?token=")

    async def test_emails_a_link_when_the_address_matches(self, service, users, email):
        """Either identifier, because someone who has forgotten their password may equally
        not remember which address they signed up with (#71)."""
        await an_account(users)

        await service.request("aragorn@gondor.test")

        assert len(email.sent) == 1

    async def test_says_nothing_and_sends_nothing_for_an_unknown_identifier(self, service, email):
        """The rule the whole endpoint is arranged around. No exception, no return value,
        nothing a router could turn into an answer — because this is the one place in the
        app that could be asked whether an account exists."""
        # Completing without raising is half the assertion: an exception here would reach
        # the router as a 500 and answer the question the 204 refuses to.
        await service.request("nobody-at-all")

        assert email.sent == []

    async def test_neither_path_has_anything_to_return(self, service, users):
        """`request` has one exit and no result, so a router cannot accidentally turn its
        answer into an answer.

        What a caller actually observes is asserted end to end in the acceptance feature —
        same status, same bytes — because that is where an oracle would be visible.
        """
        await an_account(users)

        await service.request("aragorn")
        await service.request("nobody-at-all")

    async def test_a_delivery_failure_is_not_an_answer_either(self, users, resets, sessions):
        """A 500 for a real address and a 204 for an unknown one is the same oracle wearing
        a different hat."""
        service = PasswordResetService(
            users, resets, sessions, FakeEmailSender(fails=True), reset_url="https://lastdawn.fr/reset-password"
        )
        await an_account(users)

        # Must not raise: a 500 for a real address and a 204 for an unknown one is the
        # same oracle wearing a different hat.
        await service.request("aragorn")

    async def test_stores_only_the_hash(self, service, users, resets, email):
        await an_account(users)

        await service.request("aragorn")

        held = [r.token_hash for r in resets._store.values()]
        assert email.last_token not in held
        assert held == [hash_opaque_token(email.last_token)]


class TestResetting:
    async def test_sets_the_new_password(self, service, users, email):
        user = await an_account(users)
        await service.request("aragorn")

        await service.reset(email.last_token, "a-brand-new-password")

        changed = await users.find_by_id(user.id)
        assert verify_password("a-brand-new-password", changed.hashed_password)

    async def test_the_old_password_stops_working(self, service, users, email):
        user = await an_account(users, password="old-password")
        await service.request("aragorn")

        await service.reset(email.last_token, "a-brand-new-password")

        changed = await users.find_by_id(user.id)
        assert not verify_password("old-password", changed.hashed_password)

    async def test_ends_every_session_the_account_had(self, service, users, sessions, email):
        """Resetting is what someone does when they think another person has their
        password. Leaving that person signed in is leaving the door open behind them."""
        user = await an_account(users)
        from uuid import uuid4

        from app.common.ids import SessionId
        from app.contexts.user.domain.refresh_token import RefreshToken

        for _ in range(2):
            await sessions.save(
                RefreshToken(
                    user_id=user.id,
                    session_id=SessionId(uuid4()),
                    token_hash=f"hash-{uuid4()}",
                    expires_at=datetime.now(UTC) + timedelta(days=30),
                )
            )
        await service.request("aragorn")

        await service.reset(email.last_token, "a-brand-new-password")

        assert all(token.is_revoked for token in sessions._store.values())

    async def test_verifies_the_address(self, service, users, email):
        """Following a link sent to an address proves control of it — the same proof #38's
        verification uses, by the same means. Leaving the column false would be pretending
        we had not just watched it happen."""
        user = await an_account(users)
        assert user.email_verified is False
        await service.request("aragorn")

        await service.reset(email.last_token, "a-brand-new-password")

        assert (await users.find_by_id(user.id)).email_verified is True

    async def test_gives_a_password_to_an_account_that_had_none(self, service, users, email):
        """#37 left "does an SSO user get a password later?" open; this answers it. The
        same proof of address is being offered, so the same trust follows."""
        user = await users.save(User(username="legolas", email="legolas@woodland.test"))
        await service.request("legolas")

        await service.reset(email.last_token, "a-brand-new-password")

        changed = await users.find_by_id(user.id)
        assert changed.has_password
        assert verify_password("a-brand-new-password", changed.hashed_password)

    async def test_a_link_works_once(self, service, users, email):
        """A reset link that worked twice would let anyone who read the message take the
        account back after the owner had recovered it."""
        await an_account(users)
        await service.request("aragorn")
        await service.reset(email.last_token, "first-new-password")

        with pytest.raises(ResetLinkUnusableError):
            await service.reset(email.last_token, "second-new-password")

    async def test_an_unknown_token_is_refused(self, service):
        with pytest.raises(ResetLinkUnusableError):
            await service.reset("never-issued", "whatever")

    async def test_an_expired_link_is_refused(self, service, users, resets, email):
        await an_account(users)
        await service.request("aragorn")
        for stored in resets._store.values():
            stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with pytest.raises(ResetLinkUnusableError):
            await service.reset(email.last_token, "a-brand-new-password")

    async def test_a_link_for_a_deleted_account_is_refused(self, service, users, email):
        user = await an_account(users)
        await service.request("aragorn")
        users._store.pop(user.id)

        with pytest.raises(ResetLinkUnusableError):
            await service.reset(email.last_token, "a-brand-new-password")
