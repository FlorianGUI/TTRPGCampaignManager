import asyncio

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/password_reset.feature")

# "I register as …", "I refresh my session" and "I should get an unauthorized error" come
# from this package's conftest, which is where steps shared by more than one feature live.


def link_from(message: dict[str, str]) -> str:
    return next(word for word in message["text"].split() if "token=" in word)


def token_from(message: dict[str, str]) -> str:
    return link_from(message).split("token=")[1]


@given(parsers.parse('I ask to reset the password for "{identifier}"'))
@when(parsers.parse('I ask to reset the password for "{identifier}"'))
def ask_for_a_reset(client: AsyncClient, context: dict, identifier: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/users/forgot-password", json={"identifier": identifier})
    )
    # Asserted here as well as in the scenario that is about it: a 500 slipping through
    # silently is how a step like this stops testing anything.
    assert response.status_code == 204
    context.setdefault("answers", []).append((response.status_code, response.content))
    context["response"] = response


@given(parsers.parse('I follow the reset link and choose "{password}"'))
@when(parsers.parse('I follow the reset link and choose "{password}"'))
def follow_reset_link(client: AsyncClient, context: dict, outbox: list[dict[str, str]], password: str):
    context["reset_token"] = token_from(outbox[-1])
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/users/reset-password", json={"token": context["reset_token"], "password": password})
    )


@when(parsers.parse('I follow the reset link again and choose "{password}"'))
def follow_reset_link_again(client: AsyncClient, context: dict, password: str):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/users/reset-password", json={"token": context["reset_token"], "password": password})
    )


@when("I follow a reset link I made up")
def follow_invented_reset_link(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/users/reset-password", json={"token": "not-a-real-token", "password": "whatever123"})
    )


@then(parsers.parse('I should receive an email at "{address}"'))
def received_an_email(outbox: list[dict[str, str]], address: str):
    assert [message for message in outbox if message["to"] == address]


@then("it should contain a reset link")
def contains_a_reset_link(outbox: list[dict[str, str]]):
    assert link_from(outbox[-1]).startswith("http")


@then("I should be told nothing either way")
def told_nothing(context: dict):
    assert context["response"].status_code == 204
    assert context["response"].content == b""


@then("no email should be sent")
def nothing_sent(outbox: list[dict[str, str]]):
    assert outbox == []


@then("both answers should be identical")
def answers_are_identical(context: dict):
    """The guarantee the whole endpoint is arranged around.

    If a known identifier and an unknown one ever answer differently — status, body, or
    anything else visible — this becomes a way to ask whether an account exists, which is
    exactly what it must not be.
    """
    known, unknown = context["answers"]
    assert known == unknown


@then(parsers.parse('I should be able to log in as "{username}" with "{password}"'))
def can_log_in(client: AsyncClient, username: str, password: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/users/login", data={"username": username, "password": password})
    )
    assert response.status_code == 200


@then(parsers.parse('I should not be able to log in as "{username}" with "{password}"'))
def cannot_log_in(client: AsyncClient, username: str, password: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/users/login", data={"username": username, "password": password})
    )
    assert response.status_code == 401


@then("I should be told the reset link is no longer valid")
def reset_link_refused(context: dict):
    assert context["response"].status_code == 400
