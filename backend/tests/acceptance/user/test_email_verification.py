import asyncio

import pytest
from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

from app.contexts.user.adapters.primary.api.refresh_cookie import REFRESH_COOKIE_NAME
from app.contexts.user.application import email_verification_service

# "I register as …" comes from this package's conftest, which is where it moved so that
# both features could share one definition of it.
scenarios("features/email_verification.feature")


def link_from(message: dict[str, str]) -> str:
    return next(word for word in message["text"].split() if "token=" in word)


def token_from(message: dict[str, str]) -> str:
    return link_from(message).split("token=")[1]


@given("enough time has passed to ask again")
def no_cooldown(monkeypatch: pytest.MonkeyPatch):
    """Waiting two real minutes in a test is not a test, it is a delay.

    The cooldown itself is covered by the unit tests, which can move time. What these
    scenarios are for is the behaviour around it, so here it is simply out of the way.
    """
    monkeypatch.setattr(email_verification_service, "RESEND_COOLDOWN_SECONDS", 0)


@when("I follow the verification link")
@given("I follow the verification link")
def follow_link(client: AsyncClient, context: dict, outbox: list[dict[str, str]]):
    context["followed"] = token_from(outbox[-1])
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/users/verify-email", json={"token": context["followed"]})
    )


@when("I follow the verification link again")
def follow_link_again(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/users/verify-email", json={"token": context["followed"]})
    )


@when("I follow a verification link I made up")
def follow_invented_link(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/users/verify-email", json={"token": "not-a-real-token"})
    )


@when("I ask for another verification link")
def ask_again(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/users/verify-email/resend", headers={"Authorization": f"Bearer {context['token']}"})
    )


@when(parsers.parse("I ask for another verification link {count:d} times"))
def ask_again_repeatedly(client: AsyncClient, context: dict, monkeypatch: pytest.MonkeyPatch, count: int):
    # The cap is what this scenario is about, so the cooldown is stood down to reach it.
    monkeypatch.setattr(email_verification_service, "RESEND_COOLDOWN_SECONDS", 0)
    for _ in range(count):
        context["response"] = asyncio.get_event_loop().run_until_complete(
            client.post("/users/verify-email/resend", headers={"Authorization": f"Bearer {context['token']}"})
        )


@when("I ask who I am")
def ask_who_i_am(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get("/users/me", headers={"Authorization": f"Bearer {context['token']}"})
    )


@then(parsers.parse('I should receive an email at "{address}"'))
def received_an_email(outbox: list[dict[str, str]], address: str):
    assert [message for message in outbox if message["to"] == address]


@then(parsers.parse('I should receive a second email at "{address}"'))
def received_a_second_email(outbox: list[dict[str, str]], address: str):
    assert len([message for message in outbox if message["to"] == address]) == 2


@then("it should contain a verification link")
def contains_a_link(outbox: list[dict[str, str]]):
    assert link_from(outbox[-1]).startswith("http")


@then("my address should be confirmed")
def address_confirmed(context: dict):
    assert context["response"].status_code == 200


@then("I should be told the link is no longer valid")
def link_refused(context: dict):
    assert context["response"].status_code == 400


@then("I should be told to wait")
def told_to_wait(context: dict):
    assert context["response"].status_code == 429


@then("I should be told my own username")
def told_my_username(context: dict):
    """Advisory, not enforced: an unverified account is a working account (#38)."""
    assert context["response"].status_code == 200
    assert context["response"].json()["username"]


@given("my browser loses its refresh cookie")
def lose_the_cookie(client: AsyncClient):
    client.cookies.clear()


@when("I ask for another verification link with a made-up cookie")
def ask_again_with_invented_cookie(client: AsyncClient, context: dict):
    """A valid access token and a refresh cookie naming no session.

    The two credentials answer different questions — who, and which session — and this
    endpoint needs both, because the cap is counted per session. Holding only the first
    must not get anyone through uncounted.
    """
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post(
            "/users/verify-email/resend",
            headers={
                "Authorization": f"Bearer {context['token']}",
                "Cookie": f"{REFRESH_COOKIE_NAME}=not-a-real-refresh-token",
            },
        )
    )


@then("I should be told to sign in again")
def told_to_sign_in_again(context: dict):
    assert context["response"].status_code == 401
