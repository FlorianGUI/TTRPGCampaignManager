import hashlib
import os
import secrets
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

# How long a session can last before signing in again, whatever it does in the meantime.
# The window is absolute: rotation hands out a new token but never moves the deadline, so
# thirty days after signing in the session ends even for someone who used it every day.
# A sliding window would keep a leaked family alive indefinitely as long as the thief kept
# refreshing, which is the one thing this bound exists to stop.
_DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 30
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS") or _DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS)


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


def create_refresh_token() -> str:
    """A refresh token is a random secret, not a JWT, and carries no claims at all.

    Nothing about it needs to be readable without the database, because unlike an access
    token it is never trusted on its signature alone: every use is a row lookup, which is
    what makes revocation and reuse detection possible in the first place. A bearer string
    with no structure is therefore the honest representation — 256 bits from the OS CSPRNG,
    url-safe so it survives a cookie unencoded.
    """
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Turn a refresh token into what the database is allowed to hold.

    SHA-256 rather than bcrypt, and the difference matters in both directions. Lookup is
    *by* the hash — the presented token is the only thing we know, so the hash has to be
    deterministic and unsalted or the row could not be found. That rules bcrypt out. It is
    also safe to rule it out here, which it would not be for a password: this input is 256
    bits of uniform randomness rather than something a person chose, so there is no
    dictionary to run and a fast hash costs an attacker nothing they did not already have.

    What the hash buys is that a leaked database dump is not a drawer full of live
    sessions. Never store or log the token itself.
    """
    return hashlib.sha256(token.encode()).hexdigest()
