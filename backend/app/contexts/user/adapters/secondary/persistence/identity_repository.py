from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import IdentityId, UserId
from app.contexts.user.adapters.secondary.persistence.identity_model import IdentityModel
from app.contexts.user.domain.identity import Identity, Provider
from app.contexts.user.domain.ports.identity_repository import IdentityRepository


class SqlAlchemyIdentityRepository(IdentityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, identity: Identity) -> Identity:
        model = IdentityModel(
            id=identity.id,
            user_id=identity.user_id,
            provider=identity.provider.value,
            subject=identity.subject,
        )
        self._session.add(model)
        await self._session.commit()
        return identity

    async def find_by_subject(self, provider: Provider, subject: str) -> Identity | None:
        result = await self._session.execute(
            select(IdentityModel).where(IdentityModel.provider == provider.value, IdentityModel.subject == subject)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def find_for_user(self, user_id: UserId) -> list[Identity]:
        result = await self._session.execute(select(IdentityModel).where(IdentityModel.user_id == user_id))
        return [self._to_domain(model) for model in result.scalars()]

    @staticmethod
    def _to_domain(model: IdentityModel) -> Identity:
        return Identity(
            id=IdentityId(model.id),
            user_id=UserId(model.user_id),
            provider=Provider(model.provider),
            subject=model.subject,
        )
