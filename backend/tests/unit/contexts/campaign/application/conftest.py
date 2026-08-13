import uuid

import pytest

from app.common.ids import UserId
from app.contexts.campaign.application.campaign_service import CampaignService
from tests.unit.contexts.campaign.application.fakes import (
    FakeActRepository,
    FakeCampaignRepository,
    FakeCharacterRepository,
    FakeSceneRepository,
    FakeSequenceRepository,
)


@pytest.fixture
def owner_id() -> UserId:
    return UserId(uuid.uuid4())


@pytest.fixture
def someone_else() -> UserId:
    return UserId(uuid.uuid4())


@pytest.fixture
def characters():
    return FakeCharacterRepository()


@pytest.fixture
def scenes():
    return FakeSceneRepository()


@pytest.fixture
def sequences():
    return FakeSequenceRepository()


@pytest.fixture
def acts():
    return FakeActRepository()


@pytest.fixture
def campaigns(
    characters: FakeCharacterRepository,
    scenes: FakeSceneRepository,
    sequences: FakeSequenceRepository,
    acts: FakeActRepository,
):
    """The campaign service, sharing one store of each with whoever else wants it.

    Every service has to be looking at the same rows for the cascade to be worth testing:
    a campaign delete that swept a store nobody else could see would pass without proving
    anything.
    """
    return CampaignService(FakeCampaignRepository(), characters, scenes, sequences, acts)
