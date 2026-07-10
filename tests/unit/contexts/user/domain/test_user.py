from app.contexts.user.domain.user import User


class TestUser:
    def test_id_is_auto_generated(self):
        user = User(username="aragorn", email="aragorn@gondor.test", hashed_password="hashed")
        assert user.id is not None

    def test_two_users_have_different_ids(self):
        a = User(username="aragorn", email="aragorn@gondor.test", hashed_password="hashed")
        b = User(username="legolas", email="legolas@woodland.test", hashed_password="hashed")
        assert a.id != b.id