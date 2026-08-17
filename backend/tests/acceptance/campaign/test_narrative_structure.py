import asyncio
import uuid

from httpx import AsyncClient
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/narrative_structure.feature")


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _auth_headers(context: dict) -> dict:
    return _headers(context["token"])


def _acts(campaign_id: str) -> str:
    return f"/campaigns/{campaign_id}/acts/"


def _sequences(campaign_id: str) -> str:
    return f"/campaigns/{campaign_id}/sequences/"


def _scenes(campaign_id: str) -> str:
    return f"/campaigns/{campaign_id}/scenes/"


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _placement(campaign_id: str) -> str:
    return f"/campaigns/{campaign_id}/structure/placement"


def _place(client: AsyncClient, context: dict, body: dict, campaign_id: str | None = None):
    context["response"] = _run(
        client.put(
            _placement(campaign_id or _mine(context)),
            json=body,
            headers=_auth_headers(context),
        )
    )


def _record(context: dict, kind: str, id_key: str = "scene") -> dict:
    """The record under test, from whichever shape the last call answered with.

    A retrieve answers with the record itself; a placement answers with the whole
    tree (#109), because a move can shift rows nobody touched. These steps are
    shared by both kinds of scenario, so they ask for the record rather than
    assuming the envelope.
    """
    body = context["response"].json()
    if kind not in body:
        return body

    wanted = context[id_key]["id"]
    return next(record for record in body[kind] if record["id"] == wanted)


def _mine(context: dict) -> str:
    return context["my_campaign"]["id"]


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


@given(parsers.parse('I create an act named "{title}" in my campaign'))
def create_act(client: AsyncClient, context: dict, title: str):
    response = _run(client.post(_acts(_mine(context)), json={"title": title}, headers=_auth_headers(context)))
    assert response.status_code == 201
    context.setdefault("acts", []).append(response.json())


@given(parsers.parse('I create an act named "{title}" in my second campaign'))
def create_act_elsewhere(client: AsyncClient, context: dict, title: str):
    """An act I really do own, in a campaign I really do run — just not this one.

    Deliberately not the other game master's: that would be refused by the reach check,
    and the scenario would pass even if the same-campaign rule were deleted.
    """
    response = _run(
        client.post(
            _acts(context["my_other_campaign"]["id"]),
            json={"title": title},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context["act_elsewhere"] = response.json()


@given(parsers.parse('I create a sequence named "{title}" under that act'))
def create_sequence_under_act(client: AsyncClient, context: dict, title: str):
    response = _run(
        client.post(
            _sequences(_mine(context)),
            json={"title": title, "act_id": context["acts"][0]["id"]},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context["sequence"] = response.json()


@given(parsers.parse('I create a sequence named "{title}" in my campaign'))
def create_loose_sequence(client: AsyncClient, context: dict, title: str):
    response = _run(client.post(_sequences(_mine(context)), json={"title": title}, headers=_auth_headers(context)))
    assert response.status_code == 201
    context["sequence"] = response.json()


@given(parsers.parse('I create a scene named "{title}" under that sequence'))
def create_scene_under_sequence(client: AsyncClient, context: dict, title: str):
    response = _run(
        client.post(
            _scenes(_mine(context)),
            json={"title": title, "sequence_id": context["sequence"]["id"]},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context.setdefault("first_scene", response.json())
    context["scene"] = response.json()


@given(parsers.parse('I create a scene named "{title}" under that act'))
def create_scene_under_act(client: AsyncClient, context: dict, title: str):
    response = _run(
        client.post(
            _scenes(_mine(context)),
            json={"title": title, "act_id": context["acts"][0]["id"]},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context.setdefault("first_scene", response.json())
    context["scene"] = response.json()


@given(parsers.parse('I create a scene named "{title}" in my campaign'))
def create_loose_scene(client: AsyncClient, context: dict, title: str):
    response = _run(client.post(_scenes(_mine(context)), json={"title": title}, headers=_auth_headers(context)))
    assert response.status_code == 201
    # `scene` is always the most recent; `first_scene` is the anchor a drop names.
    context.setdefault("first_scene", response.json())
    context["scene"] = response.json()


@when("I list the scenes in my campaign")
def list_scenes(client: AsyncClient, context: dict):
    context["response"] = _run(client.get(_scenes(_mine(context)), headers=_auth_headers(context)))


@when("I list the acts in my campaign")
def list_acts(client: AsyncClient, context: dict):
    context["response"] = _run(client.get(_acts(_mine(context)), headers=_auth_headers(context)))


@when("I list the acts in the other game masters campaign")
def list_their_acts(client: AsyncClient, context: dict):
    other = context["other_game_master"]
    context["response"] = _run(client.get(_acts(other["campaign"]["id"]), headers=_auth_headers(context)))


@when("I retrieve the sequence by its ID")
def retrieve_sequence(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.get(
            f"{_sequences(_mine(context))}{context['sequence']['id']}",
            headers=_auth_headers(context),
        )
    )


@when("I retrieve the scene by its ID")
def retrieve_scene(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.get(f"{_scenes(_mine(context))}{context['scene']['id']}", headers=_auth_headers(context))
    )


@when("I create a scene naming both that act and that sequence")
def create_scene_with_two_parents(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.post(
            _scenes(_mine(context)),
            json={
                "title": "Ambiguous",
                "act_id": context["acts"][0]["id"],
                "sequence_id": context["sequence"]["id"],
            },
            headers=_auth_headers(context),
        )
    )


@when("I create a scene in my campaign under that act")
def create_scene_under_a_foreign_act(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.post(
            _scenes(_mine(context)),
            json={"title": "Stolen", "act_id": context["act_elsewhere"]["id"]},
            headers=_auth_headers(context),
        )
    )


@when("I create a sequence in my campaign under that act")
def create_sequence_under_a_foreign_act(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.post(
            _sequences(_mine(context)),
            json={"title": "Stolen", "act_id": context["act_elsewhere"]["id"]},
            headers=_auth_headers(context),
        )
    )


@when("I create a scene in my campaign under an act that does not exist")
def create_scene_under_a_missing_act(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.post(
            _scenes(_mine(context)),
            json={"title": "Nowhere", "act_id": str(uuid.uuid4())},
            headers=_auth_headers(context),
        )
    )


@when("I move the scene under the second act")
def move_scene_to_second_act(client: AsyncClient, context: dict):
    _place(
        client,
        context,
        {
            "item": {"id": context["scene"]["id"], "kind": "scene"},
            "parent": {"id": context["acts"][1]["id"], "kind": "act"},
        },
    )


@when("I move the scene to the campaign")
def move_scene_to_campaign(client: AsyncClient, context: dict):
    _place(client, context, {"item": {"id": context["scene"]["id"], "kind": "scene"}})


@when("I move the scene under that act")
def move_scene_under_a_foreign_act(client: AsyncClient, context: dict):
    _place(
        client,
        context,
        {
            "item": {"id": context["scene"]["id"], "kind": "scene"},
            "parent": {"id": context["act_elsewhere"]["id"], "kind": "act"},
        },
    )


@when("I rewrite the sequence")
def rewrite_sequence(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.put(
            f"{_sequences(_mine(context))}{context['sequence']['id']}",
            json={"title": "The Causeway, rewritten", "description": "Getting across."},
            headers=_auth_headers(context),
        )
    )


@when("I retrieve the act by its ID")
def retrieve_act(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.get(f"{_acts(_mine(context))}{context['acts'][0]['id']}", headers=_auth_headers(context))
    )


@when(parsers.parse('I rename the act to "{title}"'))
def rename_act(client: AsyncClient, context: dict, title: str):
    context["response"] = _run(
        client.put(
            f"{_acts(_mine(context))}{context['acts'][0]['id']}",
            json={"title": title},
            headers=_auth_headers(context),
        )
    )


@when("I delete the act")
def delete_act(client: AsyncClient, context: dict):
    """An empty one. What a non-empty act does is #80's open question and PR 3's."""
    context["response"] = _run(
        client.delete(f"{_acts(_mine(context))}{context['acts'][0]['id']}", headers=_auth_headers(context))
    )


@when("I list the sequences in my campaign")
def list_sequences(client: AsyncClient, context: dict):
    context["response"] = _run(client.get(_sequences(_mine(context)), headers=_auth_headers(context)))


@when("I move the sequence under that act")
def move_sequence_under_act(client: AsyncClient, context: dict):
    _place(
        client,
        context,
        {
            "item": {"id": context["sequence"]["id"], "kind": "sequence"},
            "parent": {"id": context["acts"][0]["id"], "kind": "act"},
        },
    )


@when("I move the sequence to the campaign")
def move_sequence_to_campaign(client: AsyncClient, context: dict):
    _place(client, context, {"item": {"id": context["sequence"]["id"], "kind": "sequence"}})


@when("I delete the sequence")
def delete_sequence(client: AsyncClient, context: dict):
    context["response"] = _run(
        client.delete(f"{_sequences(_mine(context))}{context['sequence']['id']}", headers=_auth_headers(context))
    )


@when("I drop the second scene at the top")
def drop_second_scene_at_top(client: AsyncClient, context: dict):
    """No anchor is the head of the list, which is what a drop above everything means."""
    _place(client, context, {"item": {"id": context["scene"]["id"], "kind": "scene"}})


@when("I drop the last scene after the first")
def drop_last_scene_after_first(client: AsyncClient, context: dict):
    _place(
        client,
        context,
        {
            "item": {"id": context["scene"]["id"], "kind": "scene"},
            "after": {"id": context["first_scene"]["id"], "kind": "scene"},
        },
    )


@when("I drop the second act at the top")
def drop_second_act_at_top(client: AsyncClient, context: dict):
    _place(client, context, {"item": {"id": context["acts"][1]["id"], "kind": "act"}})


@when("I drop the scene into the second act")
def drop_scene_into_second_act(client: AsyncClient, context: dict):
    """Parent and place in one call — the drag that crosses acts and lands somewhere."""
    _place(
        client,
        context,
        {
            "item": {"id": context["scene"]["id"], "kind": "scene"},
            "parent": {"id": context["acts"][1]["id"], "kind": "act"},
        },
    )


@when("I drop the campaigns scene after the one in the act")
def drop_after_a_stranger(client: AsyncClient, context: dict):
    """A real scene of this campaign, but not a sibling of where this one is going."""
    _place(
        client,
        context,
        {
            "item": {"id": context["scene"]["id"], "kind": "scene"},
            "after": {"id": context["first_scene"]["id"], "kind": "scene"},
        },
    )


@given(parsers.parse('I create a scene named "{title}" with a read-aloud body'))
def create_scene_with_a_body(client: AsyncClient, context: dict, title: str):
    response = _run(
        client.post(
            _scenes(_mine(context)),
            json={"title": title, "body": ":::read-aloud\nThe gate does not swing.\n:::"},
            headers=_auth_headers(context),
        )
    )
    assert response.status_code == 201
    context["scene"] = response.json()


@when("I read the structure of my campaign")
def read_structure(client: AsyncClient, context: dict):
    context["response"] = _run(client.get(f"/campaigns/{_mine(context)}/structure/", headers=_auth_headers(context)))


@when("I read the structure of the other game masters campaign")
def read_their_structure(client: AsyncClient, context: dict):
    other = context["other_game_master"]
    context["response"] = _run(
        client.get(f"/campaigns/{other['campaign']['id']}/structure/", headers=_auth_headers(context))
    )


@when("I delete my campaign")
def delete_my_campaign(client: AsyncClient, context: dict):
    response = _run(client.delete(f"/campaigns/{_mine(context)}", headers=_auth_headers(context)))
    assert response.status_code == 204


@then(parsers.parse('the scenes should read "{titles}"'))
def scenes_should_read(context: dict, titles: str):
    assert context["response"].status_code == 200
    assert [s["title"] for s in context["response"].json()] == titles.split(", ")


@then(parsers.parse('the acts should read "{titles}"'))
def acts_should_read(context: dict, titles: str):
    assert context["response"].status_code == 200
    assert [a["title"] for a in context["response"].json()] == titles.split(", ")


@then("the sequence should be under that act")
def sequence_under_that_act(context: dict):
    assert context["response"].status_code == 200
    assert _record(context, "sequences", "sequence")["act_id"] == context["acts"][0]["id"]


@then("the sequence should be under no act")
def sequence_under_no_act(context: dict):
    assert _record(context, "sequences", "sequence")["act_id"] is None


@then("the scene should be under that sequence")
def scene_under_that_sequence(context: dict):
    assert context["response"].status_code == 200
    assert _record(context, "scenes")["sequence_id"] == context["sequence"]["id"]


@then("the scene should be under that act")
def scene_under_that_act(context: dict):
    assert _record(context, "scenes")["act_id"] == context["acts"][0]["id"]


@then("the scene should be under the second act")
def scene_under_second_act(context: dict):
    assert context["response"].status_code == 200
    assert _record(context, "scenes")["act_id"] == context["acts"][1]["id"]


@then("the scene should be under no act")
def scene_under_no_act(context: dict):
    assert _record(context, "scenes")["act_id"] is None


@then("the scene should be under no sequence")
def scene_under_no_sequence(context: dict):
    assert _record(context, "scenes")["sequence_id"] is None


@then("the scene should be first among its siblings")
def scene_first_among_siblings(context: dict):
    """A new parent starts its own numbering rather than continuing the campaign's."""
    assert context["response"].json()["position"] == 1024


@then(parsers.parse('I should see an act named "{title}"'))
def should_see_an_act_named(context: dict, title: str):
    assert context["response"].status_code == 200
    assert context["response"].json()["title"] == title


@then("the acts should be empty")
def acts_should_be_empty(context: dict):
    assert context["response"].status_code == 200
    assert context["response"].json() == []


@then(parsers.parse("I should see {count:d} sequences"))
def should_see_n_sequences(context: dict, count: int):
    assert context["response"].status_code == 200
    assert len(context["response"].json()) == count


@then(parsers.parse("the structure should hold {acts:d} act, {sequences:d} sequence and {scenes:d} scene"))
def structure_should_hold(context: dict, acts: int, sequences: int, scenes: int):
    assert context["response"].status_code == 200
    tree = context["response"].json()
    assert (len(tree["acts"]), len(tree["sequences"]), len(tree["scenes"])) == (acts, sequences, scenes)


@then("no scene in the structure should carry a body")
def no_body_in_the_structure(context: dict):
    """The reason this endpoint exists, asserted against the wire rather than the code."""
    assert context["response"].status_code == 200
    assert all("body" not in scene for scene in context["response"].json()["scenes"])


@then("the request should be rejected as invalid")
def rejected_as_invalid(context: dict):
    """422, not 404: the caller sent a contradiction rather than reached for something
    that is not theirs, and telling them so costs nothing."""
    assert context["response"].status_code == 422


@when("I place the second act at the top of the outline")
def place_second_act_at_top(client: AsyncClient, context: dict):
    """The same gesture as the acts route, through the one endpoint that serves every level."""
    _place(client, context, {"item": {"id": context["acts"][1]["id"], "kind": "act"}})


@when("I place the scene under that act through the outline")
def place_scene_under_act(client: AsyncClient, context: dict):
    _place(
        client,
        context,
        {
            "item": {"id": context["scene"]["id"], "kind": "scene"},
            "parent": {"id": context["acts"][0]["id"], "kind": "act"},
        },
    )


@when("I place the second act under the first through the outline")
def place_act_under_act(client: AsyncClient, context: dict):
    """An act hangs off the campaign and nothing else — the tree has no meaning for this."""
    _place(
        client,
        context,
        {
            "item": {"id": context["acts"][1]["id"], "kind": "act"},
            "parent": {"id": context["acts"][0]["id"], "kind": "act"},
        },
    )


@when("I place the scene after that sequence through the outline")
def place_scene_after_sequence(client: AsyncClient, context: dict):
    """The gesture #101 existed for: one parent, one list, whatever kind the rows are."""
    _place(
        client,
        context,
        {
            "item": {"id": context["scene"]["id"], "kind": "scene"},
            "parent": {"id": context["acts"][0]["id"], "kind": "act"},
            "after": {"id": context["sequence"]["id"], "kind": "sequence"},
        },
    )


@when("I place that act after itself through the outline")
def place_act_after_itself(client: AsyncClient, context: dict):
    act = context["acts"][0]
    _place(
        client,
        context,
        {"item": {"id": act["id"], "kind": "act"}, "after": {"id": act["id"], "kind": "act"}},
    )


@given("another game master has a campaign with an act")
def another_game_master_has_an_act(client: AsyncClient, context: dict, register_user):
    token = register_user()
    campaign = _run(client.post("/campaigns/", json={"name": "Fen Wardens"}, headers=_headers(token)))
    assert campaign.status_code == 201
    act = _run(client.post(_acts(campaign.json()["id"]), json={"title": "Theirs"}, headers=_headers(token)))
    assert act.status_code == 201
    context["their_act"] = act.json()


@when("I place their act through my outline")
def place_their_act(client: AsyncClient, context: dict):
    """A well-formed body naming a row of someone else's campaign. The ids in the body are
    resolved against my tokens, so this is "not found" and does not say whose it was."""
    _place(client, context, {"item": {"id": context["their_act"]["id"], "kind": "act"}})


@then(parsers.parse("the structure should hold {acts:d} acts, {sequences:d} sequences and {scenes:d} scenes"))
def structure_should_hold_plural(context: dict, acts: int, sequences: int, scenes: int):
    body = context["response"].json()
    assert (len(body["acts"]), len(body["sequences"]), len(body["scenes"])) == (acts, sequences, scenes)


@then(parsers.parse('the acts in the answer should read "{titles}"'))
def acts_in_the_answer_should_read(context: dict, titles: str):
    """Read off the placement's own response — the point of answering with the tree."""
    assert [a["title"] for a in context["response"].json()["acts"]] == titles.split(", ")


@then("the scene in the answer should be under that act")
def scene_in_the_answer_is_under_the_act(context: dict):
    scene = context["response"].json()["scenes"][0]
    assert scene["act_id"] == context["acts"][0]["id"]
    assert scene["sequence_id"] is None


@then("the scene should sit below the sequence in the act")
def scene_sits_below_the_sequence(context: dict):
    """One number line per parent: the scene's position is above the sequence's, so the
    outline draws it second. Before #101 both sat at POSITION_GAP and a uuid decided."""
    assert context["response"].status_code == 200, context["response"].json()
    body = context["response"].json()
    sequence = next(s for s in body["sequences"] if s["id"] == context["sequence"]["id"])
    scene = next(s for s in body["scenes"] if s["id"] == context["scene"]["id"])
    assert scene["act_id"] == sequence["act_id"]
    assert scene["position"] > sequence["position"]
