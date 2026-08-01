from uuid import UUID

import jwt

from app.common.ids import UserId
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

    async def register(self, username: str, email: str, password: str) -> str:
        """Create the account and hand back the token that signs it in.

        Registering and signing in are one action to the person doing them, so they are
        one call here. Returning the new `User` and letting the router mint a token would
        put "signing up signs you in" in an adapter, where the next inbound port — an SSO
        callback, an invite acceptance — would have to remember to repeat it.

        The token is the only thing that comes back for the same reason: an endpoint that
        also returned the user would be describing an account nobody has asked to see yet,
        and `GET /users/me` already answers that with the token this returns.
        """
        if await self._repository.find_by_username(username) is not None:
            raise UsernameAlreadyExistsError(username)
        user = User(username=username, email=email, hashed_password=hash_password(password))
        saved = await self._repository.save(user)
        return self._issue_token(saved)

    async def authenticate(self, username: str, password: str) -> str:
        user = await self._repository.find_by_username(username)
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError(username)
        return self._issue_token(user)

    def _issue_token(self, user: User) -> str:
        """The one place a session begins.

        Both ways in go through here so they cannot drift apart, and so #35 has a single
        seam to hang refresh-token issuance on rather than two call sites to keep in step.
        """
        return create_access_token(subject=str(user.id))

    async def get(self, id: UserId) -> User | None:
        return await self._repository.find_by_id(id)

    async def get_by_token(self, token: str) -> User:
        try:
            user_id = UserId(UUID(decode_access_token(token)))
        except (jwt.PyJWTError, ValueError):
            raise InvalidCredentialsError(token) from None
        user = await self._repository.find_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError(token)
        return user
