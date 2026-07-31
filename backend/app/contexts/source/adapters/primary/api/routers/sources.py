from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import SourceId
from app.common.security.auth import get_current_user
from app.contexts.source.adapters.primary.api.schemas.source import SourceCreate, SourceResponse, SourceUpdate
from app.contexts.source.adapters.secondary.persistence.source_repository import SqlAlchemySourceRepository
from app.contexts.source.application.source_service import SourceService
from app.contexts.user.domain.user import User
from app.database import get_db

# A source the caller does not own raises SourceNotAvailable exactly as one that does
# not exist, and one handler turns that into a 404 — so the response never confirms that
# an id belongs to someone. Nothing here decides that; there is nothing here to get
# wrong.
router = APIRouter(prefix="/sources", tags=["sources"], dependencies=[Depends(get_current_user)])


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
    source_id: SourceId,
    user: User = Depends(get_current_user),
    service: SourceService = Depends(get_service),
):
    source = await service.get_for(source_id, user.id)
    return SourceResponse(**source.__dict__)


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: SourceId,
    body: SourceUpdate,
    user: User = Depends(get_current_user),
    service: SourceService = Depends(get_service),
):
    source = await service.rename(source_id, user.id, body.title)
    return SourceResponse(**source.__dict__)


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: SourceId,
    user: User = Depends(get_current_user),
    service: SourceService = Depends(get_service),
):
    await service.delete(source_id, user.id)
