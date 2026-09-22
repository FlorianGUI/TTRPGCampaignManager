"""Seed a source owned by the default user."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import UserId
from app.contexts.source.adapters.secondary.persistence.source_repository import SqlAlchemySourceRepository
from app.contexts.source.application.source_service import SourceService

TITLE = "Guide de Rivebois et alentours"


async def seed_source(db: AsyncSession, owner_id: UserId) -> bool:
    """Create the demo source if it doesn't exist yet. Returns whether it created one."""
    service = SourceService(SqlAlchemySourceRepository(db))
    if any(source.title == TITLE for source in await service.list_for(owner_id)):
        return False
    await service.create(TITLE, owner_id)
    return True
