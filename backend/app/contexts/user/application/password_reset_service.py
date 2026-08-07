import os
from datetime import UTC, datetime, timedelta

from app.common.security.security import create_opaque_token, hash_opaque_token, hash_password
from app.contexts.user.domain.password_reset import PasswordReset
from app.contexts.user.domain.ports.email_sender import EmailDeliveryError, EmailSender
from app.contexts.user.domain.ports.password_reset_repository import PasswordResetRepository
from app.contexts.user.domain.ports.refresh_token_repository import RefreshTokenRepository
from app.contexts.user.domain.ports.user_repository import UserRepository
from app.contexts.user.domain.user import User

# One hour, against the twenty-four a verification link gets (#38). A reset token is
# strictly more powerful — it takes the account over rather than confirming a fact about
# it — so it should stop mattering sooner. Long enough for mail to arrive and be read;
# short enough that a message left in an unattended inbox goes stale quickly.
_DEFAULT_RESET_HOURS = 1
PASSWORD_RESET_EXPIRE_HOURS = int(os.environ.get("PASSWORD_RESET_EXPIRE_HOURS") or _DEFAULT_RESET_HOURS)


class ResetLinkUnusableError(Exception):
    """Unknown, expired, or already spent.

    One exception for all three, as everywhere else here. Nothing can be done differently
    between them — ask for another link — and separating them would confirm to whoever is
    guessing that a token existed.
    """


class PasswordResetService:
    """Requesting a reset, and spending one.

    The whole of `request` is arranged around one rule: **the answer must not depend on
    whether the account exists.** This endpoint is unauthenticated and takes an identifier
    from the request, so it is the one place in the app that could be asked "does this
    account exist?" — and #71 accepts usernames as well as addresses, which makes that a
    cheaper question to ask, not a dearer one.
    """

    def __init__(
        self,
        users: UserRepository,
        resets: PasswordResetRepository,
        sessions: RefreshTokenRepository,
        email: EmailSender,
        reset_url: str,
    ) -> None:
        self._users = users
        self._resets = resets
        self._sessions = sessions
        self._email = email
        self._reset_url = reset_url

    async def request(self, identifier: str) -> None:
        """Email a reset link, if there is anyone to email.

        Returns nothing in every case, and deliberately has no other exit: no exception, no
        boolean, nothing a router could accidentally turn into an answer. A caller that
        could tell the two apart would be an account-existence oracle, and the endpoint
        above this is careful for nothing if the service is not.

        A delivery failure is swallowed for the same reason it must not propagate: a 500
        for a real address and a 204 for an unknown one is the same oracle wearing a
        different hat. Someone who receives nothing asks again.
        """
        user = await self._find(identifier)
        if user is None:
            return

        try:
            await self._issue(user)
        except EmailDeliveryError:
            return

    async def reset(self, token: str, new_password: str) -> None:
        """Set a new password, and end every session the account had.

        Three things happen together, and the order is chosen so a failure part-way through
        leaves the account safer rather than less safe: the link is spent first, then the
        password changes, then sessions are revoked. Crashing before the revoke leaves a
        changed password and live sessions, which is recoverable by resetting again;
        revoking first and then failing would log someone out without giving them the new
        password they were promised.

        Sessions go because resetting is what someone does when they believe another person
        has their password. Leaving that person signed in is leaving the door open behind
        them — and unlike logging out, this one is not "this device only".

        The address becomes verified because following a link sent to it proves control of
        it, which is exactly what #38's verification proves and by exactly the same means.
        Leaving the column false here would be pretending we had not just watched it
        happen.

        An account with no password gets one. #37 left "does an SSO user get a password
        later?" open and this answers it: the same proof of address is being offered, so
        the same trust follows.
        """
        found = await self._resets.find_by_hash(hash_opaque_token(token))
        now = datetime.now(UTC)
        if found is None or found.is_used or found.has_expired(now):
            raise ResetLinkUnusableError

        user = await self._users.find_by_id(found.user_id)
        if user is None:
            raise ResetLinkUnusableError

        found.use(now)
        await self._resets.save(found)
        await self._users.set_password(user.id, hash_password(new_password))
        await self._users.mark_email_verified(user.id)
        await self._sessions.revoke_all_for_user(user.id, now)

    async def _find(self, identifier: str) -> User | None:
        """An address or a username, whichever it turns out to be.

        Both are looked up, always, rather than guessing from the shape of the string. A
        function that only consulted one table when the input contained an "@" would take
        measurably less time for one kind of miss than the other, and timing is an answer.
        """
        by_email = await self._users.find_by_email(identifier)
        by_username = await self._users.find_by_username(identifier)
        return by_email or by_username

    async def _issue(self, user: User) -> None:
        secret = create_opaque_token()
        await self._resets.save(
            PasswordReset(
                user_id=user.id,
                token_hash=hash_opaque_token(secret),
                expires_at=datetime.now(UTC) + timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS),
            )
        )
        link = f"{self._reset_url}?token={secret}"
        await self._email.send(
            to=user.email,
            subject="Reset your password",
            text=(
                f"Someone asked to reset the password for {user.username}.\n\n"
                f"Open the link below to choose a new one. It works once and expires in "
                f"{PASSWORD_RESET_EXPIRE_HOURS} hour(s).\n\n"
                f"{link}\n\n"
                "If this was not you, ignore this message — your password has not changed, "
                "and nobody can use this link without opening it."
            ),
        )
