"""Seed a campaign already carrying acts, a sequence, scenes and characters.

Composes `CampaignService` and its narrative-tree siblings the way the routers do —
nothing here reaches into a repository the services don't already expose, and nothing
here re-derives a rule the services already enforce (positions, sibling ordering).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import CampaignId, UserId
from app.contexts.campaign.adapters.secondary.persistence.act_repository import SqlAlchemyActRepository
from app.contexts.campaign.adapters.secondary.persistence.campaign_repository import SqlAlchemyCampaignRepository
from app.contexts.campaign.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.campaign.adapters.secondary.persistence.scene_repository import SqlAlchemySceneRepository
from app.contexts.campaign.adapters.secondary.persistence.sequence_repository import SqlAlchemySequenceRepository
from app.contexts.campaign.application.act_service import ActService
from app.contexts.campaign.application.campaign_service import CampaignService
from app.contexts.campaign.application.character_service import CharacterService
from app.contexts.campaign.application.scene_service import SceneService
from app.contexts.campaign.application.sequence_service import SequenceService
from app.contexts.campaign.application.siblings import SiblingGroups
from app.contexts.campaign.domain.campaign import Campaign
from app.contexts.campaign.domain.scene import SceneStatus

NAME = "Les Landes Oubliées"


async def seed_campaign(db: AsyncSession, owner_id: UserId) -> tuple[Campaign, bool]:
    """Return the demo campaign, creating and filling it the first time only.

    The `bool` says whether this call created it, so the caller can print an accurate
    message — everything this seeds is written once, at creation, never patched onto an
    existing campaign on a later run.
    """
    campaigns = SqlAlchemyCampaignRepository(db)
    campaign_service = CampaignService(
        campaigns,
        SqlAlchemyCharacterRepository(db),
        SqlAlchemySceneRepository(db),
        SqlAlchemySequenceRepository(db),
        SqlAlchemyActRepository(db),
    )

    for existing in await campaign_service.list_for(owner_id):
        if existing.name == NAME:
            return existing, False

    campaign = await campaign_service.create(
        NAME,
        owner_id,
        "Une campagne de démonstration, déjà remplie pour vérifier l'app sans tout construire à la main.",
    )
    await _fill(db, campaign_service, campaign.id, owner_id)
    return campaign, True


async def _fill(db: AsyncSession, campaign_service: CampaignService, campaign_id: CampaignId, owner_id: UserId) -> None:
    narrative = await campaign_service.narrative_at(campaign_id, owner_id)
    character_access = await campaign_service.characters_at(campaign_id, owner_id)

    siblings = SiblingGroups(
        SqlAlchemyActRepository(db), SqlAlchemySequenceRepository(db), SqlAlchemySceneRepository(db)
    )
    act_service = ActService(
        SqlAlchemyActRepository(db), SqlAlchemySequenceRepository(db), SqlAlchemySceneRepository(db), siblings
    )
    sequence_service = SequenceService(
        SqlAlchemySequenceRepository(db), SqlAlchemyActRepository(db), SqlAlchemySceneRepository(db), siblings
    )
    scene_service = SceneService(
        SqlAlchemySceneRepository(db), SqlAlchemyActRepository(db), SqlAlchemySequenceRepository(db), siblings
    )
    character_service = CharacterService(SqlAlchemyCharacterRepository(db))

    act1 = await act_service.create(narrative, "Acte I — L'arrivée", "Les personnages rejoignent Rivebois.")
    chemin = await sequence_service.create(narrative, "En chemin", "Le trajet jusqu'au village.", act_id=act1.id)
    await scene_service.create(
        narrative,
        "L'embuscade du pont",
        "Une bande de gobelins attaque la caravane à la tombée de la nuit.",
        SceneStatus.DONE,
        sequence_id=chemin.id,
    )
    await scene_service.create(
        narrative,
        "Arrivée à Rivebois",
        "Le village semble étrangement calme pour un soir de marché.",
        SceneStatus.DONE,
        act_id=act1.id,
    )

    act2 = await act_service.create(narrative, "Acte II — Le mystère", "Les disparitions du village.")
    await scene_service.create(
        narrative,
        "L'auberge du Cerf Blanc",
        "Les PJ recueillent des rumeurs sur les disparitions récentes.",
        SceneStatus.PLANNED,
        act_id=act2.id,
    )
    await scene_service.create(
        narrative,
        "La cave oubliée",
        "Un passage secret s'ouvre sous l'auberge.",
        SceneStatus.PLANNED,
        act_id=act2.id,
    )

    await scene_service.create(
        narrative,
        "Un rêve étrange",
        "À développer si le groupe s'y intéresse — posée directement sur la campagne.",
        SceneStatus.SKIPPED,
    )

    await character_service.create(character_access, "Corvin Ashryn", "Rôdeur elfe, guide engagé à Rivebois.")
    await character_service.create(character_access, "Mère Yolane", "Aubergiste. Sait plus qu'elle ne le dit.")
