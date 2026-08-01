import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.common.security import security
from app.common.security.security import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY, create_access_token

# An access token cannot be withdrawn once handed out — presenting one is a signature
# check and nothing else — so its lifetime is the only thing limiting how long a stolen
# one is worth stealing. That makes two properties worth holding onto: the tokens we mint
# actually carry the configured expiry, and an expired one is actually turned away.
#
# Neither is visible from the user context's tests, which only ever use a fresh token.


def _claims(token: str) -> dict:
    return dict(jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]))


class TestLifetime:
    def test_a_token_expires_after_the_configured_number_of_minutes(self):
        issued_at = datetime.now(UTC)

        token = create_access_token(subject=str(uuid.uuid4()))

        expires_at = datetime.fromtimestamp(_claims(token)["exp"], UTC)
        assert (expires_at - issued_at).total_seconds() == pytest.approx(
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds(), abs=5
        )

    def test_the_default_is_short(self):
        """Guards the number itself, which is the security decision rather than the wiring.

        Configurable so a deployment can trade refresh round-trips against exposure, but
        the value a machine gets when it configures nothing is the one that matters — and
        it should not quietly drift back towards the hour it used to be.
        """
        assert security._DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES <= 15


class TestExpiry:
    async def test_an_expired_token_is_rejected(self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
        """A short lifetime is worth nothing unless something enforces it.

        `jwt.decode` checks `exp` by default, so this passes today by not having opted
        out — which is exactly the kind of thing that gets opted out of by accident while
        debugging and never noticed, because every other test signs in moments earlier.
        """
        monkeypatch.setattr(security, "ACCESS_TOKEN_EXPIRE_MINUTES", -1)
        token = create_access_token(subject=str(uuid.uuid4()))

        response = await client.get("/campaigns/", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 401
