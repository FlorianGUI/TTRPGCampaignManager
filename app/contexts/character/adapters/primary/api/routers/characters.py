from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth import get_current_user
from app.contexts.character.adapters.primary.api.schemas.character import CharacterCreate, CharacterResponse
from app.contexts.character.adapters.secondary.persistence.character_repository import SqlAlchemyCharacterRepository
from app.contexts.character.application.character_service import CharacterService
from app.database import get_db

router = APIRouter(prefix="/characters", tags=["characters"], dependencies=[Depends(get_current_user)])


def get_service(db: AsyncSession = Depends(get_db)) -> CharacterService:
    return CharacterService(SqlAlchemyCharacterRepository(db))


@router.post("/", response_model=CharacterResponse, status_code=201)
async def create_character(
    body: CharacterCreate,
    service: CharacterService = Depends(get_service),
):
    character = await service.create(body.name, body.character_class)
    return CharacterResponse(**character.__dict__)


@router.get("/", response_model=list[CharacterResponse])
async def list_characters(service: CharacterService = Depends(get_service)):
    return [CharacterResponse(**c.__dict__) for c in await service.list_all()]


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: UUID,
    service: CharacterService = Depends(get_service),
):
    character = await service.get(character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found")
    return CharacterResponse(**character.__dict__)