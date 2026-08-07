import asyncio
import uuid

import pytest
from fastapi import Depends
from httpx import AsyncClient
from pytest_bdd import given, then
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.user.adapters.primary.api.routers.users import get_verification_service
from app.contexts.user.adapters.secondary.persistence.email_verification_repository import (
    SqlAlchemyEmailVerificationRepository,
)
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.email_verification_service import EmailVerificationService
from app.contexts.user.domain.ports.email_sender import EmailSender
from app.database import get_db
from app.main import app


@pytest.fixture(autouse=True)
def rate_limiting_off():
    """No acceptance scenario can trip a rate limit, however many the suite grows to.

    These files describe what a game master can do. A scenario that fails on the ninety-
    ninth account is testing infrastructure by accident, and the failure lands on whoever
    added the scenario rather than on whoever changed a limit. Every scenario also opens by
    registering — that is how it gets someone to be — so registration is precisely the call
    they all make, and it is the one carrying the tightest limit in the app.

    Clearing the budget per test, as `tests/conftest.py` does, is not enough here: a
    scenario needing a second person registers twice in one test, and #35's session
    scenarios spend several requests each, so the ratio of requests to scenarios is no
    longer roughly one. A single scenario can outgrow an hourly limit on its own.

    Scoped to this package rather than the session, which is the whole point: the limiter
    stays live for `tests/system/`, where throttling is turned on deliberately and the 429
    is asserted. Restored on teardown so it is still live for whatever runs after.
    """
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True


@pytest.fixture
def context():
    return {}


@pytest.fixture
def register_user(client: AsyncClient):
    """Register a brand new user and return their access token.

    Scenarios that need a second person — someone whose data I must not be able to
    reach — take their token from here rather than through the login step, which
    would overwrite the one identifying "me".

    One call, because #33 made registering return a token. It used to be register then
    login, which is the same two-step every client would have had to write.
    """

    def _register() -> str:
        username = f"user-{uuid.uuid4().hex[:8]}"
        response = asyncio.get_event_loop().run_until_complete(
            client.post(
                "/users/register",
                json={"username": username, "email": f"{username}@example.com", "password": "testpass123"},
            )
        )
        return str(response.json()["access_token"])

    return _register


@given("I am logged in as a player")
@given("I am logged in as a game master")
def log_in(context: dict, register_user):
    context["token"] = register_user()


# The three answers every context gives the same way. They live here rather than in each
# feature's step definitions so that "not found" cannot come to mean one thing for
# characters and another for campaigns.


@then("I should get a not found error")
def get_not_found_error(context: dict):
    assert context["response"].status_code == 404


@then("I should get a validation error")
def get_validation_error(context: dict):
    assert context["response"].status_code == 422


@then("I should be told I am not authenticated")
def get_unauthenticated_error(context: dict):
    assert context["response"].status_code == 401


@pytest.fixture
def outbox() -> list[dict[str, str]]:
    """Every message the app tried to send during a scenario."""
    return []


@pytest.fixture(autouse=True)
def no_real_mail(outbox: list[dict[str, str]]):
    """Nothing in this suite reaches a mail provider, ever.

    Autouse rather than opt-in, and that is the point: registering sends a verification
    link (#38), and every scenario in every feature registers somebody. A test that had to
    remember to disable mail would be one forgotten fixture away from posting to Brevo —
    with real addresses from the fixtures — on somebody's laptop or in CI.

    The repositories stay real, so the rows a scenario asserts on are the rows the app
    actually wrote. Only the outbound edge is replaced.
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

    app.dependency_overrides[get_verification_service] = override
    yield
    app.dependency_overrides.pop(get_verification_service, None)
