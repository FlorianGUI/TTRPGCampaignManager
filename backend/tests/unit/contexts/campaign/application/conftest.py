import uuid

import pytest

from app.contexts.campaign.application.campaign_service import CampaignService
from tests.unit.contexts.campaign.application.fakes import FakeCampaignRepository, FakeCharacterRepository


@pytest.fixture
def owner_id():
    return uuid.uuid4()


@pytest.fixture
def someone_else():
    return uuid.uuid4()


@pytest.fixture
def characters():
    return FakeCharacterRepository()


@pytest.fixture
def campaigns(characters: FakeCharacterRepository):
    """The campaign service, sharing one character store with whoever else wants it.

    Both services have to be looking at the same characters for the cascade to be worth
    testing: a campaign delete that swept a store nobody else could see would pass
    without proving anything.
    """
    return CampaignService(FakeCampaignRepository(), characters)
