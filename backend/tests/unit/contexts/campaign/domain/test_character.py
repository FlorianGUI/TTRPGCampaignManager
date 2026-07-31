import uuid

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
