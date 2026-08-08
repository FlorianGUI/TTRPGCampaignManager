import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.common.ids import RefreshTokenId, SessionId, UserId
from app.common.security.security import create_access_token, decode_access_token, hash_refresh_token
from app.contexts.user.application.user_service import (
    InvalidCredentialsError,
    ProviderAccountUnlinkableError,
    ProviderAddressMissingError,
    ProviderAddressUnverifiedError,
    SessionNotRenewableError,
    UsernameAlreadyExistsError,
    UsernameUnavailableError,
    UserService,
)
from app.contexts.user.domain.identity import Identity, Provider
from app.contexts.user.domain.ports.identity_provider import ProviderProfile
from app.contexts.user.domain.ports.identity_repository import IdentityRepository
from app.contexts.user.domain.ports.refresh_token_repository import RefreshTokenRepository
from app.contexts.user.domain.ports.user_repository import EmailTakenError, UsernameTakenError, UserRepository
from app.contexts.user.domain.refresh_token import RefreshToken
from app.contexts.user.domain.user import User


class FakeUserRepository(UserRepository):
    def __init__(self):
        self._store: dict[UUID, User] = {}
        # Lets a test stage the failure a lost race produces, without needing two of them.
        self.fail_next_save_with: Exception | None = None

    async def save(self, user: User) -> User:
        if self.fail_next_save_with is not None:
            failure, self.fail_next_save_with = self.fail_next_save_with, None
            raise failure
        # Refuses a taken username the way the real one does — on save, from the index,
        # rather than by being asked first.
        if any(u.username == user.username for u in self._store.values()):
            raise UsernameTakenError(user.username)
        self._store[user.id] = user
        return user

    async def find_by_id(self, id: UUID) -> User | None:
        return self._store.get(id)

    async def find_by_username(self, username: str) -> User | None:
        return next((u for u in self._store.values() if u.username == username), None)

    async def find_by_email(self, email: str) -> User | None:
        return next((u for u in self._store.values() if u.email == email), None)

    async def set_password(self, id: UUID, hashed_password: str) -> None:
        stored = self._store.get(id)
        if stored is not None:
            stored.hashed_password = hashed_password

    async def mark_email_verified(self, id: UUID) -> None:
        stored = self._store.get(id)
        if stored is not None:
            stored.email_verified = True


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

    async def revoke_all_for_user(self, user_id: UserId, at: datetime) -> None:
        for token in self._store.values():
            if token.user_id == user_id:
                token.revoke(at)


class FakeIdentityRepository(IdentityRepository):
    def __init__(self):
        self._store: dict[UUID, Identity] = {}

    async def save(self, identity: Identity) -> Identity:
        self._store[identity.id] = identity
        return identity

    async def find_by_subject(self, provider: Provider, subject: str) -> Identity | None:
        return next(
            (i for i in self._store.values() if i.provider == provider and i.subject == subject),
            None,
        )

    async def find_for_user(self, user_id: UserId) -> list[Identity]:
        return [i for i in self._store.values() if i.user_id == user_id]


def discord_profile(
    subject: str = "80351110224678912",
    email: str | None = "aragorn@gondor.test",
    email_verified: bool = True,
    display_name: str = "Aragorn Elessar",
) -> ProviderProfile:
    """What a provider hands back, with the parts a test does not care about filled in.

    Defaults to the ordinary case — a confirmed address — so a scenario about anything else
    says so in one argument and everything unstated stays boring.
    """
    return ProviderProfile(
        subject=subject,
        email=email,
        email_verified=email_verified,
        display_name=display_name,
    )


@pytest.fixture
def users():
    return FakeUserRepository()


@pytest.fixture
def sessions():
    return FakeRefreshTokenRepository()


@pytest.fixture
def identities():
    return FakeIdentityRepository()


@pytest.fixture
def service(
    users: FakeUserRepository,
    sessions: FakeRefreshTokenRepository,
    identities: FakeIdentityRepository,
):
    return UserService(users, sessions, identities)


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

    async def test_raises_for_an_account_that_has_no_password(self, service: UserService, users: FakeUserRepository):
        """An account reached only through a provider (#36, #39) has no password.

        Without the guard this is not a failed login, it is a 500: `verify_password`
        raises on `None`. And a 500 where every other username answers "incorrect" says
        the account exists and how it signs in — an oracle sitting on top of the answer
        the 401 is careful not to give.
        """
        await users.save(User(username="legolas", email="legolas@woodland.test"))

        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("legolas", "anything-at-all")


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


class TestClaimUsername:
    """Attempt-and-retry, because look-then-insert is a race with a window.

    The fake below refuses names the way the real repository does — by raising after being
    asked to save, not by being consulted first — so these exercise the same path a lost
    race takes.
    """

    async def test_takes_the_derived_name_when_it_is_free(self, service: UserService, users: FakeUserRepository):
        async def claim(username: str) -> User:
            return await users.save(User(username=username, email="aragorn@gondor.test"))

        user = await service.claim_username("Aragorn Elessar", claim)

        assert user.username == "aragorn-elessar"

    async def test_takes_the_next_variant_when_the_name_is_gone(self, service: UserService, users: FakeUserRepository):
        await users.save(User(username="alice", email="alice@example.test"))

        async def claim(username: str) -> User:
            return await users.save(User(username=username, email="alice2@example.test"))

        user = await service.claim_username("Alice", claim)

        assert user.username == "alice-2"

    async def test_keeps_going_past_several_taken_names(self, service: UserService, users: FakeUserRepository):
        for taken in ("alice", "alice-2", "alice-3"):
            await users.save(User(username=taken, email=f"{taken}@example.test"))

        async def claim(username: str) -> User:
            return await users.save(User(username=username, email="another@example.test"))

        user = await service.claim_username("Alice", claim)

        assert user.username == "alice-4"

    async def test_survives_losing_the_race_rather_than_checking_first(
        self, service: UserService, users: FakeUserRepository
    ):
        """The case that look-then-insert gets wrong.

        Here the name is free when the attempt begins and taken by the time it saves —
        exactly what two simultaneous sign-ins do to each other. A service that had
        checked availability up front would have no way to recover; this one takes the
        next variant.
        """
        attempted: list[str] = []

        async def claim(username: str) -> User:
            attempted.append(username)
            if username == "alice":
                # Free when this attempt began, gone by the time it saved.
                raise UsernameTakenError(username)
            return await users.save(User(username=username, email="late@example.test"))

        user = await service.claim_username("Alice", claim)

        # It tried the name that looked free, lost, and moved on — rather than deciding
        # up front and having nowhere to go.
        assert attempted == ["alice", "alice-2"]
        assert user.username == "alice-2"

    async def test_gives_up_rather_than_spinning_forever(self, service: UserService):
        async def claim(username: str) -> User:
            raise UsernameTakenError(username)

        with pytest.raises(UsernameUnavailableError):
            await service.claim_username("Alice", claim)


class TestRegisterRacingOnTheIndex:
    async def test_a_username_taken_between_the_check_and_the_insert_is_still_a_409(
        self, service: UserService, users: FakeUserRepository
    ):
        """The window the pre-check cannot close.

        `register` looks first, which is the fast path — but two registrations for one
        username can both pass that and only one can insert. The loser used to get an
        integrity error escaping as a 500; it now gets the same conflict the check
        produces.
        """
        users.fail_next_save_with = UsernameTakenError("aragorn")

        with pytest.raises(UsernameAlreadyExistsError):
            await service.register("aragorn", "aragorn@gondor.test", "strider123")


class TestSessionOf:
    async def test_names_the_session_a_cookie_belongs_to(self, service: UserService):
        """An access token carries only a subject, so it cannot say which of a person's
        sessions is asking. The cookie can, and that is what the verification re-send cap
        counts against (#38)."""
        session = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        assert await service.session_of(session.refresh_token) == session.session_id

    async def test_refuses_a_token_naming_no_session(self, service: UserService):
        with pytest.raises(SessionNotRenewableError):
            await service.session_of("never-issued")


class TestSignInWithProvider:
    async def test_a_first_sign_in_creates_an_account(self, service: UserService, users: FakeUserRepository):
        session = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        user = await service.get_by_token(session.access_token)
        assert user.email == "aragorn@gondor.test"
        # Derived from the display name, because Discord has no username this app can use
        # directly — see `username.derive`.
        assert user.username == "aragorn-elessar"
        assert await users.find_by_username("aragorn-elessar") is not None

    async def test_the_new_account_has_no_password(self, service: UserService):
        """The account exists and there is nothing to log in to it with.

        Not an oversight to fill in with a random hash: `authenticate` reads `None` as "this
        account has no password" and answers a 401 rather than crashing, and a hash of
        something unguessable would be a password that exists and cannot be used.
        """
        session = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        user = await service.get_by_token(session.access_token)
        assert user.hashed_password is None
        assert not user.has_password

    async def test_the_new_account_starts_verified(self, service: UserService):
        """Discord confirmed the address and we checked the claim, so nothing is left to
        prove. This is the one path that may set `email_verified` without a link."""
        session = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        assert (await service.get_by_token(session.access_token)).email_verified

    async def test_the_session_is_a_real_one(self, service: UserService, sessions: FakeRefreshTokenRepository):
        """Indistinguishable downstream from a password login: an access token, and a
        refresh token written down beside it. A callback that minted only the first would
        work perfectly until the user's first page reload."""
        session = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        written = await stored(sessions, session.refresh_token)
        assert written.session_id == session.session_id
        assert not written.is_revoked

    async def test_a_returning_user_gets_the_same_account(self, service: UserService):
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())
        second = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        assert (await service.get_by_token(first.access_token)).id == (
            await service.get_by_token(second.access_token)
        ).id

    async def test_a_returning_user_gets_a_fresh_session_rather_than_the_old_one(self, service: UserService):
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())
        second = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        assert first.session_id != second.session_id
        assert first.refresh_token != second.refresh_token

    async def test_a_returning_user_is_matched_on_the_subject_not_the_address(self, service: UserService):
        """Discord's `id` is the key and the address is not consulted at all on the way
        back in. Someone who changes their address at Discord is the same person; the
        alternative is a second account appearing because they edited a profile field."""
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())
        second = await service.sign_in_with_provider(Provider.DISCORD, discord_profile(email="strider@rangers.test"))

        assert (await service.get_by_token(first.access_token)).id == (
            await service.get_by_token(second.access_token)
        ).id

    async def test_a_returning_user_is_matched_on_the_subject_not_the_display_name(self, service: UserService):
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())
        second = await service.sign_in_with_provider(Provider.DISCORD, discord_profile(display_name="Strider"))

        assert (await service.get_by_token(first.access_token)).id == (
            await service.get_by_token(second.access_token)
        ).id

    async def test_a_returning_user_is_let_in_even_if_the_address_went_unverified(self, service: UserService):
        """The address guards are for a *first* sign-in only.

        A returning user has an identity row, and that row is the whole answer. Re-checking
        the provider's claims on the way back in would let a mutable profile field lock
        somebody out of an account they already own.
        """
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())
        second = await service.sign_in_with_provider(Provider.DISCORD, discord_profile(email_verified=False))

        assert (await service.get_by_token(first.access_token)).id == (
            await service.get_by_token(second.access_token)
        ).id

    async def test_a_different_subject_is_a_different_account(self, service: UserService):
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())
        second = await service.sign_in_with_provider(
            Provider.DISCORD,
            discord_profile(subject="99999999999999999", email="legolas@mirkwood.test", display_name="Legolas"),
        )

        assert (await service.get_by_token(first.access_token)).id != (
            await service.get_by_token(second.access_token)
        ).id

    async def test_the_same_subject_at_another_provider_is_another_account(self, service: UserService):
        """`(provider, subject)` is the key, not `subject` alone. Two providers number their
        users independently and nothing stops them colliding."""
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())
        second = await service.sign_in_with_provider(
            Provider.GOOGLE, discord_profile(email="legolas@mirkwood.test", display_name="Legolas")
        )

        assert (await service.get_by_token(first.access_token)).id != (
            await service.get_by_token(second.access_token)
        ).id

    async def test_the_identity_records_the_provider_and_subject(
        self, service: UserService, identities: FakeIdentityRepository
    ):
        session = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        user = await service.get_by_token(session.access_token)
        linked = await identities.find_for_user(user.id)
        assert [(i.provider, i.subject) for i in linked] == [(Provider.DISCORD, "80351110224678912")]

    async def test_a_name_already_taken_gets_the_next_variant(self, service: UserService):
        """Two people whose display names derive the same base both get an account. The
        second is `aragorn-elessar-2`, not an integrity error."""
        await service.register("aragorn-elessar", "someone@gondor.test", "strider123")

        session = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        assert (await service.get_by_token(session.access_token)).username == "aragorn-elessar-2"


class TestSignInWithProviderAndAnExistingAccount:
    async def test_links_to_a_local_account_when_both_sides_have_proved_the_address(
        self, service: UserService, users: FakeUserRepository, identities: FakeIdentityRepository
    ):
        """The one case where linking is safe: Discord confirmed the address, and so did the
        local account through #38. Anything less is account takeover by typing somebody
        else's address into a provider profile."""
        await service.register("aragorn", "aragorn@gondor.test", "strider123")
        local = await users.find_by_username("aragorn")
        assert local is not None
        await users.mark_email_verified(local.id)

        session = await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        signed_in = await service.get_by_token(session.access_token)
        assert signed_in.id == local.id
        # And no second account appeared under the derived name.
        assert await users.find_by_username("aragorn-elessar") is None
        assert len(await identities.find_for_user(local.id)) == 1

    async def test_a_linked_account_keeps_its_password(self, service: UserService, users: FakeUserRepository):
        """Linking adds a way in; it does not take one away. Both entrances work afterwards,
        which is the point of `user_identities` being a table rather than a column."""
        await service.register("aragorn", "aragorn@gondor.test", "strider123")
        local = await users.find_by_username("aragorn")
        assert local is not None
        await users.mark_email_verified(local.id)
        await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        session = await service.authenticate("aragorn", "strider123")

        assert (await service.get_by_token(session.access_token)).id == local.id

    async def test_two_providers_reach_one_account(
        self, service: UserService, users: FakeUserRepository, identities: FakeIdentityRepository
    ):
        """Signing in with Discord and later with Google is one account, not two.

        This is what `user_identities` being a table rather than a column on `users` buys,
        and it is worth a test of its own because the mechanism is indirect: the Discord
        sign-in sets `email_verified` on the strength of Discord's own `verified` claim, and
        it is *that* flag the Google sign-in then satisfies the both-sides-verified rule
        against. Nothing links the two providers to each other — they meet at the address,
        once, and only because both had confirmed it.
        """
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile(subject="discord-1"))
        me = await service.get_by_token(first.access_token)

        second = await service.sign_in_with_provider(Provider.GOOGLE, discord_profile(subject="google-9"))

        assert (await service.get_by_token(second.access_token)).id == me.id
        assert {(i.provider, i.subject) for i in await identities.find_for_user(me.id)} == {
            (Provider.DISCORD, "discord-1"),
            (Provider.GOOGLE, "google-9"),
        }
        # And no second account was created along the way.
        assert await users.find_by_username("aragorn-elessar-2") is None

    async def test_a_second_provider_does_not_disturb_the_first(self, service: UserService):
        """Linking adds a way in and takes none away — the Discord identity still signs in
        after Google has attached to the same account."""
        first = await service.sign_in_with_provider(Provider.DISCORD, discord_profile(subject="discord-1"))
        await service.sign_in_with_provider(Provider.GOOGLE, discord_profile(subject="google-9"))

        again = await service.sign_in_with_provider(Provider.DISCORD, discord_profile(subject="discord-1"))

        assert (await service.get_by_token(again.access_token)).id == (
            await service.get_by_token(first.access_token)
        ).id

    async def test_refuses_to_link_to_an_account_that_has_not_proved_its_address(
        self, service: UserService, identities: FakeIdentityRepository
    ):
        """Half-verified is not verified. Whoever holds the Discord profile may not be
        whoever registered the local account, and there is no way to tell which — so the
        answer is no, and the way through is for the real owner to confirm the address."""
        await service.register("aragorn", "aragorn@gondor.test", "strider123")

        with pytest.raises(ProviderAccountUnlinkableError):
            await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

    async def test_a_refused_link_creates_nothing(self, service: UserService, users: FakeUserRepository):
        """Not a second account under a derived username either. The address is unique, so
        there was never anywhere for one to go — and quietly making one would be two
        accounts for one address, which is the ambiguity #37 kept the constraint to avoid."""
        await service.register("aragorn", "aragorn@gondor.test", "strider123")

        with pytest.raises(ProviderAccountUnlinkableError):
            await service.sign_in_with_provider(Provider.DISCORD, discord_profile())

        assert await users.find_by_username("aragorn-elessar") is None

    async def test_an_address_claimed_during_the_sign_in_is_refused_rather_than_crashing(
        self, service: UserService, users: FakeUserRepository
    ):
        """The window the lookup cannot close: the address was free when it was checked and
        an ordinary registration landed before the insert. Same answer as finding it there
        in the first place, rather than an integrity error escaping as a 500."""
        users.fail_next_save_with = EmailTakenError("aragorn@gondor.test")

        with pytest.raises(ProviderAccountUnlinkableError):
            await service.sign_in_with_provider(Provider.DISCORD, discord_profile())


class TestSignInWithProviderAndAnUnusableAddress:
    async def test_refuses_a_sign_in_with_no_address_at_all(self, service: UserService, users: FakeUserRepository):
        """Discord accounts can exist without one, and `users.email` is NOT NULL. Refused
        rather than worked around — see `ProviderAddressMissingError`."""
        with pytest.raises(ProviderAddressMissingError):
            await service.sign_in_with_provider(Provider.DISCORD, discord_profile(email=None))

        assert await users.find_by_username("aragorn-elessar") is None

    async def test_refuses_an_address_the_provider_has_not_confirmed(
        self, service: UserService, users: FakeUserRepository
    ):
        """Refused even though no local account exists to link to.

        The reason is the unique index rather than takeover: writing down an unconfirmed
        address would let anyone stop its real owner registering with it, just by typing it
        into a Discord profile.
        """
        with pytest.raises(ProviderAddressUnverifiedError):
            await service.sign_in_with_provider(Provider.DISCORD, discord_profile(email_verified=False))

        assert await users.find_by_username("aragorn-elessar") is None

    async def test_an_unverified_address_does_not_reach_an_existing_account(self, service: UserService):
        """The acceptance criterion, stated directly: an unverified provider address must
        not auto-link. It is refused before the local account is even looked for."""
        await service.register("aragorn", "aragorn@gondor.test", "strider123")

        with pytest.raises(ProviderAddressUnverifiedError):
            await service.sign_in_with_provider(Provider.DISCORD, discord_profile(email_verified=False))


class TestSignInWithProviderWhenTheAccountIsGone:
    async def test_an_identity_pointing_at_no_account_is_refused(
        self, service: UserService, identities: FakeIdentityRepository
    ):
        """A row that outlived the account it named. There is nothing to sign in to, and the
        answer is the one a password login gives for an account that is gone rather than a
        500 for an inconsistency the person can do nothing about."""
        await identities.save(
            Identity(user_id=UserId(uuid.uuid4()), provider=Provider.DISCORD, subject="80351110224678912")
        )

        with pytest.raises(InvalidCredentialsError):
            await service.sign_in_with_provider(Provider.DISCORD, discord_profile())
