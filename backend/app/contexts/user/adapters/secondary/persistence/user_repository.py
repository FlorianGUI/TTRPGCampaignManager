from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.ids import UserId
from app.contexts.user.adapters.secondary.persistence.user_model import UserModel
from app.contexts.user.domain.ports.user_repository import EmailTakenError, UsernameTakenError, UserRepository
from app.contexts.user.domain.user import User

# The index names Alembic generated, which are what Postgres reports back when one is
# violated. Named here rather than matched on the message text, which is a sentence the
# driver is free to reword.
_USERNAME_INDEX = "ix_users_username"
_EMAIL_INDEX = "ix_users_email"


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            email_verified=user.email_verified,
        )
        self._session.add(model)
        try:
            await self._session.commit()
        except IntegrityError as error:
            # The session is unusable after a failed flush, and a caller that means to
            # retry with another username needs it working.
            await self._session.rollback()
            raise self._translate(error) from None
        return user

    @staticmethod
    def _translate(error: IntegrityError) -> Exception:
        """Turn the driver's unique violation into something the application can act on.

        Which constraint failed decides what the caller does next — retry with another
        name, or report that the address is spoken for — so collapsing both into one error
        would leave the application guessing.
        """
        constraint = getattr(error.orig.__cause__, "constraint_name", None) if error.orig else None
        if constraint == _USERNAME_INDEX:
            return UsernameTakenError(constraint)
        if constraint == _EMAIL_INDEX:
            return EmailTakenError(constraint)
        # Anything else is not ours to reinterpret.
        return error

    async def find_by_id(self, id: UserId) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == id))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    async def mark_email_verified(self, id: UserId) -> None:
        await self._session.execute(update(UserModel).where(UserModel.id == id).values(email_verified=True))
        await self._session.commit()

    async def find_by_username(self, username: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.username == username))
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=UserId(model.id),
            username=model.username,
            email=model.email,
            hashed_password=model.hashed_password,
            email_verified=model.email_verified,
        )
