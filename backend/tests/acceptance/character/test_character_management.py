import asyncio
import uuid

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/character_management.feature")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _auth_headers(context: dict) -> dict:
    return _headers(context["token"])


@given(parsers.parse('another player owns a character named "{name}"'))
def another_player_owns_a_character(client: AsyncClient, context: dict, register_user, name: str):
    token = register_user()
    response = asyncio.get_event_loop().run_until_complete(
        client.post(
            "/characters/",
            json={"name": name, "character_class": "Fighter"},
            headers=_headers(token),
        )
    )
    assert response.status_code == 201
    context["other_player"] = {"token": token, "character": response.json()}


@given(parsers.parse('that player also runs a campaign named "{name}"'))
def that_player_also_runs_a_campaign(client: AsyncClient, context: dict, name: str):
    other = context["other_player"]
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/campaigns/", json={"name": name}, headers=_headers(other["token"]))
    )
    assert response.status_code == 201
    other["campaign"] = response.json()


@given(parsers.parse('I create a campaign named "{name}"'))
def create_campaign(client: AsyncClient, context: dict, name: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/campaigns/", json={"name": name}, headers=_auth_headers(context))
    )
    assert response.status_code == 201
    context["my_campaign"] = response.json()


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


@given(parsers.parse('I create a character named "{name}" with class "{character_class}" in that campaign'))
def create_character_in_my_campaign(client: AsyncClient, context: dict, name: str, character_class: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post(
            "/characters/",
            json={
                "name": name,
                "character_class": character_class,
                "campaign_id": context["my_campaign"]["id"],
            },
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context.setdefault("created_characters", []).append(response.json())


@when(parsers.parse('I create a character named "{name}" with class "{character_class}" in the other players campaign'))
def create_character_in_the_other_players_campaign(client: AsyncClient, context: dict, name: str, character_class: str):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post(
            "/characters/",
            json={
                "name": name,
                "character_class": character_class,
                "campaign_id": context["other_player"]["campaign"]["id"],
            },
            headers=_auth_headers(context),
        )
    )


@when("I retrieve the character by its ID")
def retrieve_character(client: AsyncClient, context: dict):
    character_id = context["created_characters"][0]["id"]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get(f"/characters/{character_id}", headers=_auth_headers(context))
    )


@when("I retrieve the other players character")
def retrieve_the_other_players_character(client: AsyncClient, context: dict):
    character_id = context["other_player"]["character"]["id"]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get(f"/characters/{character_id}", headers=_auth_headers(context))
    )


@when(parsers.parse('I rename my character to "{name}" at level {level:d}'))
def rename_my_character(client: AsyncClient, context: dict, name: str, level: int):
    character = context["created_characters"][0]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.put(
            f"/characters/{character['id']}",
            json={"name": name, "character_class": character["character_class"], "level": level},
            headers=_auth_headers(context),
        )
    )


@when(parsers.parse('I rename the other players character to "{name}"'))
def rename_the_other_players_character(client: AsyncClient, context: dict, name: str):
    character = context["other_player"]["character"]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.put(
            f"/characters/{character['id']}",
            json={"name": name, "character_class": character["character_class"], "level": 1},
            headers=_auth_headers(context),
        )
    )


@when("I move my character to the other players campaign")
def move_my_character_to_the_other_players_campaign(client: AsyncClient, context: dict):
    character = context["created_characters"][0]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.put(
            f"/characters/{character['id']}",
            json={
                "name": character["name"],
                "character_class": character["character_class"],
                "level": character["level"],
                "campaign_id": context["other_player"]["campaign"]["id"],
            },
            headers=_auth_headers(context),
        )
    )


@when("I list all characters")
def list_characters(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get("/characters/", headers=_auth_headers(context))
    )


@when("I list all characters without a token")
def list_characters_without_a_token(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(client.get("/characters/"))


@when("I request a character with an unknown ID")
def request_unknown_character(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get(f"/characters/{uuid.uuid4()}", headers=_auth_headers(context))
    )


@when("I create a character without a class")
def create_character_without_class(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/characters/", json={"name": "Aragorn"}, headers=_auth_headers(context))
    )


@then(parsers.parse('I should see a character named "{name}" with class "{character_class}" and level {level:d}'))
def see_character(context: dict, name: str, character_class: str, level: int):
    body = context["response"].json()
    assert body["name"] == name
    assert body["character_class"] == character_class
    assert body["level"] == level


@then("the character should be owned by me")
def see_character_owned_by_me(client: AsyncClient, context: dict):
    me = asyncio.get_event_loop().run_until_complete(client.get("/users/me", headers=_auth_headers(context)))
    assert context["response"].json()["owner_id"] == me.json()["id"]


@then("the character should be at my campaign")
def see_character_at_my_campaign(context: dict):
    assert context["response"].json()["campaign_id"] == context["my_campaign"]["id"]


@then("the character should be at no campaign")
def see_character_at_no_campaign(context: dict):
    assert context["response"].json()["campaign_id"] is None


@then("my character should still be at no campaign")
def my_character_is_still_at_no_campaign(client: AsyncClient, context: dict):
    character_id = context["created_characters"][0]["id"]
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/characters/{character_id}", headers=_auth_headers(context))
    )
    assert response.json()["campaign_id"] is None


@then(parsers.parse('I should see "{name}" in the list'))
def see_character_in_list(context: dict, name: str):
    assert name in [c["name"] for c in context["response"].json()]


@then(parsers.parse('I should not see "{name}" in the list'))
def not_see_character_in_list(context: dict, name: str):
    assert name not in [c["name"] for c in context["response"].json()]


@then(parsers.parse('the other players character should still be named "{name}"'))
def other_players_character_is_unchanged(client: AsyncClient, context: dict, name: str):
    other = context["other_player"]
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/characters/{other['character']['id']}", headers=_headers(other["token"]))
    )
    assert response.json()["name"] == name
