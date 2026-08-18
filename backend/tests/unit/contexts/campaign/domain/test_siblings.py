import uuid

import pytest

from app.common.ids import CampaignId
from app.contexts.campaign.domain.scene import Scene
from app.contexts.campaign.domain.sequence import Sequence
from app.contexts.campaign.domain.siblings import AnchorNotAvailable, place_among


def a_scene(position: int) -> Scene:
    return Scene(title="x", campaign_id=CampaignId(uuid.uuid4()), position=position)


def a_sequence(position: int) -> Sequence:
    return Sequence(title="q", campaign_id=CampaignId(uuid.uuid4()), position=position)


class TestTheAnchorsOwnRefusal:
    """Which 404 a group answers with when the anchor is not in it.

    Not a detail: it used to be the caller's own, so a scene dropped after an id that did
    not resolve was told "Scene not found" — about the scene it had just asked to move,
    which was plainly there (#110). The wrong record, and it sends whoever reads it looking
    in the wrong place.
    """

    def test_an_anchor_outside_the_group_names_the_anchor(self):
        with pytest.raises(AnchorNotAvailable) as refused:
            place_among([a_scene(1024)], a_scene(2048), uuid.uuid4())

        assert "follow" in refused.value.detail
        assert "Scene" not in refused.value.detail

    def test_an_anchor_of_another_kind_is_perfectly_ordinary(self):
        """The whole of #101's fix, stated where the rule lives: a group spans kinds, so a
        scene may be dropped below the sequence above it and nothing here objects."""
        sequence, scene = a_sequence(1024), a_scene(2048)

        placement = place_among([sequence], scene, sequence.id)

        assert placement.ordered == [sequence, scene]
