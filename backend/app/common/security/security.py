import os
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = "HS256"

# Short on purpose. An access token cannot be revoked before it expires — nothing is
# looked up when one is presented, the signature is the whole check — so its lifetime is
# the window in which a stolen token still works. Sixty minutes was only tolerable while
# it was the sole credential; once #35 lands a refresh cookie, a session outlives this
# without the access token having to, and there is no reason left to keep it long.
#
# Configuration rather than a constant because the tradeoff is deployment's to make: a
# shorter window costs more refresh round-trips, and how much that matters depends on
# where the thing is running.
_DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES") or _DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": subject, "exp": expires_at}, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    return payload["sub"]
