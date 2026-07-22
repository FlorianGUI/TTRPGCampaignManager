import asyncio
import uuid

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/character_management.feature")


def _auth_headers(context: dict) -> dict:
    return {"Authorization": f"Bearer {context['token']}"}


@given(parsers.parse('I create a character named "{name}" with class "{character_class}"'))
def create_character(client: AsyncClient, context: dict, name: str, character_class: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post(
            "/characters/",
            json={"name": name, "character_class": character_class},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context.setdefault("created_characters", []).append(response.json())


@when("I retrieve the character by its ID")
def retrieve_character(client: AsyncClient, context: dict):
    character_id = context["created_characters"][0]["id"]
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/characters/{character_id}", headers=_auth_headers(context))
    )
    context["response"] = response


@when("I list all characters")
def list_characters(client: AsyncClient, context: dict):
    response = asyncio.get_event_loop().run_until_complete(client.get("/characters/", headers=_auth_headers(context)))
    context["response"] = response


@when("I request a character with an unknown ID")
def request_unknown_character(client: AsyncClient, context: dict):
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/characters/{uuid.uuid4()}", headers=_auth_headers(context))
    )
    context["response"] = response


@then(parsers.parse('I should see a character named "{name}" with class "{character_class}" and level 1'))
def see_character(context: dict, name: str, character_class: str):
    body = context["response"].json()
    assert body["name"] == name
    assert body["character_class"] == character_class
    assert body["level"] == 1


@then(parsers.parse('I should see "{name}" in the list'))
def see_character_in_list(context: dict, name: str):
    names = [c["name"] for c in context["response"].json()]
    assert name in names


@then("I should get a not found error")
def get_not_found_error(context: dict):
    assert context["response"].status_code == 404


@when("I create a character without a class")
def create_character_without_class(client: AsyncClient, context: dict):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/characters/", json={"name": "Aragorn"}, headers=_auth_headers(context))
    )
    context["response"] = response


@then("I should get a validation error")
def get_validation_error(context: dict):
    assert context["response"].status_code == 422
