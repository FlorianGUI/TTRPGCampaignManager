from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import PasswordResetId, UserId
from app.contexts.user.adapters.secondary.persistence.password_reset_model import PasswordResetModel
from app.contexts.user.domain.password_reset import PasswordReset
from app.contexts.user.domain.ports.password_reset_repository import PasswordResetRepository


class SqlAlchemyPasswordResetRepository(PasswordResetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, reset: PasswordReset) -> PasswordReset:
        # merge rather than add: spending a link saves the same row back, and an
        # insert-only save would collide on the primary key.
        await self._session.merge(
            PasswordResetModel(
                id=reset.id,
                user_id=reset.user_id,
                token_hash=reset.token_hash,
                created_at=reset.created_at,
                expires_at=reset.expires_at,
                used_at=reset.used_at,
            )
        )
        await self._session.commit()
        return reset

    async def find_by_hash(self, token_hash: str) -> PasswordReset | None:
        result = await self._session.execute(
            select(PasswordResetModel).where(PasswordResetModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return PasswordReset(
            id=PasswordResetId(model.id),
            user_id=UserId(model.user_id),
            token_hash=model.token_hash,
            created_at=model.created_at,
            expires_at=model.expires_at,
            used_at=model.used_at,
        )
