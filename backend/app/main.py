from fastapi import FastAPI

from app.common.error_handlers import setup_error_handlers
from app.common.health.health_route import router as health_router
from app.common.security.cors import setup_cors
from app.common.security.rate_limiter import setup_rate_limiter
from app.contexts.campaign.adapters.primary.api.routers.campaigns import router as campaigns_router
from app.contexts.campaign.adapters.primary.api.routers.characters import router as characters_router
from app.contexts.campaign.adapters.primary.api.routers.scenes import router as scenes_router
from app.contexts.source.adapters.primary.api.routers.sources import router as sources_router
from app.contexts.user.adapters.primary.api.routers.auth import router as auth_router
from app.contexts.user.adapters.primary.api.routers.users import router as users_router

app = FastAPI(
    title="TTRPG Campaign Manager",
    version="0.1.0",
    description="API for gathering TTRPG source material, character sheets, and campaign info for the Game Master",
)

setup_cors(app)
setup_rate_limiter(app)
setup_error_handlers(app)

app.include_router(health_router)
app.include_router(campaigns_router)
app.include_router(characters_router)
app.include_router(scenes_router)
app.include_router(sources_router)
app.include_router(users_router)
app.include_router(auth_router)
