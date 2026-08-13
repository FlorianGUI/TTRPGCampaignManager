import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.access import Unsafe
from app.common.ids import ActId, SequenceId, UserId
from app.contexts.campaign.adapters.secondary.persistence.act_repository import SqlAlchemyActRepository
from app.contexts.campaign.adapters.secondary.persistence.scene_repository import SqlAlchemySceneRepository
from app.contexts.campaign.adapters.secondary.persistence.sequence_repository import SqlAlchemySequenceRepository
from app.contexts.campaign.domain.act import Act
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess
from app.contexts.campaign.domain.narrative_access import Narrative
from app.contexts.campaign.domain.position import POSITION_GAP
from app.contexts.campaign.domain.scene import Scene
from app.contexts.campaign.domain.sequence import Sequence


@pytest.fixture
def owner_id() -> UserId:
    return UserId(uuid.uuid4())


@pytest.fixture
def narrative(owner_id: UserId) -> Narrative:
    campaign = Campaign(name="The Drowning of Greyfen", owner_id=owner_id)
    return CampaignAccess(owner_id).narrative_at(Unsafe(campaign))


@pytest.fixture
def elsewhere(owner_id: UserId) -> Narrative:
    return CampaignAccess(owner_id).narrative_at(Unsafe(Campaign(name="Fen Wardens", owner_id=owner_id)))


@pytest.fixture
def acts(db: AsyncSession) -> SqlAlchemyActRepository:
    return SqlAlchemyActRepository(db)


@pytest.fixture
def sequences(db: AsyncSession) -> SqlAlchemySequenceRepository:
    return SqlAlchemySequenceRepository(db)


@pytest.fixture
def scenes(db: AsyncSession) -> SqlAlchemySceneRepository:
    return SqlAlchemySceneRepository(db)


class TestActRepository:
    async def test_persists_and_reads_back(self, acts: SqlAlchemyActRepository, narrative: Narrative):
        act = Act(
            title="Act I — Water Rising",
            campaign_id=narrative.campaign_id,
            position=POSITION_GAP,
            description="The party earns the Wardens' trust.",
        )
        await acts.save(act)

        found = (await acts.find_by_id(act.id)).unchecked

        assert found is not None
        assert found.title == "Act I — Water Rising"
        assert found.description == "The party earns the Wardens' trust."
        assert found.position == POSITION_GAP

    async def test_orders_by_position(self, acts: SqlAlchemyActRepository, narrative: Narrative):
        for title, position in [("Act III", 3072), ("Act I", 1024), ("Act II", 2048)]:
            await acts.save(Act(title=title, campaign_id=narrative.campaign_id, position=position))

        assert [a.title for a in await acts.find_all_in(narrative.acts)] == ["Act I", "Act II", "Act III"]

    async def test_last_position_is_none_for_a_campaign_with_no_acts(
        self, acts: SqlAlchemyActRepository, narrative: Narrative
    ):
        assert await acts.last_position_in(narrative.acts) is None

    async def test_does_not_see_another_campaigns_acts(
        self, acts: SqlAlchemyActRepository, narrative: Narrative, elsewhere: Narrative
    ):
        await acts.save(Act(title="Theirs", campaign_id=elsewhere.campaign_id, position=POSITION_GAP))

        assert await acts.find_all_in(narrative.acts) == []
        assert await acts.last_position_in(narrative.acts) is None


class TestSequenceRepository:
    async def test_persists_its_act(self, sequences: SqlAlchemySequenceRepository, narrative: Narrative):
        act_id = ActId(uuid.uuid4())
        sequence = Sequence(
            title="The Causeway", campaign_id=narrative.campaign_id, position=POSITION_GAP, act_id=act_id
        )
        await sequences.save(sequence)

        found = (await sequences.find_by_id(sequence.id)).unchecked

        assert found is not None
        assert found.act_id == act_id

    async def test_a_sequence_under_the_campaign_keeps_a_null_act(
        self, sequences: SqlAlchemySequenceRepository, narrative: Narrative
    ):
        sequence = Sequence(title="Loose", campaign_id=narrative.campaign_id, position=POSITION_GAP)
        await sequences.save(sequence)

        found = (await sequences.find_by_id(sequence.id)).unchecked

        assert found is not None
        assert found.act_id is None

    async def test_positions_are_counted_per_act(self, sequences: SqlAlchemySequenceRepository, narrative: Narrative):
        """The `IS NULL` case, which is the one `= NULL` gets silently wrong.

        Two sequences under the campaign and one under an act. Asking for the act's last
        position must not see the campaign's, and asking for the campaign's must not see
        the act's — an equality comparison against NULL matches nothing and would answer
        `None` to both.
        """
        act_id = ActId(uuid.uuid4())
        await sequences.save(Sequence(title="Loose one", campaign_id=narrative.campaign_id, position=1024))
        await sequences.save(Sequence(title="Loose two", campaign_id=narrative.campaign_id, position=2048))
        await sequences.save(
            Sequence(title="In the act", campaign_id=narrative.campaign_id, position=1024, act_id=act_id)
        )

        assert await sequences.last_position_under(narrative.sequences, None) == 2048
        assert await sequences.last_position_under(narrative.sequences, act_id) == 1024

    async def test_last_position_under_an_empty_act_is_none(
        self, sequences: SqlAlchemySequenceRepository, narrative: Narrative
    ):
        await sequences.save(Sequence(title="Loose", campaign_id=narrative.campaign_id, position=1024))

        assert await sequences.last_position_under(narrative.sequences, ActId(uuid.uuid4())) is None

    async def test_lists_every_sequence_whatever_it_hangs_off(
        self, sequences: SqlAlchemySequenceRepository, narrative: Narrative
    ):
        """Campaign-wide, because the read that matters is the whole tree at once."""
        act_id = ActId(uuid.uuid4())
        await sequences.save(Sequence(title="Loose", campaign_id=narrative.campaign_id, position=1024))
        await sequences.save(
            Sequence(title="In the act", campaign_id=narrative.campaign_id, position=2048, act_id=act_id)
        )

        assert len(await sequences.find_all_in(narrative.sequences)) == 2

    async def test_deleting_a_campaigns_sequences_leaves_another_alone(
        self, sequences: SqlAlchemySequenceRepository, narrative: Narrative, elsewhere: Narrative
    ):
        await sequences.save(Sequence(title="Theirs", campaign_id=elsewhere.campaign_id, position=1024))

        await sequences.delete_all_in(narrative.sequences)

        assert len(await sequences.find_all_in(elsewhere.sequences)) == 1


class TestSceneParentageRoundTrips:
    async def test_a_scene_under_an_act(self, scenes: SqlAlchemySceneRepository, narrative: Narrative):
        act_id = ActId(uuid.uuid4())
        scene = Scene(title="Interlude", campaign_id=narrative.campaign_id, position=POSITION_GAP, act_id=act_id)
        await scenes.save(scene)

        found = (await scenes.find_by_id(scene.id)).unchecked

        assert found is not None
        assert found.act_id == act_id
        assert found.sequence_id is None

    async def test_a_scene_under_a_sequence(self, scenes: SqlAlchemySceneRepository, narrative: Narrative):
        sequence_id = SequenceId(uuid.uuid4())
        scene = Scene(
            title="Arrival at dusk",
            campaign_id=narrative.campaign_id,
            position=POSITION_GAP,
            sequence_id=sequence_id,
        )
        await scenes.save(scene)

        found = (await scenes.find_by_id(scene.id)).unchecked

        assert found is not None
        assert found.sequence_id == sequence_id
        assert found.act_id is None

    async def test_positions_are_counted_per_parent(self, scenes: SqlAlchemySceneRepository, narrative: Narrative):
        act_id = ActId(uuid.uuid4())
        await scenes.save(Scene(title="Loose", campaign_id=narrative.campaign_id, position=4096))
        await scenes.save(Scene(title="In the act", campaign_id=narrative.campaign_id, position=1024, act_id=act_id))

        assert await scenes.last_position_under(narrative.scenes, None, None) == 4096
        assert await scenes.last_position_under(narrative.scenes, act_id, None) == 1024

    async def test_a_move_survives_the_round_trip(self, scenes: SqlAlchemySceneRepository, narrative: Narrative):
        """merge() writes every column, so a reparent must not leave the old one behind."""
        act_id = ActId(uuid.uuid4())
        sequence_id = SequenceId(uuid.uuid4())
        scene = Scene(title="The muster", campaign_id=narrative.campaign_id, position=POSITION_GAP, act_id=act_id)
        await scenes.save(scene)

        scene.move_under(None, sequence_id, 2048)
        await scenes.save(scene)

        found = (await scenes.find_by_id(scene.id)).unchecked
        assert found is not None
        assert found.act_id is None
        assert found.sequence_id == sequence_id
        assert found.position == 2048
