import uuid
from datetime import UTC, datetime

from app.common.ids import UserId
from app.contexts.campaign.domain.campaign import Campaign

# Far enough in the past that "did it move" needs no tolerance. Asserting that two
# `datetime.now()` calls differ would be a test of the clock's resolution, and one that
# fails on a fast machine.
LONG_AGO = datetime(2020, 1, 1, tzinfo=UTC)


class TestCampaign:
    def test_knows_when_it_was_made_the_moment_it_exists(self):
        """The whole reason the clock is in the domain (#78): no round trip first."""
        campaign = Campaign(name="Greyfen", owner_id=UserId(uuid.uuid4()))

        assert campaign.created_at is not None
        assert campaign.updated_at is not None

    def test_records_time_with_an_offset(self):
        """Naive timestamps are a bug waiting for the first player in another room."""
        campaign = Campaign(name="Greyfen", owner_id=UserId(uuid.uuid4()))

        assert campaign.created_at.tzinfo is not None
        assert campaign.updated_at.tzinfo is not None

    def test_revising_moves_the_updated_time(self):
        campaign = Campaign(name="Greyfen", owner_id=UserId(uuid.uuid4()))
        campaign.updated_at = LONG_AGO

        campaign.revise("The Hollow Beneath Greyfen", "A drowned village")

        assert campaign.updated_at > LONG_AGO

    def test_revising_leaves_the_created_time_alone(self):
        """A campaign is made once. Editing it is not making it again."""
        campaign = Campaign(name="Greyfen", owner_id=UserId(uuid.uuid4()))
        campaign.created_at = LONG_AGO

        campaign.revise("The Hollow Beneath Greyfen", None)

        assert campaign.created_at == LONG_AGO

    def test_revising_changes_what_the_campaign_says(self):
        campaign = Campaign(name="Greyfen", owner_id=UserId(uuid.uuid4()), description="A village")

        campaign.revise("The Hollow Beneath Greyfen", "A drowned village")

        assert campaign.name == "The Hollow Beneath Greyfen"
        assert campaign.description == "A drowned village"

    def test_revising_can_clear_the_description(self):
        campaign = Campaign(name="Greyfen", owner_id=UserId(uuid.uuid4()), description="A village")

        campaign.revise("Greyfen", None)

        assert campaign.description is None
