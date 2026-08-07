from uuid import uuid4

import pytest

from app.common.ids import UserId
from app.contexts.user.domain.identity import Identity, Provider


class TestIdentity:
    def test_id_is_auto_generated(self):
        identity = Identity(user_id=UserId(uuid4()), provider=Provider.GOOGLE, subject="1234567890")

        assert identity.id is not None

    def test_two_identities_have_different_ids(self):
        user = UserId(uuid4())
        google = Identity(user_id=user, provider=Provider.GOOGLE, subject="1234567890")
        discord = Identity(user_id=user, provider=Provider.DISCORD, subject="9876543210")

        assert google.id != discord.id

    def test_one_account_can_hold_several(self):
        """The reason this is a table rather than columns on `users`: linking a second
        provider is a row, not a migration."""
        user = UserId(uuid4())

        identities = [
            Identity(user_id=user, provider=Provider.GOOGLE, subject="1234567890"),
            Identity(user_id=user, provider=Provider.DISCORD, subject="9876543210"),
        ]

        assert {identity.user_id for identity in identities} == {user}


class TestProvider:
    def test_is_stored_as_its_plain_string(self):
        """A StrEnum, so the value written to the database and compared against a
        provider's response is the string itself — no mapping table to keep in step."""
        assert Provider.GOOGLE == "google"
        assert Provider.DISCORD == "discord"

    def test_rejects_a_provider_it_does_not_know(self):
        """`provider` is half the unique key that decides which account a sign-in reaches.
        A free string would let "google" and "Google" be two providers to the database and
        one to a reader, and the row that lost would be a second account for one person."""
        with pytest.raises(ValueError):
            Provider("gogle")
