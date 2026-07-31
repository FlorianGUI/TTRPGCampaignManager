import asyncio
import uuid

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/character_management.feature")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _auth_headers(context: dict) -> dict:
    return _headers(context["token"])


def _characters(campaign_id: str) -> str:
    return f"/campaigns/{campaign_id}/characters/"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@given(parsers.parse('I create a campaign named "{name}"'))
def create_campaign(client: AsyncClient, context: dict, name: str):
    response = _run(client.post("/campaigns/", json={"name": name}, headers=_auth_headers(context)))
    assert response.status_code == 201
    context["my_campaign"] = response.json()


@given(parsers.parse('I create a second campaign named "{name}"'))
def create_second_campaign(client: AsyncClient, context: dict, name: str):
    response = _run(client.post("/campaigns/", json={"name": name}, headers=_auth_headers(context)))
    assert response.status_code == 201
    context["my_other_campaign"] = response.json()


@given(parsers.parse('another game master runs a campaign named "{name}"'))
def another_game_master_runs_a_campaign(client: AsyncClient, context: dict, register_user, name: str):
    token = register_user()
    response = _run(client.post("/campaigns/", json={"name": name}, headers=_headers(token)))
    assert response.status_code == 201
    context["other_game_master"] = {"token": token, "campaign": response.json()}


@given(parsers.parse('that game master has a character named "{name}" at it'))
def that_game_master_has_a_character(client: AsyncClient, context: dict, name: str):
    other = context["other_game_master"]
    response = _run(
        client.post(
            _characters(other["campaign"]["id"]),
            json={"name": name},
            headers=_headers(other["token"]),
        )
    )
    assert response.status_code == 201
    other["character"] = response.json()


@given(parsers.parse('I create a character named "{name}" at my campaign'))
def create_character(client: AsyncClient, context: dict, name: str):
    response = _run(
        client.post(
            _characters(context["my_campaign"]["id"]),
            json={"name": name},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context.setdefault("created_characters", []).append(response.json())


@given(parsers.parse('I create a character named "{name}" described as "{description}"'))
def create_character_with_description(client: AsyncClient, context: dict, name: str, description: str):
    response = _run(
        client.post(
            _characters(context["my_campaign"]["id"]),
            json={"name": name, "description": description},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context.setdefault("created_characters", []).append(response.json())


@when("I retrieve the character by its ID")
def retrieve_character(client: AsyncClient, context: dict):
    character = context["created_characters"][0]
    context["response"] = _run(
        client.get(
            f"{_characters(context['my_campaign']['id'])}{character['id']}",
            headers=_auth_headers(context),
        )
    )


@when("I retrieve that character through my other campaign")
def retrieve_character_through_my_other_campaign(client: AsyncClient, context: dict):
    character = context["created_characters"][0]
    context["response"] = _run(
        client.get(
            f"{_characters(context['my_other_campaign']['id'])}{character['id']}",
            headers=_auth_headers(context),
        )
    )


@when("I retrieve the other game masters character")
def retrieve_the_other_game_masters_character(client: AsyncClient, context: dict):
    other = context["other_game_master"]
    context["response"] = _run(
        client.get(
            f"{_characters(other['campaign']['id'])}{other['character']['id']}",
            headers=_auth_headers(context),
        )
    )


@when(parsers.parse('I rename my character to "{name}"'))
def rename_my_character(client: AsyncClient, context: dict, name: str):
    character = context["created_characters"][0]
    context["response"] = _run(
        client.put(
            f"{_characters(context['my_campaign']['id'])}{character['id']}",
            json={"name": name},
            headers=_auth_headers(context),
        )
    )


@when(parsers.parse('I rename the other game masters character to "{name}"'))
def rename_the_other_game_masters_character(client: AsyncClient, context: dict, name: str):
    other = context["other_game_master"]
    context["response"] = _run(
        client.put(
            f"{_characters(other['campaign']['id'])}{other['character']['id']}",
            json={"name": name},
            headers=_auth_headers(context),
        )
    )


@when(parsers.parse('I create a character named "{name}" at the other game masters campaign'))
def create_character_at_the_other_game_masters_campaign(client: AsyncClient, context: dict, name: str):
    other = context["other_game_master"]
    context["response"] = _run(
        client.post(
            _characters(other["campaign"]["id"]),
            json={"name": name},
            headers=_auth_headers(context),
        )
    )


@when("I rename a character with an unknown ID")
def rename_unknown_character(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.put(
            f"{_characters(context['my_campaign']['id'])}{uuid.uuid4()}",
            json={"name": "Nobody"},
            headers=_auth_headers(context),
        )
    )


@when("I list the characters at my campaign")
def list_characters(client: AsyncClient, context: dict):
    context["response"] = _run(client.get(_characters(context["my_campaign"]["id"]), headers=_auth_headers(context)))


@when("I list the characters at the other game masters campaign")
def list_characters_at_the_other_game_masters_campaign(client: AsyncClient, context: dict):
    other = context["other_game_master"]
    context["response"] = _run(client.get(_characters(other["campaign"]["id"]), headers=_auth_headers(context)))


@when("I list the characters at an unknown campaign")
def list_characters_at_an_unknown_campaign(client: AsyncClient, context: dict):
    context["response"] = _run(client.get(_characters(str(uuid.uuid4())), headers=_auth_headers(context)))


@when("I list the characters at my campaign without a token")
def list_characters_without_a_token(client: AsyncClient, context: dict):
    context["response"] = _run(client.get(_characters(context["my_campaign"]["id"])))


@when("I request a character with an unknown ID")
def request_unknown_character(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.get(
            f"{_characters(context['my_campaign']['id'])}{uuid.uuid4()}",
            headers=_auth_headers(context),
        )
    )


@when("I create a character without a name")
def create_character_without_a_name(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.post(
            _characters(context["my_campaign"]["id"]),
            json={},
            headers=_auth_headers(context),
        )
    )


@then(parsers.parse('I should see a character named "{name}"'))
def see_character(context: dict, name: str):
    assert context["response"].json()["name"] == name


@then(parsers.parse('I should see the description "{description}"'))
def see_description(context: dict, description: str):
    assert context["response"].json()["description"] == description


@then("the character should be owned by me")
def see_character_owned_by_me(client: AsyncClient, context: dict):
    me = _run(client.get("/users/me", headers=_auth_headers(context)))
    assert context["response"].json()["owner_id"] == me.json()["id"]


@then("the character should be at my campaign")
def see_character_at_my_campaign(context: dict):
    assert context["response"].json()["campaign_id"] == context["my_campaign"]["id"]


@then(parsers.parse('I should see "{name}" in the list'))
def see_character_in_list(context: dict, name: str):
    assert name in [c["name"] for c in context["response"].json()]


@then(parsers.parse('the other game masters character should still be named "{name}"'))
def other_game_masters_character_is_unchanged(client: AsyncClient, context: dict, name: str):
    other = context["other_game_master"]
    response = _run(
        client.get(
            f"{_characters(other['campaign']['id'])}{other['character']['id']}",
            headers=_headers(other["token"]),
        )
    )
    assert response.json()["name"] == name
