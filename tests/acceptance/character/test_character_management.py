import uuid

import pytest
from httpx import AsyncClient
from pytest_bdd import given, when, then, scenarios, parsers

scenarios("features/character_management.feature")


@pytest.fixture
def context():
    return {}


@given(parsers.parse('I create a character named "{name}" with class "{character_class}"'))
async def create_character(client: AsyncClient, context: dict, name: str, character_class: str):
    response = await client.post("/characters/", json={"name": name, "character_class": character_class})
    assert response.status_code == 201
    context.setdefault("created_characters", []).append(response.json())


@when("I retrieve the character by its ID")
async def retrieve_character(client: AsyncClient, context: dict):
    character_id = context["created_characters"][0]["id"]
    response = await client.get(f"/characters/{character_id}")
    context["response"] = response


@when("I list all characters")
async def list_characters(client: AsyncClient, context: dict):
    response = await client.get("/characters/")
    context["response"] = response


@when("I request a character with an unknown ID")
async def request_unknown_character(client: AsyncClient, context: dict):
    response = await client.get(f"/characters/{uuid.uuid4()}")
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
async def create_character_without_class(client: AsyncClient, context: dict):
    response = await client.post("/characters/", json={"name": "Aragorn"})
    context["response"] = response


@then("I should get a validation error")
def get_validation_error(context: dict):
    assert context["response"].status_code == 422