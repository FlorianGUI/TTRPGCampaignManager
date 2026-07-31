import asyncio
import uuid

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/source_management.feature")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _auth_headers(context: dict) -> dict:
    return _headers(context["token"])


@given(parsers.parse('another game master owns a source titled "{title}"'))
def another_game_master_owns_a_source(client: AsyncClient, context: dict, register_user, title: str):
    token = register_user()
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/sources/", json={"title": title}, headers=_headers(token))
    )
    assert response.status_code == 201
    context["other_game_master"] = {"token": token, "source": response.json()}


@given(parsers.parse('I create a source titled "{title}"'))
def create_source(client: AsyncClient, context: dict, title: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/sources/", json={"title": title}, headers=_auth_headers(context))
    )
    assert response.status_code == 201
    context.setdefault("created_sources", []).append(response.json())


@when("I retrieve the source by its ID")
def retrieve_source(client: AsyncClient, context: dict):
    source_id = context["created_sources"][0]["id"]
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/sources/{source_id}", headers=_auth_headers(context))
    )
    context["response"] = response


@when("I retrieve the other game masters source")
def retrieve_the_other_game_masters_source(client: AsyncClient, context: dict):
    source_id = context["other_game_master"]["source"]["id"]
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/sources/{source_id}", headers=_auth_headers(context))
    )
    context["response"] = response


@when(parsers.parse('I rename my source to "{title}"'))
def rename_my_source(client: AsyncClient, context: dict, title: str):
    source_id = context["created_sources"][0]["id"]
    response = asyncio.get_event_loop().run_until_complete(
        client.put(f"/sources/{source_id}", json={"title": title}, headers=_auth_headers(context))
    )
    context["response"] = response


@when(parsers.parse('I rename the other game masters source to "{title}"'))
def rename_the_other_game_masters_source(client: AsyncClient, context: dict, title: str):
    source_id = context["other_game_master"]["source"]["id"]
    response = asyncio.get_event_loop().run_until_complete(
        client.put(f"/sources/{source_id}", json={"title": title}, headers=_auth_headers(context))
    )
    context["response"] = response


@when("I list all sources")
def list_sources(client: AsyncClient, context: dict):
    response = asyncio.get_event_loop().run_until_complete(client.get("/sources/", headers=_auth_headers(context)))
    context["response"] = response


@when("I list all sources without a token")
def list_sources_without_a_token(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(client.get("/sources/"))


@when("I request a source with an unknown ID")
def request_unknown_source(client: AsyncClient, context: dict):
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/sources/{uuid.uuid4()}", headers=_auth_headers(context))
    )
    context["response"] = response


@when("I create a source without a title")
def create_source_without_a_title(client: AsyncClient, context: dict):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/sources/", json={}, headers=_auth_headers(context))
    )
    context["response"] = response


@then(parsers.parse('I should see a source titled "{title}"'))
def see_source(context: dict, title: str):
    assert context["response"].json()["title"] == title


@then("the source should be owned by me")
def see_source_owned_by_me(client: AsyncClient, context: dict):
    me = asyncio.get_event_loop().run_until_complete(client.get("/users/me", headers=_auth_headers(context)))
    assert context["response"].json()["owner_id"] == me.json()["id"]


@then(parsers.parse('I should see "{title}" in the list'))
def see_source_in_list(context: dict, title: str):
    titles = [s["title"] for s in context["response"].json()]
    assert title in titles


@then(parsers.parse('I should not see "{title}" in the list'))
def not_see_source_in_list(context: dict, title: str):
    titles = [s["title"] for s in context["response"].json()]
    assert title not in titles


@then(parsers.parse('the other game masters source should still be titled "{title}"'))
def other_game_masters_source_is_unchanged(client: AsyncClient, context: dict, title: str):
    other = context["other_game_master"]
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/sources/{other['source']['id']}", headers=_headers(other["token"]))
    )
    assert response.json()["title"] == title


@then("I should get a not found error")
def get_not_found_error(context: dict):
    assert context["response"].status_code == 404


@then("I should get a validation error")
def get_validation_error(context: dict):
    assert context["response"].status_code == 422


@then("I should be told I am not authenticated")
def get_unauthenticated_error(context: dict):
    assert context["response"].status_code == 401
