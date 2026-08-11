import uuid
from datetime import UTC, datetime

from app.common.ids import CampaignId, UserId
from app.contexts.campaign.domain.character import Character


class TestCharacter:
    def test_starts_without_a_description(self):
        character = Character(name="Aragorn", owner_id=UserId(uuid.uuid4()), campaign_id=CampaignId(uuid.uuid4()))
        assert character.description is None

    def test_id_is_auto_generated(self):
        character = Character(name="Aragorn", owner_id=UserId(uuid.uuid4()), campaign_id=CampaignId(uuid.uuid4()))
        assert character.id is not None

    def test_two_characters_have_different_ids(self):
        owner_id = UserId(uuid.uuid4())
        campaign_id = CampaignId(uuid.uuid4())
        a = Character(name="Aragorn", owner_id=owner_id, campaign_id=campaign_id)
        b = Character(name="Legolas", owner_id=owner_id, campaign_id=campaign_id)
        assert a.id != b.id


class TestCharacterTimestamps:
    """The same contract as `Campaign`, restated because the sheet is a different entity.

    Not a copy for its own sake: `revise` is what makes `updated_at` true, and a service
    that assigns the fields directly would pass every other test in this file.
    """

    LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)

    def _character(self) -> Character:
        return Character(name="Aragorn", owner_id=UserId(uuid.uuid4()), campaign_id=CampaignId(uuid.uuid4()))

    def test_records_time_with_an_offset(self):
        character = self._character()

        assert character.created_at.tzinfo is not None
        assert character.updated_at.tzinfo is not None

    def test_revising_moves_the_updated_time(self):
        character = self._character()
        character.updated_at = self.LONG_AGO

        character.revise("Strider", "A ranger of the North")

        assert character.updated_at > self.LONG_AGO

    def test_revising_leaves_the_created_time_alone(self):
        character = self._character()
        character.created_at = self.LONG_AGO

        character.revise("Strider", None)

        assert character.created_at == self.LONG_AGO

    def test_revising_rewrites_the_sheet(self):
        character = self._character()

        character.revise("Strider", "A ranger of the North")

        assert character.name == "Strider"
        assert character.description == "A ranger of the North"
