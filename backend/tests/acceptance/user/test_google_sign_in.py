from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, when

from app.contexts.user.domain.ports.identity_provider import IdentityProviderError, ProviderProfile
from tests.acceptance.user.conftest import (
    AUTHORIZATION_CODE,
    come_back,
    sign_in_and_remember,
    start,
)
from tests.conftest import FakeIdentityProvider

"""The Google sign-in, driven the way a browser drives it.

Deliberately a second feature file rather than an Examples table over the Discord one. The
two providers share a flow but not a story: Google's identity arrives inside a signed
id_token and Discord's from a profile call, Google has no "account with no address" case at
all, and the scenario that matters most here — one person arriving through both — has no
counterpart there. A table would need a column of exceptions for every row.

The shared vocabulary lives in this package's conftest. What is here is Google's alone.
"""

scenarios("features/google_sign_in.feature")

PROVIDER = "google"

SUBJECT = "110169484474386276334"


@given(parsers.parse('Google knows me as "{name}" with the confirmed address "{email}"'))
def google_knows_me(google_provider: FakeIdentityProvider, name: str, email: str):
    google_provider.answer = ProviderProfile(subject=SUBJECT, email=email, email_verified=True, display_name=name)


@given(parsers.parse('Google knows me as "{name}" with the unconfirmed address "{email}"'))
def google_knows_me_unverified(google_provider: FakeIdentityProvider, name: str, email: str):
    google_provider.answer = ProviderProfile(subject=SUBJECT, email=email, email_verified=False, display_name=name)


@given("Google answers with an id_token that does not verify")
def google_answers_unverifiably(google_provider: FakeIdentityProvider):
    """A forged signature, a wrong audience, an expired token — one answer to a caller.

    Which of them it was is the adapter's business, and every one of them has its own test
    over there against a real RS256 token. From here it is what a network failure is: the
    sign-in did not happen, and nothing about the account changed.
    """
    google_provider.answer = IdentityProviderError("Google's id_token did not verify: InvalidSignatureError")


@given("I sign in with Google")
@when("I sign in with Google")
def sign_in_with_google(client: AsyncClient, context: dict):
    context["first_account"] = context.get("account")
    sign_in_and_remember(client, context, PROVIDER)


@when("I sign in with Google again")
def sign_in_with_google_again(client: AsyncClient, context: dict):
    context["first_account"] = context["account"]
    sign_in_and_remember(client, context, PROVIDER)


@given("I have started signing in with Google")
def started_signing_in_with_google(client: AsyncClient, context: dict):
    start(client, context, PROVIDER)


@when(parsers.parse('Google starts using the address "{email}" for me'))
def google_changes_my_address(google_provider: FakeIdentityProvider, email: str):
    assert isinstance(google_provider.answer, ProviderProfile)
    google_provider.answer = ProviderProfile(
        subject=google_provider.answer.subject,
        email=email,
        email_verified=True,
        display_name=google_provider.answer.display_name,
    )


@when("I refuse to authorise the app at Google")
def refuse_at_google(client: AsyncClient, context: dict):
    state = start(client, context, PROVIDER)
    come_back(client, context, PROVIDER, error="access_denied", state=state)


@when("the Google callback comes back with a state I did not send")
def google_callback_with_a_foreign_state(client: AsyncClient, context: dict):
    come_back(client, context, PROVIDER, code=AUTHORIZATION_CODE, state="a-state-from-somewhere-else")


@when("the Google callback comes back a second time")
def google_callback_comes_back_again(client: AsyncClient, context: dict):
    come_back(client, context, PROVIDER, **context["callback"])


@when("that sign-in comes back to the Google callback instead")
def cross_provider_callback(client: AsyncClient, context: dict):
    """A sign-in begun at one provider, coming back at another's callback — the mix-up shape.

    The cookie records which provider it began at, so this is turned away before anything is
    redeemed. Without that field it would get as far as asking Google to honour a Discord
    code, which also fails — but for a reason belonging to Google rather than to us, and
    only by luck of the two never sharing a token endpoint.
    """
    come_back(client, context, PROVIDER, code=AUTHORIZATION_CODE, state=context["state"])
