import asyncio
import uuid

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/scene_management.feature")

# The body every "byte for byte" scenario uses. Deliberately awkward: a container
# directive with an attribute, two inline ones, a trailing newline and an em dash. If any
# layer between the request and the column decides to be helpful, one of those goes.
READ_ALOUD = (
    ':::read-aloud{label="Boxed text"}\n'
    "The gate does not swing. It sinks —\n"
    ":::\n\n"
    ":npc[Torvald] wants :item[the rubbing], and :dice[2d6]{result=7} says whether he gets it.\n"
)


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _auth_headers(context: dict) -> dict:
    return _headers(context["token"])


def _scenes(campaign_id: str) -> str:
    return f"/campaigns/{campaign_id}/scenes/"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _my_scene(context: dict, title: str | None = None) -> dict:
    created = context["created_scenes"]
    if title is None:
        return created[0]
    return next(s for s in created if s["title"] == title)


@given(parsers.parse('I create a campaign named "{name}"'))
def create_campaign(client: AsyncClient, context: dict, name: str):
    response = _run(client.post("/campaigns/", json={"name": name}, headers=_auth_headers(context)))
    assert response.status_code == 201
    context["my_campaign"] = response.json()


@given(parsers.parse('another game master runs a campaign named "{name}"'))
def another_game_master_runs_a_campaign(client: AsyncClient, context: dict, register_user, name: str):
    token = register_user()
    response = _run(client.post("/campaigns/", json={"name": name}, headers=_headers(token)))
    assert response.status_code == 201
    context["other_game_master"] = {"token": token, "campaign": response.json()}


@given(parsers.parse('that game master has a scene named "{title}" in it'))
def that_game_master_has_a_scene(client: AsyncClient, context: dict, title: str):
    other = context["other_game_master"]
    response = _run(
        client.post(
            _scenes(other["campaign"]["id"]),
            json={"title": title},
            headers=_headers(other["token"]),
        )
    )
    assert response.status_code == 201
    other["scene"] = response.json()


@given(parsers.parse('I create a scene named "{title}" in my campaign'))
def create_scene(client: AsyncClient, context: dict, title: str):
    response = _run(
        client.post(
            _scenes(context["my_campaign"]["id"]),
            json={"title": title},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context.setdefault("created_scenes", []).append(response.json())


@given(parsers.parse('I create a scene named "{title}" with a read-aloud body'))
def create_scene_with_a_body(client: AsyncClient, context: dict, title: str):
    response = _run(
        client.post(
            _scenes(context["my_campaign"]["id"]),
            json={"title": title, "body": READ_ALOUD},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context.setdefault("created_scenes", []).append(response.json())


@when("I retrieve the scene by its ID")
def retrieve_scene(client: AsyncClient, context: dict):
    scene = _my_scene(context)
    context["response"] = _run(
        client.get(
            f"{_scenes(context['my_campaign']['id'])}{scene['id']}",
            headers=_auth_headers(context),
        )
    )


@when("I list the scenes in my campaign")
def list_scenes(client: AsyncClient, context: dict):
    context["response"] = _run(client.get(_scenes(context["my_campaign"]["id"]), headers=_auth_headers(context)))


@when("I list the scenes in the other game masters campaign")
def list_the_other_game_masters_scenes(client: AsyncClient, context: dict):
    other = context["other_game_master"]
    context["response"] = _run(client.get(_scenes(other["campaign"]["id"]), headers=_auth_headers(context)))


@when("I retrieve the other game masters scene through their campaign")
def retrieve_their_scene_through_their_campaign(client: AsyncClient, context: dict):
    """The campaign refuses first, so nothing inside it is ever looked at."""
    other = context["other_game_master"]
    context["response"] = _run(
        client.get(
            f"{_scenes(other['campaign']['id'])}{other['scene']['id']}",
            headers=_auth_headers(context),
        )
    )


@when("I retrieve the other game masters scene through my campaign")
def retrieve_their_scene_through_my_campaign(client: AsyncClient, context: dict):
    """A real scene id, a campaign I really do run — and still nothing.

    This is the one the token exists for: the campaign check passes, so the only thing
    left refusing is `SceneAccess` asking whether the row belongs to the campaign it was
    reached through.
    """
    other = context["other_game_master"]
    context["response"] = _run(
        client.get(
            f"{_scenes(context['my_campaign']['id'])}{other['scene']['id']}",
            headers=_auth_headers(context),
        )
    )


@when("I mark the scene as done")
def mark_the_scene_as_done(client: AsyncClient, context: dict):
    scene = _my_scene(context)
    context["response"] = _run(
        client.put(
            f"{_scenes(context['my_campaign']['id'])}{scene['id']}",
            json={"title": scene["title"], "body": scene["body"], "status": "done"},
            headers=_auth_headers(context),
        )
    )


@when(parsers.parse('I rewrite the scene "{title}"'))
def rewrite_the_scene(client: AsyncClient, context: dict, title: str):
    scene = _my_scene(context, title)
    context["response"] = _run(
        client.put(
            f"{_scenes(context['my_campaign']['id'])}{scene['id']}",
            json={"title": title, "body": READ_ALOUD, "status": "done"},
            headers=_auth_headers(context),
        )
    )


@when("I rewrite the other game masters scene through my campaign")
def rewrite_their_scene(client: AsyncClient, context: dict):
    other = context["other_game_master"]
    context["response"] = _run(
        client.put(
            f"{_scenes(context['my_campaign']['id'])}{other['scene']['id']}",
            json={"title": "Stolen", "body": "", "status": "planned"},
            headers=_auth_headers(context),
        )
    )


@when("I delete the scene")
def delete_the_scene(client: AsyncClient, context: dict):
    scene = _my_scene(context)
    context["response"] = _run(
        client.delete(
            f"{_scenes(context['my_campaign']['id'])}{scene['id']}",
            headers=_auth_headers(context),
        )
    )


@when("I delete the other game masters scene through my campaign")
def delete_their_scene(client: AsyncClient, context: dict):
    other = context["other_game_master"]
    context["response"] = _run(
        client.delete(
            f"{_scenes(context['my_campaign']['id'])}{other['scene']['id']}",
            headers=_auth_headers(context),
        )
    )


@when("I create a scene in a campaign that does not exist")
def create_scene_in_a_campaign_that_does_not_exist(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.post(
            _scenes(str(uuid.uuid4())),
            json={"title": "Nowhere"},
            headers=_auth_headers(context),
        )
    )


@when("I delete my campaign")
def delete_my_campaign(client: AsyncClient, context: dict):
    response = _run(client.delete(f"/campaigns/{context['my_campaign']['id']}", headers=_auth_headers(context)))
    assert response.status_code == 204


@then(parsers.parse('I should see a scene named "{title}"'))
def should_see_a_scene_named(context: dict, title: str):
    assert context["response"].status_code == 200
    assert context["response"].json()["title"] == title


@then("the scene should be in my campaign")
def scene_should_be_in_my_campaign(context: dict):
    assert context["response"].json()["campaign_id"] == context["my_campaign"]["id"]


@then(parsers.parse("I should see {count:d} scenes"))
def should_see_n_scenes(context: dict, count: int):
    assert context["response"].status_code == 200
    assert len(context["response"].json()) == count


@then(parsers.parse('the scenes should read "{titles}"'))
def scenes_should_read(context: dict, titles: str):
    assert context["response"].status_code == 200
    assert [s["title"] for s in context["response"].json()] == titles.split(", ")


@then("the body should come back byte for byte")
def body_should_come_back_byte_for_byte(context: dict):
    assert context["response"].status_code == 200
    assert context["response"].json()["body"] == READ_ALOUD


@then("the body should be empty")
def body_should_be_empty(context: dict):
    assert context["response"].json()["body"] == ""


@then("the scene should be planned")
def scene_should_be_planned(context: dict):
    assert context["response"].json()["status"] == "planned"


@then("the scene should be done")
def scene_should_be_done(context: dict):
    assert context["response"].json()["status"] == "done"
