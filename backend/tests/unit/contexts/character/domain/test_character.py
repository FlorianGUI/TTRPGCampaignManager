import uuid

from app.contexts.character.domain.character import Character


class TestCharacter:
    def test_default_level_is_1(self):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=uuid.uuid4())
        assert character.level == 1

    def test_starts_at_no_campaign(self):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=uuid.uuid4())
        assert character.campaign_id is None

    def test_id_is_auto_generated(self):
        character = Character(name="Aragorn", character_class="Ranger", owner_id=uuid.uuid4())
        assert character.id is not None

    def test_two_characters_have_different_ids(self):
        owner_id = uuid.uuid4()
        a = Character(name="Aragorn", character_class="Ranger", owner_id=owner_id)
        b = Character(name="Legolas", character_class="Archer", owner_id=owner_id)
        assert a.id != b.id
