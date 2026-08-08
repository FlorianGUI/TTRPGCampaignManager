from collections.abc import Awaitable, Callable
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
from app.contexts.user.domain.identity import Identity, Provider
from app.contexts.user.domain.ports.identity_provider import ProviderProfile
from app.contexts.user.domain.ports.identity_repository import IdentityRepository
from app.contexts.user.domain.ports.refresh_token_repository import RefreshTokenRepository
from app.contexts.user.domain.ports.user_repository import EmailTakenError, UsernameTakenError, UserRepository
from app.contexts.user.domain.refresh_token import RefreshToken
from app.contexts.user.domain.session import Session
from app.contexts.user.domain.user import User
from app.contexts.user.domain.username import derive as derive_username
from app.contexts.user.domain.username import variant as username_variant

# Enough that contention never reaches it, small enough that a base which somehow cannot
# produce a free name fails rather than loops.
_USERNAME_ATTEMPTS = 50


class UsernameAlreadyExistsError(Exception):
    pass


class UsernameUnavailableError(Exception):
    """No variant of a derived base was free within the attempt cap.

    Distinct from `UsernameAlreadyExistsError`, which is a person being told the name they
    chose is taken. This one is nobody's fault and nothing the caller can fix by choosing
    differently — it means fifty variants of one base are all in use.
    """


class InvalidCredentialsError(Exception):
    pass


class SessionNotRenewableError(Exception):
    """The refresh token presented cannot buy a new access token, for any of its reasons.

    One exception for "no such token", "already used", "revoked" and "expired" on purpose.
    Only the last of those is ordinary, and telling a caller which one it hit would confirm
    to whoever stole a token that it was real and merely stale. Nothing can be done
    differently in any of the four cases: sign in again.
    """


class ProviderAddressMissingError(Exception):
    """The provider signed somebody in but gave us no address to attach the account to.

    Discord specifically: `email` comes back `null` when the account has none, and the
    account row needs one — `users.email` is NOT NULL and unique, deliberately, because an
    address is what password reset and verification identify a person by (#37).

    The sign-in is refused rather than worked around. The alternatives were an account with
    no address, which makes both of those flows ambiguous for every account, and prompting
    for one, which needs somewhere to park a half-finished sign-up. Refusing is the smaller
    commitment and the only one that can be loosened later without a migration to undo.
    """


class ProviderAddressUnverifiedError(Exception):
    """The provider handed over an address it has not itself confirmed.

    Refused for both of the things it could otherwise do. It must not link to an existing
    local account — that is account takeover by typing somebody else's address into a
    provider profile, and it is the reason `email_verified` exists at all. And it must not
    create a *new* account either, because `users.email` is unique: an unverified address
    written down here is an address its real owner can no longer register with.

    Not a dead end in practice. Discord exposes `verified` precisely because it asks people
    to confirm, so the way through is to confirm the address there and come back.
    """


class ProviderAccountUnlinkableError(Exception):
    """The provider's address already belongs to a local account that has not proved it.

    Auto-linking on a matching address is a known account-takeover route, and it is only
    safe when *both* sides are verified: the provider has confirmed the address reaches this
    person, and the local account has confirmed the same thing through #38. This is the case
    where the provider's half is good and the local half is not.

    Nothing safe is available here. Linking would hand the account to whoever holds the
    provider profile; creating a second account cannot happen, because the address is
    unique. So the sign-in is refused and the way through is to verify the local account —
    which is a thing only its real owner can do, which is the point.
    """


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        sessions: RefreshTokenRepository,
        identities: IdentityRepository,
    ) -> None:
        self._repository = repository
        self._sessions = sessions
        self._identities = identities

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
        try:
            saved = await self._repository.save(user)
        except UsernameTakenError:
            # The check above is the fast path, not the guarantee. Two registrations for
            # one username can both pass it and only one can insert — which used to
            # surface as an integrity error escaping to a 500, for the caller who lost by
            # milliseconds. The index decides; this reports its decision as the same 409
            # the check produces.
            raise UsernameAlreadyExistsError(username) from None
        return await self._begin_session(saved)

    async def claim_username(self, display_name: str, claim: Callable[[str], Awaitable[User]]) -> User:
        """Take the first free username derived from a provider's display name.

        Written as attempt-and-retry rather than look-then-insert, and that is the whole
        point of it. Checking availability first is a race with a window: two people called
        Alice signing in at the same moment both find "alice" free, and one of them gets an
        integrity error instead of an account. The unique index is the only authority on
        whether a name is taken, so this asks it — by inserting — and takes the next
        variant when the answer is no.

        `claim` builds and saves the user for a given username, so the caller decides what
        else goes on the row (which provider, which address, verified or not) without this
        needing to know. It is expected to raise `UsernameTakenError`, which is what the
        repository raises.

        The attempt cap exists so a pathological base cannot spin forever; reaching it means
        something is wrong beyond contention.
        """
        base = derive_username(display_name)
        for attempt in range(_USERNAME_ATTEMPTS):
            try:
                return await claim(username_variant(base, attempt))
            except UsernameTakenError:
                continue
        raise UsernameUnavailableError(base)

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

    async def sign_in_with_provider(self, provider: Provider, profile: ProviderProfile) -> Session:
        """Sign in whoever a provider has just vouched for, creating the account if needed.

        The fourth way in, and it ends where the other three do — `_begin_session` — so what
        an SSO caller receives is indistinguishable from a password login downstream: same
        access token, same refresh cookie, same logout. Minting an access token here instead
        would compile and pass and produce accounts that work until the first page reload.

        **The subject lookup comes first, and it is the only lookup a returning user gets.**
        Once an identity exists, the address on the profile is not consulted at all — not to
        confirm it, not to update the account, not to notice it changed. A `sub` is the
        provider's permanent name for a person; an address is a mutable attribute that can
        be reassigned to somebody else entirely. Reading the address on the way in would
        make a sign-in depend on a value the account holder does not control, which is the
        takeover route this whole arrangement exists to close.

        Everything address-shaped therefore belongs to the first sign-in only, and lives in
        `_account_for` below.
        """
        known = await self._identities.find_by_subject(provider, profile.subject)
        if known is None:
            return await self._begin_session(await self._account_for(provider, profile))

        user = await self._repository.find_by_id(known.user_id)
        if user is None:
            # An identity pointing at no account: the user was removed and this row outlived
            # it. There is nothing to sign in to, and the answer is the one a password login
            # gives for an account that is gone rather than a 500 for an inconsistency the
            # person signing in can do nothing about.
            raise InvalidCredentialsError(profile.subject)
        return await self._begin_session(user)

    async def _account_for(self, provider: Provider, profile: ProviderProfile) -> User:
        """Which local account a *first* sign-in from this provider reaches.

        Three outcomes and they are deliberately not symmetrical, because the risks are not.
        Creating an account is cheap and reversible. Linking to one that already exists hands
        over everything in it, so it is allowed on exactly one condition — both sides have
        proved the address — and refused in every other case rather than made to work.

        Read the two guards at the top as one rule: an address this provider has not
        confirmed is not usable for anything here. It cannot link, for the obvious reason,
        and it cannot start a new account either, because `users.email` is unique — writing
        an unconfirmed address down would let anyone lock its real owner out of registering
        by typing it into a provider profile.
        """
        if profile.email is None:
            raise ProviderAddressMissingError(provider)
        if not profile.email_verified:
            raise ProviderAddressUnverifiedError(provider)
        address = profile.email

        existing = await self._repository.find_by_email(address)
        if existing is not None:
            if not existing.email_verified:
                raise ProviderAccountUnlinkableError(provider)
            return await self._link(existing, provider, profile.subject)

        async def claim(username: str) -> User:
            created = await self._repository.save(
                # Verified on arrival, because the provider just said so and we checked.
                # This is the one place `email_verified` may be set without a link being
                # followed, and it is why the guard above is not optional.
                User(username=username, email=address, email_verified=True)
            )
            return await self._link(created, provider, profile.subject)

        try:
            return await self.claim_username(profile.display_name, claim)
        except EmailTakenError:
            # The address was free when it was looked up and is not any more — an ordinary
            # registration landed in between. Same answer as finding it in the first place:
            # the account exists and has not proved this address, so nothing may be linked.
            raise ProviderAccountUnlinkableError(provider) from None

    async def _link(self, user: User, provider: Provider, subject: str) -> User:
        await self._identities.save(Identity(user_id=user.id, provider=provider, subject=subject))
        return user

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
        belongs_to = session_id or SessionId(uuid4())
        await self._sessions.save(
            RefreshToken(
                user_id=user.id,
                session_id=belongs_to,
                token_hash=hash_refresh_token(secret),
                expires_at=deadline,
            )
        )
        return Session(
            access_token=create_access_token(subject=str(user.id)),
            refresh_token=secret,
            expires_at=deadline,
            session_id=belongs_to,
        )

    async def session_of(self, refresh_token: str) -> SessionId:
        """Which session a refresh cookie belongs to.

        The access token carries only a subject, so an authenticated request cannot say
        which of a person's sessions it is — but the cookie can, and it is sent to
        everything under /users by its own Path. Needed by the verification re-send cap,
        which counts per session so that signing in starts the count again (#38).
        """
        found = await self._sessions.find_by_hash(hash_refresh_token(refresh_token))
        if found is None:
            raise SessionNotRenewableError
        return found.session_id

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
