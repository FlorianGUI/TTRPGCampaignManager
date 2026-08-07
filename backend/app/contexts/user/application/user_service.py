from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from app.common.ids import SessionId, UserId
from app.common.security.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.contexts.user.domain.ports.refresh_token_repository import RefreshTokenRepository
from app.contexts.user.domain.ports.user_repository import UserRepository
from app.contexts.user.domain.refresh_token import RefreshToken
from app.contexts.user.domain.session import Session
from app.contexts.user.domain.user import User


class UsernameAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class SessionNotRenewableError(Exception):
    """The refresh token presented cannot buy a new access token, for any of its reasons.

    One exception for "no such token", "already used", "revoked" and "expired" on purpose.
    Only the last of those is ordinary, and telling a caller which one it hit would confirm
    to whoever stole a token that it was real and merely stale. Nothing can be done
    differently in any of the four cases: sign in again.
    """


class UserService:
    def __init__(self, repository: UserRepository, sessions: RefreshTokenRepository) -> None:
        self._repository = repository
        self._sessions = sessions

    async def register(self, username: str, email: str, password: str) -> Session:
        """Create the account and hand back the tokens that sign it in.

        Registering and signing in are one action to the person doing them, so they are
        one call here. Returning the new `User` and letting the router mint tokens would
        put "signing up signs you in" in an adapter, where the next inbound port — an SSO
        callback, an invite acceptance — would have to remember to repeat it.

        The tokens are the only thing that comes back for the same reason: an endpoint that
        also returned the user would be describing an account nobody has asked to see yet,
        and `GET /users/me` already answers that with the token this returns.
        """
        if await self._repository.find_by_username(username) is not None:
            raise UsernameAlreadyExistsError(username)
        user = User(username=username, email=email, hashed_password=hash_password(password))
        saved = await self._repository.save(user)
        return await self._begin_session(saved)

    async def authenticate(self, username: str, password: str) -> Session:
        """Sign in with a username and password, for the accounts that have one.

        The middle condition is the one worth reading. An account created through a
        provider has no password at all (#37), and `verify_password` against `None` raises
        rather than returning False — so without it, presenting any password for an
        SSO-only username is a 500 instead of a 401. That is both a crash and an account
        oracle: an error where every other username gives "incorrect" tells an attacker
        the account exists and how it signs in.

        Passwordless accounts therefore fail exactly as a wrong password does. There is no
        separate "this account uses Google" answer for the same reason /users/login says
        nothing else it knows.
        """
        user = await self._repository.find_by_username(username)
        if user is None or user.hashed_password is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError(username)
        return await self._begin_session(user)

    async def refresh(self, refresh_token: str) -> Session:
        """Trade a refresh token for a new access token and a replacement refresh token.

        The replacement is the point. If refreshing handed back the same token, a copy
        stolen off the wire or out of a backup would stay good for the whole window and
        nothing would ever notice. Rotating means a stolen token is only useful until the
        real client next refreshes — and, more usefully, that whichever of the two loses
        that race presents a token which has already been spent.

        That is the second branch below, and it is the security-critical one: a *revoked*
        token coming back is not an error, it is evidence. The only way to hold one is to
        have been given it and not have been the one who spent it, which means the secret
        exists in two places. Rejecting just this request would leave the thief's freshly
        rotated token working, so the whole session goes and both parties are logged out.
        The legitimate user signing in again is the correct price for that.

        Expiry, by contrast, is ordinary: the session reached the end of its absolute
        window, and nothing about that suggests anyone leaked anything.
        """
        presented = await self._sessions.find_by_hash(hash_refresh_token(refresh_token))
        if presented is None:
            raise SessionNotRenewableError
        now = datetime.now(UTC)
        if presented.is_revoked:
            await self._sessions.revoke_session(presented.session_id, now)
            raise SessionNotRenewableError
        if presented.has_expired(now):
            raise SessionNotRenewableError
        user = await self._repository.find_by_id(presented.user_id)
        if user is None:
            raise SessionNotRenewableError
        presented.revoke(now)
        await self._sessions.save(presented)
        return await self._begin_session(user, session_id=presented.session_id, expires_at=presented.expires_at)

    async def log_out(self, refresh_token: str) -> None:
        """End this session, and say nothing about whether there was one.

        Silent when the token is unknown, because logging out is not a place to learn
        whether a token is real, and because the honest case — a cookie left over from a
        session the server already revoked — looks exactly like a probe and should not
        fail somebody's attempt to sign out.

        This device only: other browsers keep their own sessions, which is what makes them
        separate sessions in the first place. Signing out everywhere is a different
        feature and deserves its own endpoint rather than arriving as a surprise here.
        """
        found = await self._sessions.find_by_hash(hash_refresh_token(refresh_token))
        if found is not None:
            await self._sessions.revoke_session(found.session_id, datetime.now(UTC))

    async def _begin_session(
        self,
        user: User,
        session_id: SessionId | None = None,
        expires_at: datetime | None = None,
    ) -> Session:
        """The one place a session begins, or carries on.

        Every way in goes through here — registering, logging in, refreshing — so they
        cannot drift apart, and so there is no route to an access token that forgets to
        leave a refresh token behind it.

        Both optional arguments continue a session rather than starting one. Keeping
        `session_id` is what makes rotation a chain instead of a pile of unrelated tokens,
        and it is the thing reuse detection revokes. Keeping `expires_at` is what makes
        the window absolute: a refresh that recomputed the deadline would push it, and a
        session refreshed often enough would then never end.
        """
        secret = create_refresh_token()
        deadline = expires_at or datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        await self._sessions.save(
            RefreshToken(
                user_id=user.id,
                session_id=session_id or SessionId(uuid4()),
                token_hash=hash_refresh_token(secret),
                expires_at=deadline,
            )
        )
        return Session(
            access_token=create_access_token(subject=str(user.id)),
            refresh_token=secret,
            expires_at=deadline,
        )

    async def get(self, id: UserId) -> User | None:
        return await self._repository.find_by_id(id)

    async def get_by_token(self, token: str) -> User:
        try:
            user_id = UserId(UUID(decode_access_token(token)))
        except (jwt.PyJWTError, ValueError):
            raise InvalidCredentialsError(token) from None
        user = await self._repository.find_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError(token)
        return user
