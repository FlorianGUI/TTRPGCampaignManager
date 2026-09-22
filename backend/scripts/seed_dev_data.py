"""Seed a default user and a filled-in campaign for local manual testing.

A CLI entry point, not a context of its own — it composes the same application services
the routers do, the way any primary adapter is meant to. Nothing here reaches into a
repository the services don't already expose, and nothing here re-derives a rule the
services already enforce (positions, sibling ordering, the campaign as aggregate root).

Idempotent: re-running finds the default user and the demo campaign by name and does
nothing further, so `just seed` is safe to run after every fresh `just migrate`.

Run with `just seed`.
"""

import asyncio

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
from app.contexts.campaign.domain.scene import SceneStatus
from app.contexts.source.adapters.secondary.persistence.source_repository import SqlAlchemySourceRepository
from app.contexts.source.application.source_service import SourceService
from app.contexts.user.adapters.secondary.persistence.identity_repository import SqlAlchemyIdentityRepository
from app.contexts.user.adapters.secondary.persistence.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from app.contexts.user.adapters.secondary.persistence.user_repository import SqlAlchemyUserRepository
from app.contexts.user.application.user_service import UserService
from app.database import AsyncSessionLocal

DEFAULT_USERNAME = "gm"
DEFAULT_EMAIL = "gm@example.local"
DEFAULT_PASSWORD = "DevPassword123!"
DEMO_CAMPAIGN_NAME = "Les Landes Oubliées"


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        users = SqlAlchemyUserRepository(db)
        user_service = UserService(users, SqlAlchemyRefreshTokenRepository(db), SqlAlchemyIdentityRepository(db))

        user = await users.find_by_username(DEFAULT_USERNAME)
        if user is None:
            # register() also mints a session, which a seed script has no use for — the
            # user is re-read below rather than threading a Session through this function
            # for a value it would never use.
            await user_service.register(DEFAULT_USERNAME, DEFAULT_EMAIL, DEFAULT_PASSWORD)
            user = await users.find_by_username(DEFAULT_USERNAME)
        assert user is not None
        print(f"User: {DEFAULT_USERNAME} / {DEFAULT_PASSWORD}")

        campaigns = SqlAlchemyCampaignRepository(db)
        if any(c.name == DEMO_CAMPAIGN_NAME for c in await campaigns.find_all_for(user.id)):
            print(f"Campaign '{DEMO_CAMPAIGN_NAME}' already exists — nothing more to seed.")
            return

        campaign_service = CampaignService(
            campaigns,
            SqlAlchemyCharacterRepository(db),
            SqlAlchemySceneRepository(db),
            SqlAlchemySequenceRepository(db),
            SqlAlchemyActRepository(db),
        )
        campaign = await campaign_service.create(
            DEMO_CAMPAIGN_NAME,
            user.id,
            "Une campagne de démonstration, déjà remplie pour vérifier l'app sans tout construire à la main.",
        )

        narrative = await campaign_service.narrative_at(campaign.id, user.id)
        character_access = await campaign_service.characters_at(campaign.id, user.id)

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
        source_service = SourceService(SqlAlchemySourceRepository(db))

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

        await source_service.create("Guide de Rivebois et alentours", user.id)

        print(f"Campaign '{DEMO_CAMPAIGN_NAME}' seeded: 2 acts, 5 scenes, 2 characters, 1 source.")


if __name__ == "__main__":
    asyncio.run(seed())
