from app.contexts.user.domain.user import User


class TestUser:
    def test_id_is_auto_generated(self):
        user = User(username="aragorn", email="aragorn@gondor.test", hashed_password="hashed")
        assert user.id is not None

    def test_two_users_have_different_ids(self):
        a = User(username="aragorn", email="aragorn@gondor.test", hashed_password="hashed")
        b = User(username="legolas", email="legolas@woodland.test", hashed_password="hashed")
        assert a.id != b.id

    def test_an_account_may_have_no_password(self):
        """A provider account never had one. `None` rather than a sentinel hash, so
        `has_password` is a question with an answer instead of a comparison against a
        magic string every caller has to know."""
        user = User(username="legolas", email="legolas@woodland.test")

        assert user.hashed_password is None
        assert user.has_password is False

    def test_a_password_account_has_one(self):
        user = User(username="aragorn", email="aragorn@gondor.test", hashed_password="hashed")

        assert user.has_password is True

    def test_an_address_is_unverified_until_something_proves_it(self):
        """The default has to be false. Every route to true — a provider asserting it, the
        flow in #38 — is a positive act, and treating "we never checked" as verified is
        the account-takeover route the column exists to close."""
        user = User(username="aragorn", email="aragorn@gondor.test", hashed_password="hashed")

        assert user.email_verified is False
