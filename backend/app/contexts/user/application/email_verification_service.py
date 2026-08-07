import os
from datetime import UTC, datetime, timedelta

from app.common.ids import SessionId
from app.common.security.security import create_opaque_token, hash_opaque_token
from app.contexts.user.domain.email_verification import EmailVerification
from app.contexts.user.domain.ports.email_sender import EmailDeliveryError, EmailSender
from app.contexts.user.domain.ports.email_verification_repository import EmailVerificationRepository
from app.contexts.user.domain.ports.user_repository import UserRepository
from app.contexts.user.domain.user import User

# 24 hours: the shortest window that still covers registering in the evening and reading
# the mail next morning (#38). Configurable for the same reason the token lifetimes in
# security.py are — how long is tolerable depends on who is using it.
_DEFAULT_TOKEN_HOURS = 24
VERIFICATION_TOKEN_EXPIRE_HOURS = int(os.environ.get("VERIFICATION_TOKEN_EXPIRE_HOURS") or _DEFAULT_TOKEN_HOURS)

# Three per session, resetting when a new session begins (#38).
_DEFAULT_RESENDS_PER_SESSION = 3
RESENDS_PER_SESSION = int(os.environ.get("RESENDS_PER_SESSION") or _DEFAULT_RESENDS_PER_SESSION)

# The cap alone is decoration: it resets on sign-in, so signing out and back in buys three
# more. This is the control that actually stops a loop, because nothing resets it. Long
# enough that a script achieves nothing, short enough that someone who genuinely lost a
# message is not stuck waiting.
_DEFAULT_COOLDOWN_SECONDS = 120
RESEND_COOLDOWN_SECONDS = int(os.environ.get("RESEND_COOLDOWN_SECONDS") or _DEFAULT_COOLDOWN_SECONDS)


class TooManyVerificationRequestsError(Exception):
    """Either control refused: the session's three are spent, or the cooldown is running.

    One exception for both because the caller does the same thing — waits — and because
    saying which would describe the limits to someone probing them.
    """

    def __init__(self, retry_after: int | None = None) -> None:
        super().__init__("Too many verification emails requested")
        self.retry_after = retry_after


class VerificationLinkUnusableError(Exception):
    """The link is unknown, expired, or already spent.

    One exception for all three deliberately, matching how `SessionNotRenewableError`
    treats a refresh token. Nothing can be done differently between them — ask for another
    link — and separating them would confirm to whoever is guessing that a token existed.
    """


class EmailVerificationService:
    """Issuing and spending the links that set `email_verified`.

    Separate from `UserService` rather than folded into it, because registration should not
    depend on a mail provider being reachable: every unit test of signing up would need an
    email fake, and an outage at Brevo would turn account creation into a 500. Composed by
    the router instead, which is also where the decision "registering sends one" belongs
    now that the two failure modes are different.
    """

    def __init__(
        self,
        users: UserRepository,
        verifications: EmailVerificationRepository,
        email: EmailSender,
        verify_url: str,
    ) -> None:
        self._users = users
        self._verifications = verifications
        self._email = email
        self._verify_url = verify_url

    async def send_for_registration(self, user: User, session_id: SessionId) -> None:
        """Issue the first link, and never let its delivery break registering.

        A provider outage must not fail account creation. The row is written before the
        send is attempted, so the account exists, the link exists, and a caller who never
        received it can ask for another — which is the whole reason re-send is in this
        issue.
        """
        try:
            await self._issue(user, session_id)
        except EmailDeliveryError:
            # Swallowed here and nowhere else. `resend` propagates it, because there a
            # person pressed a button and is owed an answer.
            return

    async def resend(self, user: User, session_id: SessionId) -> None:
        """Issue another link for the caller's own address.

        Authenticated, and it takes the user from the session rather than an address from
        the request. That is what stops this being a way to send mail to strangers, and it
        is also why nothing here has to be careful about disclosing whether an address is
        registered: the caller already proved who they are.
        """
        if user.email_verified:
            # Nothing to verify. Not an error — a second tab, or a link followed between
            # loading the page and pressing the button.
            return

        await self._check_allowance(user, session_id)
        await self._issue(user, session_id)

    async def verify(self, token: str) -> User:
        """Spend a link and mark the address verified.

        The user is re-read rather than trusted from the token, and the token is spent
        before the user is saved: a link that fails halfway leaves an unusable token and an
        unverified address, which is recoverable by asking for another. The reverse order
        could verify twice.
        """
        found = await self._verifications.find_by_hash(hash_opaque_token(token))
        now = datetime.now(UTC)
        if found is None or found.is_used or found.has_expired(now):
            raise VerificationLinkUnusableError

        user = await self._users.find_by_id(found.user_id)
        if user is None:
            raise VerificationLinkUnusableError

        found.use(now)
        await self._verifications.save(found)
        await self._users.mark_email_verified(user.id)
        user.email_verified = True
        return user

    async def _check_allowance(self, user: User, session_id: SessionId) -> None:
        used = await self._verifications.count_for_session(session_id)
        if used >= RESENDS_PER_SESSION:
            raise TooManyVerificationRequestsError

        last = await self._verifications.last_sent_at(user.id)
        if last is None:
            return
        waited = (datetime.now(UTC) - last).total_seconds()
        if waited < RESEND_COOLDOWN_SECONDS:
            raise TooManyVerificationRequestsError(retry_after=int(RESEND_COOLDOWN_SECONDS - waited) + 1)

    async def _issue(self, user: User, session_id: SessionId) -> None:
        secret = create_opaque_token()
        await self._verifications.save(
            EmailVerification(
                user_id=user.id,
                session_id=session_id,
                token_hash=hash_opaque_token(secret),
                expires_at=datetime.now(UTC) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS),
            )
        )
        link = f"{self._verify_url}?token={secret}"
        await self._email.send(
            to=user.email,
            subject="Confirm your email address",
            text=(
                f"Welcome to the Campaign Manager, {user.username}.\n\n"
                f"Confirm this address by opening the link below. It works once and "
                f"expires in {VERIFICATION_TOKEN_EXPIRE_HOURS} hours.\n\n"
                f"{link}\n\n"
                "If you did not create this account, ignore this message and nothing will happen."
            ),
        )
