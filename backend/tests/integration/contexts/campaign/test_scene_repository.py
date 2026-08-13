import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.common.ids import SceneId, UserId
from app.contexts.campaign.adapters.secondary.persistence.scene_repository import SqlAlchemySceneRepository
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.narrative_access import SceneAccess
from app.contexts.campaign.domain.position import POSITION_GAP
from app.contexts.campaign.domain.scene import Scene, SceneStatus

# The tokens are built through CampaignAccess.narrative_at rather than by hand: it is the
# only constructor application code has, so building them any other way here would test a
# repository nothing in the app can actually call.

# Deliberately awkward: a container directive with an attribute, two inline ones, an em
# dash and a trailing newline. If any layer between here and the column decides to be
# helpful — normalising newlines, stripping, escaping — one of those goes.
READ_ALOUD = (
    ':::read-aloud{label="Boxed text"}\n'
    "The gate does not swing. It sinks —\n"
    ":::\n\n"
    ":npc[Torvald] wants :item[the rubbing].\n"
)


def _scene_in(access: SceneAccess, title: str, position: int = POSITION_GAP, **overrides) -> Scene:
    return Scene(title=title, campaign_id=access.campaign_id, position=position, **overrides)


@pytest.fixture
def repository(db: AsyncSession) -> SqlAlchemySceneRepository:
    return SqlAlchemySceneRepository(db)


@pytest.fixture
def owner_id() -> UserId:
    return UserId(uuid.uuid4())


@pytest.fixture
def access(owner_id: UserId) -> SceneAccess:
    campaign = Campaign(name="The Drowning of Greyfen", owner_id=owner_id)
    return CampaignAccess(owner_id).narrative_at(Unsafe(campaign))


@pytest.fixture
def other_access(owner_id: UserId) -> SceneAccess:
    return CampaignAccess(owner_id).narrative_at(Unsafe(Campaign(name="Fen Wardens", owner_id=owner_id)))


class TestSave:
    async def test_returns_the_saved_scene(self, repository: SqlAlchemySceneRepository, access: SceneAccess):
        scene = _scene_in(access, "The parley at Stonegate")

        assert await repository.save(scene) == scene

    async def test_persists_every_field(self, repository: SqlAlchemySceneRepository, access: SceneAccess):
        scene = _scene_in(access, "The sunken arch", body=READ_ALOUD, status=SceneStatus.PLAYED, position=2048)
        await repository.save(scene)

        found = (await repository.find_by_id(scene.id)).unchecked

        assert found is not None
        assert found.title == "The sunken arch"
        assert found.body == READ_ALOUD
        assert found.status is SceneStatus.PLAYED
        assert found.campaign_id == access.campaign_id
        assert found.position == 2048

    async def test_a_body_round_trips_byte_for_byte(self, repository: SqlAlchemySceneRepository, access: SceneAccess):
        """#80's acceptance line, against a real column.

        The dialect goes in and comes back unchanged — no normalising of newlines, no
        stripping, no escaping of the directive syntax. This is the test that would fail
        the day someone taught the backend to read this field.
        """
        scene = _scene_in(access, "The sunken arch", body=READ_ALOUD)
        await repository.save(scene)

        found = (await repository.find_by_id(scene.id)).unchecked

        assert found is not None
        assert found.body == READ_ALOUD

    async def test_saving_again_updates_rather_than_duplicates(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess
    ):
        scene = _scene_in(access, "The parley")
        await repository.save(scene)

        scene.revise("The parley at Stonegate", READ_ALOUD, SceneStatus.PLAYED)
        await repository.save(scene)

        assert len(await repository.find_all_in(access)) == 1

    async def test_saving_again_keeps_the_position(self, repository: SqlAlchemySceneRepository, access: SceneAccess):
        """The merge() hazard #78 found, on the column where it would hurt most.

        merge() copies the transient object onto the loaded row, so a field left out of
        the SceneModel above is erased. For `position` that does not merely blank a
        value — it drops the scene out of narrative order on every edit.
        """
        scene = _scene_in(access, "The sunken arch", position=4096)
        await repository.save(scene)

        scene.revise("The sunken arch", READ_ALOUD, SceneStatus.PLAYED)
        await repository.save(scene)

        found = (await repository.find_by_id(scene.id)).unchecked
        assert found is not None
        assert found.position == 4096

    async def test_saving_again_keeps_the_created_time(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess
    ):
        scene = _scene_in(access, "The parley")
        await repository.save(scene)
        created = scene.created_at

        scene.revise("The parley at Stonegate", "", SceneStatus.PLAYED)
        await repository.save(scene)

        found = (await repository.find_by_id(scene.id)).unchecked
        assert found is not None
        assert found.created_at == created


class TestFindById:
    async def test_finds_nothing_when_the_scene_does_not_exist(self, repository: SqlAlchemySceneRepository):
        assert (await repository.find_by_id(SceneId(uuid.uuid4()))).unchecked is None

    async def test_hands_back_a_scene_from_any_campaign(
        self, repository: SqlAlchemySceneRepository, other_access: SceneAccess
    ):
        """Unscoped on purpose — the rule lives in `SceneAccess`, not in this WHERE clause.

        Asserting on what the repository returned is exactly what `unchecked` is for, and
        this is the test that documents the cost the port describes.
        """
        elsewhere = _scene_in(other_access, "Session zero")
        await repository.save(elsewhere)

        assert (await repository.find_by_id(elsewhere.id)).unchecked is not None


class TestFindAllIn:
    async def test_finds_nothing_in_a_campaign_with_no_scenes(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess
    ):
        assert await repository.find_all_in(access) == []

    async def test_orders_by_position_and_not_by_insertion(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess
    ):
        """The ordering is the query's, which is what the fake is copying.

        Saved deliberately out of order: a repository that returned insertion order would
        pass every unit test in the suite and hand a game master their story backwards.
        """
        await repository.save(_scene_in(access, "The nesting pair", position=3072))
        await repository.save(_scene_in(access, "Arrival at dusk", position=1024))
        await repository.save(_scene_in(access, "The sunken arch", position=2048))

        titles = [s.title for s in await repository.find_all_in(access)]

        assert titles == ["Arrival at dusk", "The sunken arch", "The nesting pair"]

    async def test_breaks_a_tie_by_id_so_a_list_cannot_reorder_itself(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess
    ):
        """Two scenes appended in the same instant can share a position (see the service).

        Without the second sort key equal positions come back in whatever order Postgres
        likes, and two identical requests can disagree — which is how a list starts
        skipping and repeating rows. Asking twice is the only way to test it.
        """
        await repository.save(_scene_in(access, "One", position=1024))
        await repository.save(_scene_in(access, "Two", position=1024))
        await repository.save(_scene_in(access, "Three", position=1024))

        first = [s.id for s in await repository.find_all_in(access)]
        second = [s.id for s in await repository.find_all_in(access)]

        assert first == second == sorted(first)

    async def test_does_not_find_another_campaigns_scenes(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess, other_access: SceneAccess
    ):
        await repository.save(_scene_in(other_access, "Session zero"))

        assert await repository.find_all_in(access) == []


class TestLastPositionIn:
    async def test_answers_nothing_for_a_campaign_with_no_scenes(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess
    ):
        """MAX over an empty set is NULL, which is what `position_after(None)` expects."""
        assert await repository.last_position_in(access) is None

    async def test_answers_the_highest_position(self, repository: SqlAlchemySceneRepository, access: SceneAccess):
        await repository.save(_scene_in(access, "Arrival at dusk", position=1024))
        await repository.save(_scene_in(access, "The nesting pair", position=3072))
        await repository.save(_scene_in(access, "The sunken arch", position=2048))

        assert await repository.last_position_in(access) == 3072

    async def test_ignores_another_campaigns_scenes(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess, other_access: SceneAccess
    ):
        await repository.save(_scene_in(other_access, "Session zero", position=99999))

        assert await repository.last_position_in(access) is None


class TestDelete:
    async def test_removes_the_scene(self, repository: SqlAlchemySceneRepository, access: SceneAccess):
        scene = _scene_in(access, "The rubbing")
        await repository.save(scene)

        await repository.delete(scene.id)

        assert (await repository.find_by_id(scene.id)).unchecked is None

    async def test_deleting_something_absent_is_not_an_error(self, repository: SqlAlchemySceneRepository):
        await repository.delete(SceneId(uuid.uuid4()))


class TestDeleteAllIn:
    async def test_empties_the_campaign(self, repository: SqlAlchemySceneRepository, access: SceneAccess):
        await repository.save(_scene_in(access, "Arrival at dusk", position=1024))
        await repository.save(_scene_in(access, "The sunken arch", position=2048))

        await repository.delete_all_in(access)

        assert await repository.find_all_in(access) == []

    async def test_leaves_another_campaign_alone(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess, other_access: SceneAccess
    ):
        elsewhere = _scene_in(other_access, "Session zero")
        await repository.save(elsewhere)

        await repository.delete_all_in(access)

        assert len(await repository.find_all_in(other_access)) == 1

    async def test_emptying_a_campaign_with_no_scenes_is_not_an_error(
        self, repository: SqlAlchemySceneRepository, access: SceneAccess
    ):
        await repository.delete_all_in(access)
