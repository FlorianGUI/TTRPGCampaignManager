import uuid

import pytest

from app.contexts.campaign.domain.access import CampaignAccess, CampaignNotReachable
from app.contexts.campaign.domain.campaign import Campaign


class TestGrant:
    def test_the_owner_is_handed_a_token_for_this_table(self):
        owner_id = uuid.uuid4()
        campaign = Campaign(name="Greyfen", owner_id=owner_id)

        access = campaign.grant(owner_id)

        assert access == CampaignAccess(campaign_id=campaign.id, viewer_id=owner_id)

    def test_a_stranger_is_handed_nothing(self):
        """The check the whole design rests on: no token, and nothing below it is callable."""
        campaign = Campaign(name="Greyfen", owner_id=uuid.uuid4())

        with pytest.raises(CampaignNotReachable):
            campaign.grant(uuid.uuid4())


class TestNewCharacter:
    def test_stamps_the_sheet_with_the_table_and_the_viewer(self):
        owner_id = uuid.uuid4()
        campaign = Campaign(name="Greyfen", owner_id=owner_id)

        character = campaign.grant(owner_id).new_character("Aragorn", "A ranger of the North")

        assert character.name == "Aragorn"
        assert character.description == "A ranger of the North"
        assert character.owner_id == owner_id
        assert character.campaign_id == campaign.id

    def test_description_is_optional(self):
        owner_id = uuid.uuid4()
        campaign = Campaign(name="Greyfen", owner_id=owner_id)

        assert campaign.grant(owner_id).new_character("Aragorn").description is None


class TestWhatTheTokenPermits:
    """Today a token means you run the table, so it permits everything at it.

    These read as tautologies on purpose. They are here so that #31 — which makes both
    answers depend on whose sheet it is — changes a test that already exists rather than
    arriving with nothing to contradict.
    """

    def test_the_game_master_may_edit_a_sheet_at_their_table(self):
        owner_id = uuid.uuid4()
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        access = campaign.grant(owner_id)

        assert access.may_edit(access.new_character("Aragorn")) is True

    def test_the_game_master_may_delete_a_sheet_at_their_table(self):
        owner_id = uuid.uuid4()
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        access = campaign.grant(owner_id)

        assert access.may_delete(access.new_character("Aragorn")) is True
