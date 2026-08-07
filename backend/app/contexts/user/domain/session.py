from dataclasses import dataclass
from datetime import datetime

from app.common.ids import SessionId


@dataclass(frozen=True)
class Session:
    """The two tokens a signed-in client holds, and the only place they travel together.

    They are returned as a pair because they are minted as a pair and because the split
    between them is the whole design: the access token goes in the response body for
    JavaScript to hold in memory, the refresh token goes in an `httpOnly` cookie that
    JavaScript cannot read. A service that returned one and left the caller to arrange the
    other would let an adapter forget half of it.

    `refresh_token` is the secret itself, not its hash — the only moment in the system
    where that value exists outside the browser. It goes straight into a `Set-Cookie` and
    is never logged, stored, or returned in a body.

    `expires_at` is the session's deadline, not this token's, and it does not move when
    the pair is rotated. It travels with the tokens so the cookie can be given a matching
    lifetime; nothing enforces the window from here, since the row is what gets checked.
    """

    access_token: str
    refresh_token: str
    expires_at: datetime
    # Which session these belong to — the same value across every rotation of the pair.
    # Carried here so a caller can attach something to the session that started, which is
    # what the verification re-send cap counts against (#38).
    session_id: SessionId
