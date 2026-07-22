from app.contexts.character.domain.character import Character


class TestCharacter:
    def test_default_level_is_1(self):
        character = Character(name="Aragorn", character_class="Ranger")
        assert character.level == 1

    def test_id_is_auto_generated(self):
        character = Character(name="Aragorn", character_class="Ranger")
        assert character.id is not None

    def test_two_characters_have_different_ids(self):
        a = Character(name="Aragorn", character_class="Ranger")
        b = Character(name="Legolas", character_class="Archer")
        assert a.id != b.id
