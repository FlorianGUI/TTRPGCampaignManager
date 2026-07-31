import uuid

from app.contexts.campaign.domain.campaign import Campaign


class TestIsVisibleTo:
    def test_the_owner_sees_their_own_table(self):
        owner_id = uuid.uuid4()
        assert Campaign(name="Greyfen", owner_id=owner_id).is_visible_to(owner_id) is True

    def test_nobody_else_does(self):
        assert Campaign(name="Greyfen", owner_id=uuid.uuid4()).is_visible_to(uuid.uuid4()) is False


class TestIsEditableBy:
    def test_the_owner_may_change_their_own_table(self):
        owner_id = uuid.uuid4()
        assert Campaign(name="Greyfen", owner_id=owner_id).is_editable_by(owner_id) is True

    def test_nobody_else_may(self):
        assert Campaign(name="Greyfen", owner_id=uuid.uuid4()).is_editable_by(uuid.uuid4()) is False
