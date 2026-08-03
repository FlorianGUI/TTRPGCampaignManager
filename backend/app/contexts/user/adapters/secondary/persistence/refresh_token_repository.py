from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import RefreshTokenId, SessionId, UserId
from app.contexts.user.adapters.secondary.persistence.refresh_token_model import RefreshTokenModel
from app.contexts.user.domain.ports.refresh_token_repository import RefreshTokenRepository
from app.contexts.user.domain.refresh_token import RefreshToken


class SqlAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, token: RefreshToken) -> RefreshToken:
        # merge() rather than add(): rotation saves a token that already exists, to record
        # that it has been spent, and issuance saves one that does not.
        await self._session.merge(
            RefreshTokenModel(
                id=token.id,
                user_id=token.user_id,
                session_id=token.session_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                revoked_at=token.revoked_at,
            )
        )
        await self._session.commit()
        return token

    async def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        statement = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def revoke_session(self, session_id: SessionId, at: datetime) -> None:
        # One statement rather than a read-modify-write loop, and `revoked_at IS NULL` in
        # the predicate so tokens rotation already retired keep the moment they actually
        # stopped working. The set is small — one row per refresh — but it is unbounded in
        # a long-lived session, and this is the path a leak takes.
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.session_id == session_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=at)
        )
        await self._session.commit()

    @staticmethod
    def _to_domain(model: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=RefreshTokenId(model.id),
            user_id=UserId(model.user_id),
            session_id=SessionId(model.session_id),
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
        )
