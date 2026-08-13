import uuid

import pytest

from app.common.access import Unsafe
from app.common.ids import UserId
from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess, CampaignNotReachable
from app.contexts.campaign.domain.narrative_access import SceneAccess
from app.contexts.campaign.domain.position import POSITION_GAP
from app.contexts.campaign.domain.scene import Scene, SceneNotAvailable


def _scene_in(access: SceneAccess, title: str) -> Scene:
    return Scene(title=title, campaign_id=access.campaign_id, position=POSITION_GAP)


def _access_for(name: str) -> SceneAccess:
    owner_id = UserId(uuid.uuid4())
    return CampaignAccess(owner_id).narrative_at(Unsafe(Campaign(name=name, owner_id=owner_id))).scenes


class TestNarrativeAt:
    """The one thing anywhere that builds a token for the tree."""

    def test_the_owner_is_handed_a_token_for_this_campaign(self):
        owner_id = UserId(uuid.uuid4())
        campaign = Campaign(name="Greyfen", owner_id=owner_id)

        access = CampaignAccess(owner_id).narrative_at(Unsafe(campaign)).scenes

        assert access.campaign_id == campaign.id
        assert access.viewer_id == owner_id

    def test_nobody_else_is_handed_one(self):
        """The reach check, and the only place in the tree it is asked.

        This is what #31 widens. If this test ever needs a second copy somewhere below,
        the rule has forked and #80's whole authorisation section has been undone.
        """
        campaign = Campaign(name="Greyfen", owner_id=UserId(uuid.uuid4()))

        with pytest.raises(CampaignNotReachable):
            CampaignAccess(UserId(uuid.uuid4())).narrative_at(Unsafe(campaign))

    def test_a_campaign_that_is_not_there_answers_the_same_way(self):
        """A campaign refusal, not a scene one: the caller never gets far enough to be
        told anything about what is inside."""
        with pytest.raises(CampaignNotReachable):
            CampaignAccess(UserId(uuid.uuid4())).narrative_at(Unsafe(None))


class TestSceneAccess:
    """Today a token means you run the campaign, so it permits everything in it.

    The passing cases read as tautologies on purpose — the same reason the character
    ones do. #80 is explicit that this rule never forks from the campaign's, so if these
    ever stop agreeing it should be because someone deliberately changed
    `NarrativeAccess`, with these tests contradicting them.
    """

    @pytest.fixture
    def access(self) -> SceneAccess:
        return _access_for("Greyfen")

    def test_the_game_master_may_read_a_scene_in_their_campaign(self, access: SceneAccess):
        scene = _scene_in(access, "The parley at Stonegate")

        assert access.readable(Unsafe(scene)) is scene

    def test_the_game_master_may_edit_a_scene_in_their_campaign(self, access: SceneAccess):
        scene = _scene_in(access, "The parley at Stonegate")

        assert access.editable(Unsafe(scene)) is scene

    def test_the_game_master_may_delete_a_scene_in_their_campaign(self, access: SceneAccess):
        scene = _scene_in(access, "The parley at Stonegate")

        assert access.deletable(Unsafe(scene)) is scene

    def test_a_scene_that_is_not_there_cannot_be_read(self, access: SceneAccess):
        with pytest.raises(SceneNotAvailable):
            access.readable(Unsafe(None))

    def test_a_scene_that_is_not_there_cannot_be_edited(self, access: SceneAccess):
        with pytest.raises(SceneNotAvailable):
            access.editable(Unsafe(None))

    def test_a_scene_that_is_not_there_cannot_be_deleted(self, access: SceneAccess):
        with pytest.raises(SceneNotAvailable):
            access.deletable(Unsafe(None))


class TestASceneInAnotherCampaign:
    """The only per-record question the tree has: does this row belong to the campaign
    I was reached through. A real scene, a real id, a token for somewhere else."""

    @pytest.fixture
    def access(self) -> SceneAccess:
        return _access_for("Greyfen")

    @pytest.fixture
    def elsewhere(self) -> SceneAccess:
        return _access_for("Fen Wardens")

    def test_cannot_be_read(self, access: SceneAccess, elsewhere: SceneAccess):
        with pytest.raises(SceneNotAvailable):
            access.readable(Unsafe(_scene_in(elsewhere, "The muster")))

    def test_cannot_be_edited(self, access: SceneAccess, elsewhere: SceneAccess):
        with pytest.raises(SceneNotAvailable):
            access.editable(Unsafe(_scene_in(elsewhere, "The muster")))

    def test_cannot_be_deleted(self, access: SceneAccess, elsewhere: SceneAccess):
        with pytest.raises(SceneNotAvailable):
            access.deletable(Unsafe(_scene_in(elsewhere, "The muster")))

    def test_answers_exactly_as_a_scene_that_does_not_exist(self, access: SceneAccess, elsewhere: SceneAccess):
        """Both become 404s, so they must not be told apart here either."""
        with pytest.raises(SceneNotAvailable) as in_another_campaign:
            access.readable(Unsafe(_scene_in(elsewhere, "The muster")))
        with pytest.raises(SceneNotAvailable) as never_existed:
            access.readable(Unsafe(None))

        assert in_another_campaign.value.detail == never_existed.value.detail
