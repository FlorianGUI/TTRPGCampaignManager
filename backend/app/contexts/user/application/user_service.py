from uuid import UUID

import jwt

from app.common.security.security import create_access_token, decode_access_token, hash_password, verify_password
from app.contexts.user.domain.ports.user_repository import UserRepository
from app.contexts.user.domain.user import User


class UsernameAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def register(self, username: str, email: str, password: str) -> User:
        if await self._repository.find_by_username(username) is not None:
            raise UsernameAlreadyExistsError(username)
        user = User(username=username, email=email, hashed_password=hash_password(password))
        return await self._repository.save(user)

    async def authenticate(self, username: str, password: str) -> str:
        user = await self._repository.find_by_username(username)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError(username)
        return create_access_token(subject=str(user.id))

    async def get(self, id: UUID) -> User | None:
        return await self._repository.find_by_id(id)

    async def get_by_token(self, token: str) -> User:
        try:
            user_id = UUID(decode_access_token(token))
        except (jwt.PyJWTError, ValueError):
            raise InvalidCredentialsError(token) from None
        user = await self._repository.find_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError(token)
        return user
