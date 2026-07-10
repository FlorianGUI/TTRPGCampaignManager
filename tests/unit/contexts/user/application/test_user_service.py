import uuid
from uuid import UUID

import pytest

from app.contexts.user.application.security import decode_access_token
from app.contexts.user.application.user_service import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
    UserService,
)
from app.contexts.user.domain.ports.user_repository import UserRepository
from app.contexts.user.domain.user import User


class FakeUserRepository(UserRepository):
    def __init__(self):
        self._store: dict[UUID, User] = {}

    async def save(self, user: User) -> User:
        self._store[user.id] = user
        return user

    async def find_by_id(self, id: UUID) -> User | None:
        return self._store.get(id)

    async def find_by_username(self, username: str) -> User | None:
        return next((u for u in self._store.values() if u.username == username), None)


@pytest.fixture
def service():
    return UserService(FakeUserRepository())


class TestRegister:
    async def test_returns_user_with_correct_fields(self, service: UserService):
        user = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        assert user.username == "aragorn"
        assert user.email == "aragorn@gondor.test"

    async def test_hashes_the_password(self, service: UserService):
        user = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        assert user.hashed_password != "strider123"

    async def test_raises_when_username_already_exists(self, service: UserService):
        await service.register("aragorn", "aragorn@gondor.test", "strider123")

        with pytest.raises(UsernameAlreadyExistsError):
            await service.register("aragorn", "other@gondor.test", "otherpass")


class TestAuthenticate:
    async def test_returns_a_valid_token_for_correct_credentials(self, service: UserService):
        user = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        token = await service.authenticate("aragorn", "strider123")

        assert decode_access_token(token) == str(user.id)

    async def test_raises_for_wrong_password(self, service: UserService):
        await service.register("aragorn", "aragorn@gondor.test", "strider123")

        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("aragorn", "wrongpass")

    async def test_raises_for_unknown_username(self, service: UserService):
        with pytest.raises(InvalidCredentialsError):
            await service.authenticate("unknown", "whatever")


class TestGet:
    async def test_returns_user_when_found(self, service: UserService):
        created = await service.register("aragorn", "aragorn@gondor.test", "strider123")

        found = await service.get(created.id)

        assert found == created

    async def test_returns_none_when_not_found(self, service: UserService):
        result = await service.get(uuid.uuid4())

        assert result is None