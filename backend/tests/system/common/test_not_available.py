import uuid

import pytest
from httpx import AsyncClient

from app.main import app

# The 404-not-403 decision in #12 is only worth anything if the two 404s are actually
# identical. Everywhere else asserts the status; nothing asserted the body, so a context
# could have drifted to a distinguishing message and every suite would still be green.
#
# This lives with the infrastructure rather than in a context because it is the one
# handler in app/common that all three go through, and the property is about them
# agreeing with each other.


PASSWORD = "testpass123"


async def _register(client: AsyncClient) -> str:
    username = f"user-{uuid.uuid4().hex[:8]}"
    await client.post(
        "/users/register",
        json={"username": username, "email": f"{username}@example.com", "password": PASSWORD},
    )
    response = await client.post("/users/login", data={"username": username, "password": PASSWORD})
    return str(response.json()["access_token"])


def _documented_404_fields(path: str) -> set[str]:
    """The fields the published schema promises a 404 body has.

    Checked against a real response rather than on its own, because documentation that
    has drifted from behaviour is worse than none. It rides along with an existing
    assertion instead of taking a test of its own: every test here registers users, and
    the suite already sits close to the rate limiter on /users/register.
    """
    schema = app.openapi()
    model = schema["paths"][path]["get"]["responses"]["404"]["content"]["application/json"]["schema"]
    return set(schema["components"]["schemas"][model["$ref"].rsplit("/", 1)[-1]]["properties"])


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def mine(client: AsyncClient) -> str:
    return await _register(client)


@pytest.fixture
async def theirs(client: AsyncClient) -> str:
    return await _register(client)


class TestSomeoneElsesRecordIsIndistinguishableFromNothing:
    async def test_for_a_source(self, client: AsyncClient, mine: str, theirs: str):
        created = await client.post("/sources/", json={"title": "Xanathars Guide"}, headers=_headers(theirs))

        not_mine = await client.get(f"/sources/{created.json()['id']}", headers=_headers(mine))
        never_existed = await client.get(f"/sources/{uuid.uuid4()}", headers=_headers(mine))

        assert not_mine.status_code == never_existed.status_code == 404
        assert not_mine.json() == never_existed.json() == {"detail": "Source not found"}
        assert set(never_existed.json()) == _documented_404_fields("/sources/{source_id}")

    async def test_for_a_campaign(self, client: AsyncClient, mine: str, theirs: str):
        created = await client.post("/campaigns/", json={"name": "Someone elses table"}, headers=_headers(theirs))

        not_mine = await client.get(f"/campaigns/{created.json()['id']}", headers=_headers(mine))
        never_existed = await client.get(f"/campaigns/{uuid.uuid4()}", headers=_headers(mine))

        assert not_mine.status_code == never_existed.status_code == 404
        assert not_mine.json() == never_existed.json() == {"detail": "Campaign not found"}

    async def test_for_a_character(self, client: AsyncClient, mine: str, theirs: str):
        """Reaching through a campaign I do run, so it is the sheet being hidden and not the table."""
        campaign = await client.post("/campaigns/", json={"name": "Greyfen"}, headers=_headers(mine))
        elsewhere = await client.post("/campaigns/", json={"name": "Theirs"}, headers=_headers(theirs))
        created = await client.post(
            f"/campaigns/{elsewhere.json()['id']}/characters/",
            json={"name": "Boromir"},
            headers=_headers(theirs),
        )

        at_my_table = f"/campaigns/{campaign.json()['id']}/characters"
        not_mine = await client.get(f"{at_my_table}/{created.json()['id']}", headers=_headers(mine))
        never_existed = await client.get(f"{at_my_table}/{uuid.uuid4()}", headers=_headers(mine))

        assert not_mine.status_code == never_existed.status_code == 404
        assert not_mine.json() == never_existed.json() == {"detail": "Character not found"}


class TestTheSchemaSaysSo:
    """The 404s have to be declared by hand, so something has to notice when they are not.

    FastAPI infers documented responses from signatures, and there are no `HTTPException`
    raises left in the routers — a domain exception travels out and a handler turns it
    into a response. Nothing connects those two for the schema generator, so a new route
    documents itself as never failing unless its author remembers `responses=`.
    """

    def test_every_route_with_a_path_parameter_documents_its_404(self):
        """The invariant that happens to be exactly true here.

        A path parameter means the route names a record, and naming a record you may not
        have is the one thing that answers 404 — including the two character collections,
        which sit under `{campaign_id}` and answer for the table before they ever look at
        a sheet. Routes without one (`/health`, `/users/login`, the two list endpoints)
        cannot 404 and correctly say nothing.
        """
        undocumented = [
            f"{verb.upper()} {path}"
            for path, operations in app.openapi()["paths"].items()
            if "{" in path
            for verb, operation in operations.items()
            if "404" not in operation["responses"]
        ]

        assert undocumented == []
