import asyncio
import os
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.contexts.user.adapters.primary.api.routers.auth import get_discord_provider, get_google_provider
from app.contexts.user.adapters.primary.api.routers.users import (
    get_password_reset_service,
    get_verification_service,
)
from app.contexts.user.adapters.secondary.persistence.email_verification_repository import (
    SqlAlchemyEmailVerificationRepository,
)
from app.contexts.user.adapters.secondary.persistence.password_reset_repository import (
    SqlAlchemyPasswordResetRepository,
)
from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import (
    SqlAlchemyRefreshTokenRepository,
)
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.email_verification_service import EmailVerificationService
from app.contexts.user.application.password_reset_service import PasswordResetService
from app.contexts.user.domain.identity import Provider
from app.contexts.user.domain.ports.email_sender import EmailSender
from app.contexts.user.domain.ports.identity_provider import IdentityProvider, ProviderProfile
from app.database import get_db
from app.main import app

load_dotenv()

# Tests run against their own database, never the one `just dev` writes to. Sharing the
# two means a character created by hand in the running app can fail an acceptance test.
#
# The variable is deliberately required rather than derived from DATABASE_URL: it is set
# for local development and CI only, so on a machine that has no test database configured
# — production, where the repo is checked out but never tested — the suite refuses to
# start instead of quietly creating one next to the real database.
if "TEST_DATABASE_URL" not in os.environ:
    raise RuntimeError(
        "TEST_DATABASE_URL is not set. The suite needs a database of its own so it cannot "
        "collide with development data — copy the line from .env.example. If you are seeing "
        "this on a deployed server, the tests are not meant to run there."
    )

_TEST_URL = make_url(os.environ["TEST_DATABASE_URL"])

# The session fixture below drops whatever this points at, so refuse anything that is not
# unmistakably a test database, however the environment came to be configured.
if not (_TEST_URL.database or "").endswith("_test"):
    raise RuntimeError(
        f"TEST_DATABASE_URL points at {_TEST_URL.database!r}. The suite drops and recreates "
        "its database on every run, so it will only accept a name ending in '_test'."
    )

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

# NullPool avoids asyncpg connections being reused across event loops between tests
_test_engine = create_async_engine(_TEST_URL, poolclass=NullPool)

# Sessions are bound to the per-test connection rather than the engine, and join its
# already-open transaction with a savepoint. A repository's commit() then releases a
# savepoint instead of writing for real, so the rollback in db_connection still undoes it.
_TestSessionLocal = async_sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
    join_transaction_mode="create_savepoint",
)


async def _recreate_test_database():
    """Drop and recreate the test database.

    CREATE/DROP DATABASE cannot run inside a transaction, hence the autocommit connection,
    and it runs against the `postgres` maintenance database because the target is being
    replaced. FORCE evicts connections a previous interrupted run may have left open.
    """
    admin_engine = create_async_engine(_TEST_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin_engine.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{_TEST_URL.database}" WITH (FORCE)'))
            await connection.execute(text(f'CREATE DATABASE "{_TEST_URL.database}"'))
    finally:
        await admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Rebuild the test database from nothing and bring it up to head, once per session.

    Tearing down at the start rather than at the end is deliberate: an interrupted run
    never reaches its teardown, and a leftover database would then be migrated on top of
    instead of rebuilt, which is the schema drift this is meant to prevent. It also means
    every run exercises the migrations from zero.

    Migrations run in a subprocess so alembic gets its own event loop, and so the schema
    under test is the one the migrations actually produce rather than a create_all guess.
    """
    asyncio.run(_recreate_test_database())
    migration = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=_BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": _TEST_URL.render_as_string(hide_password=False)},
        capture_output=True,
        text=True,
    )
    if migration.returncode != 0:
        raise RuntimeError(f"Could not migrate the test database:\n{migration.stdout}\n{migration.stderr}")


@pytest.fixture(autouse=True)
def rate_limiter_budget():
    """Give every test the limiter's full budget, rather than switching the limiter off.

    Two hundred tests hitting one in-process app inside half a minute look exactly like
    the traffic the limiter exists to turn away, and they share a key: the ASGI transport
    reports the same client address for all of them. #33 answered that by disabling the
    limiter for the whole session, which left nothing exercising it — `rate_limiter.py`
    read as fully covered while no test had ever seen a 429.

    Clearing the storage between tests answers it without that: the limiter stays on and
    real everywhere, so a test that wants to prove throttling just makes the calls, and no
    test can be pushed over an edge by traffic that belongs to another one. Test order and
    suite size stop mattering, which is what made adding a scenario dangerous before.

    Not enough on its own for the BDD suite — one scenario can register more accounts than
    an hourly limit allows all by itself. See `tests/acceptance/conftest.py`.
    """
    app.state.limiter.reset()


@pytest.fixture
async def db_connection():
    """Give each test its own connection, inside a transaction that is never committed.

    Everything a test writes is rolled back on teardown, so tests stay independent of
    each other and of previous runs against a persistent local database.
    """
    async with _test_engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()


@pytest.fixture
async def db(db_connection):
    async with _TestSessionLocal(bind=db_connection) as session:
        yield session


@pytest.fixture
async def client(db_connection):
    async def _override_get_db():
        async with _TestSessionLocal(bind=db_connection) as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    # https, not http, and the refresh cookie is why. It is set `Secure`, and httpx's
    # cookie jar enforces that the way a browser does: it will accept the cookie over a
    # plain http base URL and then never send it back, so every refresh test would fail
    # with a missing cookie rather than for any reason to do with the code under test.
    # The transport is in-process either way — the scheme is a claim about the connection,
    # and https is the true one for every deployment this runs in.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def outbox() -> list[dict[str, str]]:
    """Every message the app tried to send during a scenario."""
    return []


@pytest.fixture(autouse=True)
def no_real_mail(outbox: list[dict[str, str]]):
    """Nothing in this suite reaches a mail provider, ever.

    At the root rather than in one package, which is the correction: it lived under
    tests/acceptance/ first, and the system tests register users too — they went straight
    to the real adapter and died on a missing BREVO_API_KEY. That failure was the polite
    version. The rude version is a suite that finds the key set, on a laptop or in CI, and
    posts fixture addresses to Brevo.

    Autouse for the same reason: registering sends a verification link (#38), and almost
    every test that touches the app registers somebody. A fixture you had to remember would
    be one omission away from real mail.

    The repositories stay real, so the rows a test asserts on are the rows the app actually
    wrote. Only the outbound edge is replaced.
    """

    class RecordingEmailSender(EmailSender):
        async def send(self, to: str, subject: str, text: str, html: str | None = None) -> None:
            outbox.append({"to": to, "subject": subject, "text": text})

    def override(db: AsyncSession = Depends(get_db)) -> EmailVerificationService:
        return EmailVerificationService(
            SqlAlchemyUserRepository(db),
            SqlAlchemyEmailVerificationRepository(db),
            RecordingEmailSender(),
            verify_url="http://testserver/users/verify-email",
        )

    def override_reset(db: AsyncSession = Depends(get_db)) -> PasswordResetService:
        return PasswordResetService(
            SqlAlchemyUserRepository(db),
            SqlAlchemyPasswordResetRepository(db),
            SqlAlchemyRefreshTokenRepository(db),
            RecordingEmailSender(),
            reset_url="http://testserver/reset-password",
        )

    # Every service that sends, not just the first one. Adding a sender and forgetting this
    # is exactly how the suite started reaching for a real API key again — it failed
    # loudly this time, but the failure it is guarding against is the quiet one.
    app.dependency_overrides[get_verification_service] = override
    app.dependency_overrides[get_password_reset_service] = override_reset
    yield
    app.dependency_overrides.pop(get_verification_service, None)
    app.dependency_overrides.pop(get_password_reset_service, None)


class FakeIdentityProvider(IdentityProvider):
    """A provider that answers from memory instead of from discord.com.

    Replaces only the outbound edge, exactly as `RecordingEmailSender` does: the state
    cookie, the PKCE pair, the redirect and every decision about which account a sign-in
    reaches are the real ones. What is faked is the one thing a test cannot have — a person
    consenting at a provider's own domain.

    `answer` is what the next `profile` call produces. Set it to an exception to stage a
    provider that refuses or cannot be reached.
    """

    def __init__(self, speaks_for: Provider = Provider.DISCORD) -> None:
        self._speaks_for = speaks_for
        self.answer: ProviderProfile | Exception = ProviderProfile(
            subject="80351110224678912",
            email="aragorn@gondor.test",
            email_verified=True,
            display_name="Aragorn Elessar",
        )
        # Every (code, verifier) pair redeemed, so a test can prove the verifier that came
        # back is the one minted at the start rather than something the caller supplied.
        self.redeemed: list[tuple[str, str]] = []

    @property
    def provider(self) -> Provider:
        return self._speaks_for

    def authorization_url(self, state: str, code_challenge: str) -> str:
        return f"https://{self._speaks_for}.test/oauth2/authorize?state={state}&code_challenge={code_challenge}"

    async def profile(self, code: str, code_verifier: str) -> ProviderProfile:
        self.redeemed.append((code, code_verifier))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


@pytest.fixture
def sso_provider() -> FakeIdentityProvider:
    """What Discord would have said, for the scenario to arrange."""
    return FakeIdentityProvider(Provider.DISCORD)


@pytest.fixture
def google_provider() -> FakeIdentityProvider:
    """The same for Google.

    Its own instance rather than one shared object with a switch on it, so a scenario that
    arranges what Discord knows cannot silently be answering as Google — which is exactly
    the confusion the cross-provider scenarios exist to rule out.
    """
    return FakeIdentityProvider(Provider.GOOGLE)


@pytest.fixture(autouse=True)
def no_real_sso(sso_provider: FakeIdentityProvider, google_provider: FakeIdentityProvider):
    """Nothing in this suite reaches discord.com or accounts.google.com, ever.

    Autouse and at the root for the same reason `no_real_mail` is. The real adapters read
    their client secret at construction, so on a machine that has one configured a test
    which merely wandered onto a callback would post a fixture's authorization code to a
    live token endpoint. A fixture you had to remember would be one omission away from that.

    **Both providers, not just the first.** Registering an adapter and forgetting to add it
    here is how the suite would start reaching for a real credential again — and unlike the
    mail case, which failed loudly on a missing key, this one would quietly succeed against
    whatever application the developer happens to have configured.
    """
    app.dependency_overrides[get_discord_provider] = lambda: sso_provider
    app.dependency_overrides[get_google_provider] = lambda: google_provider
    yield
    app.dependency_overrides.pop(get_discord_provider, None)
    app.dependency_overrides.pop(get_google_provider, None)
