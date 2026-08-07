from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.common.ids import EmailVerificationId, SessionId, UserId
from app.common.security.security import hash_opaque_token
from app.contexts.user.application.email_verification_service import (
    RESEND_COOLDOWN_SECONDS,
    RESENDS_PER_SESSION,
    EmailVerificationService,
    TooManyVerificationRequestsError,
    VerificationLinkUnusableError,
)
from app.contexts.user.domain.email_verification import EmailVerification
from app.contexts.user.domain.ports.email_sender import EmailDeliveryError, EmailSender
from app.contexts.user.domain.ports.email_verification_repository import EmailVerificationRepository
from app.contexts.user.domain.user import User
from tests.unit.contexts.user.application.test_user_service import FakeUserRepository


class FakeEmailSender(EmailSender):
    """Every message this suite ever sends. No test reaches a provider."""

    def __init__(self, fails: bool = False) -> None:
        self.sent: list[dict[str, str]] = []
        self.fails = fails

    async def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
        if self.fails:
            raise EmailDeliveryError("nope")
        self.sent.append({"to": to, "subject": subject, "text": text})

    @property
    def last_link(self) -> str:
        """The URL out of the most recent message, as a reader would click it."""
        body = self.sent[-1]["text"]
        return next(word for word in body.split() if "token=" in word)

    @property
    def last_token(self) -> str:
        return self.last_link.split("token=")[1]


class FakeEmailVerificationRepository(EmailVerificationRepository):
    def __init__(self) -> None:
        self._store: dict[EmailVerificationId, EmailVerification] = {}

    async def save(self, verification: EmailVerification) -> EmailVerification:
        self._store[verification.id] = verification
        return verification

    async def find_by_hash(self, token_hash: str) -> EmailVerification | None:
        return next((v for v in self._store.values() if v.token_hash == token_hash), None)

    async def count_for_session(self, session_id: SessionId) -> int:
        return len([v for v in self._store.values() if v.session_id == session_id])

    async def last_sent_at(self, user_id: UserId) -> datetime | None:
        sent = [v.created_at for v in self._store.values() if v.user_id == user_id]
        return max(sent) if sent else None

    def age_everything(self, by: timedelta) -> None:
        """Pretend time passed, so the cooldown can be tested without waiting for it."""
        for verification in self._store.values():
            verification.created_at -= by


@pytest.fixture
def users():
    return FakeUserRepository()


@pytest.fixture
def verifications():
    return FakeEmailVerificationRepository()


@pytest.fixture
def email():
    return FakeEmailSender()


@pytest.fixture
def service(users, verifications, email):
    return EmailVerificationService(users, verifications, email, verify_url="https://api.test/users/verify-email")


@pytest.fixture
def session_id():
    return SessionId(uuid4())


async def a_user(users: FakeUserRepository, verified: bool = False) -> User:
    return await users.save(
        User(username="aragorn", email="aragorn@gondor.test", hashed_password="hashed", email_verified=verified)
    )


class TestSendingForRegistration:
    async def test_emails_a_link_to_the_new_account(self, service, users, email, session_id):
        user = await a_user(users)

        await service.send_for_registration(user, session_id)

        assert email.sent[0]["to"] == "aragorn@gondor.test"
        assert email.last_link.startswith("https://api.test/users/verify-email?token=")

    async def test_the_link_points_where_it_was_configured_to(self, users, verifications, email, session_id):
        """The URL is the SPA's, not the API's, and a scanner prefetching it must reach a
        page rather than an endpoint that spends the token."""
        service = EmailVerificationService(users, verifications, email, verify_url="https://lastdawn.fr/verify-email")
        user = await a_user(users)

        await service.send_for_registration(user, session_id)

        assert email.last_link.startswith("https://lastdawn.fr/verify-email?token=")

    async def test_stores_only_the_hash_of_the_token(self, service, users, email, verifications, session_id):
        """A database dump should not be a drawer full of working links."""
        user = await a_user(users)

        await service.send_for_registration(user, session_id)

        held = [v.token_hash for v in verifications._store.values()]
        assert email.last_token not in held
        assert held == [hash_opaque_token(email.last_token)]

    async def test_a_provider_outage_does_not_break_registering(self, users, verifications, session_id):
        """Account creation must not depend on Brevo being reachable. The row is written
        first, so the link exists and re-send is the way back."""
        service = EmailVerificationService(
            users, verifications, FakeEmailSender(fails=True), verify_url="https://api.test/users/verify-email"
        )
        user = await a_user(users)

        await service.send_for_registration(user, session_id)

        assert len(verifications._store) == 1


class TestVerifying:
    async def test_marks_the_address_verified(self, service, users, email, session_id):
        user = await a_user(users)
        await service.send_for_registration(user, session_id)

        verified = await service.verify(email.last_token)

        assert verified.email_verified is True
        assert (await users.find_by_id(user.id)).email_verified is True

    async def test_a_link_works_once(self, service, users, email, session_id):
        user = await a_user(users)
        await service.send_for_registration(user, session_id)
        await service.verify(email.last_token)

        with pytest.raises(VerificationLinkUnusableError):
            await service.verify(email.last_token)

    async def test_an_unknown_token_is_refused(self, service):
        with pytest.raises(VerificationLinkUnusableError):
            await service.verify("never-issued")

    async def test_an_expired_link_is_refused(self, service, users, verifications, email, session_id):
        user = await a_user(users)
        await service.send_for_registration(user, session_id)
        for stored in verifications._store.values():
            stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with pytest.raises(VerificationLinkUnusableError):
            await service.verify(email.last_token)

    async def test_a_link_for_a_deleted_account_is_refused(self, service, users, email, session_id):
        user = await a_user(users)
        await service.send_for_registration(user, session_id)
        users._store.pop(user.id)

        with pytest.raises(VerificationLinkUnusableError):
            await service.verify(email.last_token)


class TestResending:
    async def test_sends_another_link(self, service, users, email, verifications, session_id):
        user = await a_user(users)
        verifications.age_everything(timedelta(seconds=RESEND_COOLDOWN_SECONDS + 1))

        await service.resend(user, session_id)

        assert len(email.sent) == 1

    async def test_the_old_link_still_works(self, service, users, email, verifications, session_id):
        """Asking for a new one must not break the mail already in someone's inbox — they
        may well open the first message."""
        user = await a_user(users)
        await service.send_for_registration(user, session_id)
        first = email.last_token
        verifications.age_everything(timedelta(seconds=RESEND_COOLDOWN_SECONDS + 1))
        await service.resend(user, session_id)

        assert (await service.verify(first)).email_verified is True

    async def test_stops_at_the_cap_for_one_session(self, service, users, verifications, session_id):
        user = await a_user(users)
        for _ in range(RESENDS_PER_SESSION):
            verifications.age_everything(timedelta(seconds=RESEND_COOLDOWN_SECONDS + 1))
            await service.resend(user, session_id)

        verifications.age_everything(timedelta(seconds=RESEND_COOLDOWN_SECONDS + 1))
        with pytest.raises(TooManyVerificationRequestsError):
            await service.resend(user, session_id)

    async def test_signing_in_again_starts_the_count_over(self, service, users, verifications, session_id):
        """What the decision on #38 asks for: the cap is per session, and a new sign-in is
        a new session."""
        user = await a_user(users)
        for _ in range(RESENDS_PER_SESSION):
            verifications.age_everything(timedelta(seconds=RESEND_COOLDOWN_SECONDS + 1))
            await service.resend(user, session_id)

        verifications.age_everything(timedelta(seconds=RESEND_COOLDOWN_SECONDS + 1))
        await service.resend(user, SessionId(uuid4()))

    async def test_the_cooldown_does_not_reset_with_a_new_session(self, service, users, session_id):
        """The hole the cap alone leaves. Signing out and back in buys three more sends,
        so if the cooldown reset too there would be nothing stopping a loop."""
        user = await a_user(users)
        await service.resend(user, session_id)

        with pytest.raises(TooManyVerificationRequestsError):
            await service.resend(user, SessionId(uuid4()))

    async def test_says_how_long_to_wait(self, service, users, session_id):
        user = await a_user(users)
        await service.resend(user, session_id)

        with pytest.raises(TooManyVerificationRequestsError) as refused:
            await service.resend(user, session_id)

        retry_after = refused.value.retry_after
        assert retry_after is not None
        assert 0 < retry_after <= RESEND_COOLDOWN_SECONDS + 1

    async def test_an_already_verified_account_is_a_no_op(self, service, users, email, session_id):
        """A second tab, or a link followed between loading the page and pressing the
        button. Not an error, and not a message either."""
        user = await a_user(users, verified=True)

        await service.resend(user, session_id)

        assert email.sent == []
