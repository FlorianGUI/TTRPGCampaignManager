from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.contexts.source.adapters.primary.api.schemas.source import SourceCreate, SourceResponse, SourceUpdate
from app.contexts.source.adapters.secondary.persistence.source_repository import SqlAlchemySourceRepository
from app.contexts.source.application.source_service import SourceService
from app.contexts.user.domain.user import User
from app.database import get_db

router = APIRouter(prefix="/sources", tags=["sources"], dependencies=[Depends(get_current_user)])

# A source the caller does not own answers exactly as one that does not exist — same
# status, same detail — so the response never confirms that an id belongs to someone.
NOT_FOUND = HTTPException(status_code=404, detail="Source not found")


def get_service(db: AsyncSession = Depends(get_db)) -> SourceService:
    return SourceService(SqlAlchemySourceRepository(db))


@router.post("/", response_model=SourceResponse, status_code=201)
async def create_source(
    body: SourceCreate,
    user: User = Depends(get_current_user),
    service: SourceService = Depends(get_service),
):
    source = await service.create(body.title, user.id)
    return SourceResponse(**source.__dict__)


@router.get("/", response_model=list[SourceResponse])
async def list_sources(
    user: User = Depends(get_current_user),
    service: SourceService = Depends(get_service),
):
    return [SourceResponse(**s.__dict__) for s in await service.list_for(user.id)]


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: UUID,
    user: User = Depends(get_current_user),
    service: SourceService = Depends(get_service),
):
    source = await service.get_for(source_id, user.id)
    if source is None:
        raise NOT_FOUND
    return SourceResponse(**source.__dict__)


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: UUID,
    body: SourceUpdate,
    user: User = Depends(get_current_user),
    service: SourceService = Depends(get_service),
):
    source = await service.rename(source_id, user.id, body.title)
    if source is None:
        raise NOT_FOUND
    return SourceResponse(**source.__dict__)
