import uuid

import pytest

from app.contexts.campaign.domain.campaign import Campaign, CampaignAccess, CampaignNotReachable
from app.contexts.campaign.domain.character import Character, CharacterNotAvailable
from app.contexts.campaign.domain.character_access import CharacterAccess


def _character_at(access: CharacterAccess, name: str) -> Character:
    return Character(name=name, owner_id=access.viewer_id, campaign_id=access.campaign_id)


class TestCampaignAccess:
    def test_the_owner_may_read_their_own_table(self):
        owner_id = uuid.uuid4()

        assert CampaignAccess(owner_id).readable(Campaign(name="Greyfen", owner_id=owner_id)) is not None

    def test_nobody_else_may_read_it(self):
        campaign = Campaign(name="Greyfen", owner_id=uuid.uuid4())

        with pytest.raises(CampaignNotReachable):
            CampaignAccess(uuid.uuid4()).readable(campaign)

    def test_a_campaign_that_is_not_there_answers_the_same_way(self):
        """The 404 decision, at the level where it is decided."""
        with pytest.raises(CampaignNotReachable):
            CampaignAccess(uuid.uuid4()).readable(None)

    def test_the_owner_may_edit_and_delete_their_own_table(self):
        owner_id = uuid.uuid4()
        campaign = Campaign(name="Greyfen", owner_id=owner_id)
        access = CampaignAccess(owner_id)

        assert access.editable(campaign) is campaign
        assert access.deletable(campaign) is campaign

    def test_nobody_else_may_edit_or_delete_it(self):
        campaign = Campaign(name="Greyfen", owner_id=uuid.uuid4())
        access = CampaignAccess(uuid.uuid4())

        with pytest.raises(CampaignNotReachable):
            access.editable(campaign)
        with pytest.raises(CampaignNotReachable):
            access.deletable(campaign)


class TestCharactersAt:
    """The one thing anywhere that builds a CharacterAccess."""

    def test_the_owner_is_handed_a_token_for_this_table(self):
        owner_id = uuid.uuid4()
        campaign = Campaign(name="Greyfen", owner_id=owner_id)

        access = CampaignAccess(owner_id).characters_at(campaign)

        assert access == CharacterAccess(campaign_id=campaign.id, viewer_id=owner_id)

    def test_a_stranger_is_handed_nothing(self):
        """The check the whole design rests on: no token, and nothing below it is callable."""
        campaign = Campaign(name="Greyfen", owner_id=uuid.uuid4())

        with pytest.raises(CampaignNotReachable):
            CampaignAccess(uuid.uuid4()).characters_at(campaign)

    def test_a_campaign_that_is_not_there_hands_out_nothing_either(self):
        with pytest.raises(CampaignNotReachable):
            CampaignAccess(uuid.uuid4()).characters_at(None)


class TestCharacterAccess:
    """Today a token means you run the table, so it permits everything at it.

    The passing cases read as tautologies on purpose. They are here so that #31 — which
    makes all three depend on whose sheet it is — changes tests that already exist rather
    than arriving with nothing to contradict.
    """

    @pytest.fixture
    def access(self):
        owner_id = uuid.uuid4()
        return CampaignAccess(owner_id).characters_at(Campaign(name="Greyfen", owner_id=owner_id))

    def test_the_game_master_may_read_a_sheet_at_their_table(self, access: CharacterAccess):
        character = _character_at(access, "Aragorn")

        assert access.readable(character) is character

    def test_the_game_master_may_edit_a_sheet_at_their_table(self, access: CharacterAccess):
        character = _character_at(access, "Aragorn")

        assert access.editable(character) is character

    def test_the_game_master_may_delete_a_sheet_at_their_table(self, access: CharacterAccess):
        character = _character_at(access, "Aragorn")

        assert access.deletable(character) is character

    def test_a_sheet_that_is_not_there_cannot_be_read(self, access: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            access.readable(None)

    def test_a_sheet_that_is_not_there_cannot_be_edited(self, access: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            access.editable(None)

    def test_a_sheet_that_is_not_there_cannot_be_deleted(self, access: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            access.deletable(None)


class TestASheetAtAnotherTable:
    """The rule that used to be a WHERE clause, now somewhere it can be read.

    A real character, fetched by a real id, through a token for a different campaign —
    which is exactly what an unscoped `find_by_id` now hands back. These are the tests
    that were impossible to write while the rule lived in SQL.
    """

    @pytest.fixture
    def access(self):
        owner_id = uuid.uuid4()
        return CampaignAccess(owner_id).characters_at(Campaign(name="Greyfen", owner_id=owner_id))

    @pytest.fixture
    def elsewhere(self):
        owner_id = uuid.uuid4()
        return CampaignAccess(owner_id).characters_at(Campaign(name="Fen Wardens", owner_id=owner_id))

    def test_cannot_be_read(self, access: CharacterAccess, elsewhere: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            access.readable(_character_at(elsewhere, "Boromir"))

    def test_cannot_be_edited(self, access: CharacterAccess, elsewhere: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            access.editable(_character_at(elsewhere, "Boromir"))

    def test_cannot_be_deleted(self, access: CharacterAccess, elsewhere: CharacterAccess):
        with pytest.raises(CharacterNotAvailable):
            access.deletable(_character_at(elsewhere, "Boromir"))

    def test_answers_exactly_as_a_sheet_that_does_not_exist(self, access: CharacterAccess, elsewhere: CharacterAccess):
        """Both become 404s, so they must not be told apart here either."""
        with pytest.raises(CharacterNotAvailable) as at_another_table:
            access.readable(_character_at(elsewhere, "Boromir"))
        with pytest.raises(CharacterNotAvailable) as never_existed:
            access.readable(None)

        assert at_another_table.value.detail == never_existed.value.detail
