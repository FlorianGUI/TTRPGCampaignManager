from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.user.adapters.secondary.persistence.user_model import UserModel
from app.contexts.user.domain.ports.user_repository import UserRepository
from app.contexts.user.domain.user import User


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
        )
        self._session.add(model)
        await self._session.commit()
        return user

    async def find_by_id(self, id: UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_by_username(self, username: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.username == username))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            username=model.username,
            email=model.email,
            hashed_password=model.hashed_password,
        )
