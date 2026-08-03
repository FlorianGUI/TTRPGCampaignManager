from datetime import UTC, datetime
from typing import Literal, TypedDict

from fastapi import Response

REFRESH_COOKIE_NAME = "refresh"


class _Attributes(TypedDict):
    httponly: bool
    secure: bool
    samesite: Literal["strict"]
    path: str


# Everything about how the refresh token travels, in one place and shared by setting and
# clearing, because the attributes are the security control and because a cookie cleared
# with attributes that do not match the ones it was set with is not cleared at all.
#
#   httponly  — the whole reason a refresh token is a cookie rather than a JSON field.
#               Script cannot read it, so an XSS that owns the page still cannot walk away
#               with a thirty-day credential. This is what lets the frontend hold the
#               access token in memory only, with nothing durable in localStorage (#34).
#   secure    — never sent over plain HTTP. Fine in development too: browsers treat
#               http://localhost as a trustworthy origin and send secure cookies to it.
#   samesite  — Strict, which most session cookies cannot afford: it stops the cookie
#               riding along on a top-level navigation from another site, so following a
#               link into the app would arrive signed out. A refresh cookie never needs
#               that — it is only ever read by an XHR the app itself makes — so Strict
#               costs nothing here and removes most of the CSRF surface for free.
#   path      — /users, deliberately wider than the /users/refresh the issue suggested.
#               Logout has to revoke server-side, which means it has to receive the
#               cookie, and it lives at /users/logout. The scoping still does its job:
#               no campaign, character or source request carries this cookie, and that is
#               where the volume of requests is.
_ATTRIBUTES: _Attributes = {"httponly": True, "secure": True, "samesite": "strict", "path": "/users"}


def set_refresh_cookie(response: Response, token: str, expires_at: datetime) -> None:
    """Attach a refresh token to the response, for as long as the session has left.

    The lifetime is the session's remaining life rather than a fresh window, because
    rotation does not move the deadline. A cookie that outlived the session it belongs to
    would have the browser presenting a token the server stopped honouring days ago —
    harmless but confusing, and it would hide the expiry from the frontend, which can
    otherwise treat "the cookie is gone" as "sign in again".
    """
    max_age = max(int((expires_at - datetime.now(UTC)).total_seconds()), 0)
    response.set_cookie(REFRESH_COOKIE_NAME, token, max_age=max_age, **_ATTRIBUTES)


def clear_refresh_cookie(response: Response) -> None:
    """Ask the browser to drop the cookie.

    Only ever the second half of logging out. The token is already revoked server-side by
    the time this runs, so a client that ignores the header is left holding something
    dead rather than a working session — the cookie is the convenience, the row is the
    truth.
    """
    response.delete_cookie(REFRESH_COOKIE_NAME, **_ATTRIBUTES)
