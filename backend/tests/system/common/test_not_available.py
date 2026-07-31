import uuid

import pytest
from httpx import AsyncClient

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
