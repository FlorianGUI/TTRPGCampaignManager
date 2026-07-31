import asyncio
import uuid

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/campaign_management.feature")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _auth_headers(context: dict) -> dict:
    return _headers(context["token"])


@given(parsers.parse('another game master owns a campaign named "{name}"'))
def another_game_master_owns_a_campaign(client: AsyncClient, context: dict, register_user, name: str):
    token = register_user()
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/campaigns/", json={"name": name}, headers=_headers(token))
    )
    assert response.status_code == 201
    context["other_game_master"] = {"token": token, "campaign": response.json()}


@given(parsers.parse('I create a campaign named "{name}"'))
def create_campaign(client: AsyncClient, context: dict, name: str):
    response = asyncio.get_event_loop().run_until_complete(
        client.post("/campaigns/", json={"name": name}, headers=_auth_headers(context))
    )
    assert response.status_code == 201
    context.setdefault("created_campaigns", []).append(response.json())


@when("I retrieve the campaign by its ID")
def retrieve_campaign(client: AsyncClient, context: dict):
    campaign_id = context["created_campaigns"][0]["id"]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get(f"/campaigns/{campaign_id}", headers=_auth_headers(context))
    )


@when("I retrieve the other game masters campaign")
def retrieve_the_other_game_masters_campaign(client: AsyncClient, context: dict):
    campaign_id = context["other_game_master"]["campaign"]["id"]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get(f"/campaigns/{campaign_id}", headers=_auth_headers(context))
    )


@when(parsers.parse('I rename my campaign to "{name}"'))
def rename_my_campaign(client: AsyncClient, context: dict, name: str):
    campaign_id = context["created_campaigns"][0]["id"]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.put(f"/campaigns/{campaign_id}", json={"name": name}, headers=_auth_headers(context))
    )


@when(parsers.parse('I rename the other game masters campaign to "{name}"'))
def rename_the_other_game_masters_campaign(client: AsyncClient, context: dict, name: str):
    campaign_id = context["other_game_master"]["campaign"]["id"]
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.put(f"/campaigns/{campaign_id}", json={"name": name}, headers=_auth_headers(context))
    )


@when("I list all campaigns")
def list_campaigns(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get("/campaigns/", headers=_auth_headers(context))
    )


@when("I list all campaigns without a token")
def list_campaigns_without_a_token(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(client.get("/campaigns/"))


@when("I request a campaign with an unknown ID")
def request_unknown_campaign(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.get(f"/campaigns/{uuid.uuid4()}", headers=_auth_headers(context))
    )


@when("I create a campaign without a name")
def create_campaign_without_a_name(client: AsyncClient, context: dict):
    context["response"] = asyncio.get_event_loop().run_until_complete(
        client.post("/campaigns/", json={}, headers=_auth_headers(context))
    )


@then(parsers.parse('I should see a campaign named "{name}"'))
def see_campaign(context: dict, name: str):
    assert context["response"].json()["name"] == name


@then("the campaign should be owned by me")
def see_campaign_owned_by_me(client: AsyncClient, context: dict):
    me = asyncio.get_event_loop().run_until_complete(client.get("/users/me", headers=_auth_headers(context)))
    assert context["response"].json()["owner_id"] == me.json()["id"]


@then(parsers.parse('I should see "{name}" in the campaign list'))
def see_campaign_in_list(context: dict, name: str):
    assert name in [c["name"] for c in context["response"].json()]


@then(parsers.parse('I should not see "{name}" in the campaign list'))
def not_see_campaign_in_list(context: dict, name: str):
    assert name not in [c["name"] for c in context["response"].json()]


@then(parsers.parse('the other game masters campaign should still be named "{name}"'))
def other_game_masters_campaign_is_unchanged(client: AsyncClient, context: dict, name: str):
    other = context["other_game_master"]
    response = asyncio.get_event_loop().run_until_complete(
        client.get(f"/campaigns/{other['campaign']['id']}", headers=_headers(other["token"]))
    )
    assert response.json()["name"] == name
