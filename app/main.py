from fastapi import FastAPI

from app.common.health.health_route import router as health_router
from app.common.security.rate_limiter import setup_rate_limiter
from app.contexts.character.adapters.primary.api.routers.characters import router as characters_router
from app.contexts.user.adapters.primary.api.routers.users import router as users_router

app = FastAPI(
    title="D&D Character Sheet Creator",
    version="0.1.0",
    description="API for creating and managing D&D character sheets",
)

setup_rate_limiter(app)

app.include_router(health_router)
app.include_router(characters_router)
app.include_router(users_router)