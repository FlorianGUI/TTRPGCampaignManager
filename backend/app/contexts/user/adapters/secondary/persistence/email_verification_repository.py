from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import EmailVerificationId, SessionId, UserId
from app.contexts.user.adapters.secondary.persistence.email_verification_model import EmailVerificationModel
from app.contexts.user.domain.email_verification import EmailVerification
from app.contexts.user.domain.ports.email_verification_repository import EmailVerificationRepository


class SqlAlchemyEmailVerificationRepository(EmailVerificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, verification: EmailVerification) -> EmailVerification:
        await self._session.merge(
            EmailVerificationModel(
                id=verification.id,
                user_id=verification.user_id,
                session_id=verification.session_id,
                token_hash=verification.token_hash,
                created_at=verification.created_at,
                expires_at=verification.expires_at,
                used_at=verification.used_at,
            )
        )
        await self._session.commit()
        return verification

    async def find_by_hash(self, token_hash: str) -> EmailVerification | None:
        result = await self._session.execute(
            select(EmailVerificationModel).where(EmailVerificationModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def count_for_session(self, session_id: SessionId) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(EmailVerificationModel)
            .where(EmailVerificationModel.session_id == session_id)
        )
        return result.scalar_one()

    async def last_sent_at(self, user_id: UserId) -> datetime | None:
        result = await self._session.execute(
            select(func.max(EmailVerificationModel.created_at)).where(EmailVerificationModel.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _to_domain(model: EmailVerificationModel) -> EmailVerification:
        return EmailVerification(
            id=EmailVerificationId(model.id),
            user_id=UserId(model.user_id),
            session_id=SessionId(model.session_id),
            token_hash=model.token_hash,
            created_at=model.created_at,
            expires_at=model.expires_at,
            used_at=model.used_at,
        )
