import os
from typing import Any, cast

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# What everything else gets. Generous on purpose: the rest of the API is authenticated,
# and the limit that fits a game master flipping between campaign pages is not the limit
# that fits a login form. `/users/refresh` lives here too — see its docstring for why.
GLOBAL_RATE_LIMIT = "100/minute"

# The two endpoints a stranger can reach with something worth guessing or spamming, each
# an order of magnitude tighter than the default and tightened on the axis that suits it.
#
# Login is per minute because the attack is one address trying many passwords quickly, and
# ten is well above what a human retyping a password needs. Register is per hour because
# the attack is one address creating many accounts, and nobody signs up twice a minute —
# five a minute would still allow three hundred accounts an hour, which is not a limit.
#
# Environment-overridable, like ACCESS_TOKEN_EXPIRE_MINUTES: the right number depends on
# how many people sit behind one address at a deployment, which is deployment's to know.
# The defaults are the safe end, so an unset variable is never the loose choice.
_DEFAULT_LOGIN_RATE_LIMIT = "10/minute"
_DEFAULT_REGISTER_RATE_LIMIT = "5/hour"
# Password reset is the one endpoint here that will send mail to an address supplied by
# whoever called it, which makes it the outbound-spam amplifier the re-send in #38 was
# careful not to be. Per hour rather than per minute for the same reason as register:
# nobody legitimately asks twice in a minute, and a per-minute cap loose enough to look
# harmless still adds up to hundreds of messages an hour aimed at one inbox.
_DEFAULT_FORGOT_PASSWORD_RATE_LIMIT = "5/hour"

LOGIN_RATE_LIMIT = os.environ.get("LOGIN_RATE_LIMIT") or _DEFAULT_LOGIN_RATE_LIMIT
REGISTER_RATE_LIMIT = os.environ.get("REGISTER_RATE_LIMIT") or _DEFAULT_REGISTER_RATE_LIMIT
FORGOT_PASSWORD_RATE_LIMIT = os.environ.get("FORGOT_PASSWORD_RATE_LIMIT") or _DEFAULT_FORGOT_PASSWORD_RATE_LIMIT

# One fixed sentence per endpoint, and deliberately not a sentence that can vary. A 429 on
# login that read differently for a real username than an unknown one would hand out
# account existence for free — the exact thing the 401 above it is careful not to do. The
# key is the address alone, so there is nothing about the account in scope here to leak.
TOO_MANY_LOGIN_ATTEMPTS = "Too many sign-in attempts from here. Try again shortly."
TOO_MANY_REGISTRATIONS = "Too many accounts created from here. Try again later."
# Says nothing about whether any of those requests matched an account, for the same reason
# the 204 does not.
TOO_MANY_RESET_REQUESTS = "Too many password reset requests from here. Try again later."
# The one sentence here that a signed-in person reads, because a 429 on refresh is the end
# of their session rather than a form telling them to slow down (#68). It has to say that,
# and it has to say what to do about it — a message that only complained about volume would
# leave someone staring at a login page with no idea why they are looking at it.
#
# `/users/refresh` answers on the application-wide limit like everything else, so this
# reaches it through an explicit `@limiter.limit(GLOBAL_RATE_LIMIT, error_message=...)` on
# the route rather than through a tighter number — see that endpoint's docstring. Without
# it slowapi falls back to `str(limit.limit)` and the login page would read "100 per
# 1 minute", which is both unreadable and the limit recited back to whoever just found it.
TOO_MANY_REFRESHES = "Too many requests from here. This session has been ended — sign in again to continue."

# `key_func` is the address, and that only means anything if the address is the caller's
# rather than the proxy's. Behind nginx it is not, unless the proxy sends X-Forwarded-For
# and uvicorn is told to trust the peer it arrives from — see `nginx/api.lastdawn.fr.conf`
# and FORWARDED_ALLOW_IPS in `docker-compose.prod.yml`. Get that wrong and every caller
# shares one bucket, which fails silently: it behaves like a working limiter right up
# until two people use the app at once.
#
# `headers_enabled` is what puts `Retry-After` on the 429, so a client can say how long
# rather than guessing. The storage is in-memory, so all of this is per process and resets
# on deploy — fine at one container, worth knowing before concluding it is stricter.
limiter = Limiter(key_func=get_remote_address, default_limits=[GLOBAL_RATE_LIMIT], headers_enabled=True)


class TooManyRequestsResponse(BaseModel):
    """The body every 429 becomes: `detail`, the same shape as every other error here."""

    detail: str


def too_many_requests_responses(detail: str) -> dict[int | str, dict[str, Any]]:
    """Declare the 429 an endpoint with its own limit can answer with, for the OpenAPI schema.

    Written out for the same reason `not_available_responses` is: the limit is applied by a
    decorator rather than raised in the body, so there is nothing in the signature for
    FastAPI to read and the docs would claim these endpoints never throttle.
    """
    return {
        429: {
            "model": TooManyRequestsResponse,
            "description": (
                "Too many requests from this address. `Retry-After` gives the seconds to wait. "
                "The limit is keyed on the caller's address alone, so this answer never depends "
                "on which account was named."
            ),
            "content": {"application/json": {"example": {"detail": detail}}},
        }
    }


def _too_many_requests_handler(request: Request, exc: Exception) -> Response:
    """Answer a throttled caller in the shape the rest of the API answers in.

    slowapi's own handler returns `{"error": "Rate limit exceeded: 10 per 1 minute"}`, which
    is a second error shape for the sign-up and login forms to special-case, and it recites
    the limit back at whoever just probed for it. `detail` is what every other error here
    carries, so the forms parse one thing.

    Sync rather than `async` on purpose: `SlowAPIMiddleware` runs the app's registered
    handler itself, and it cannot await one from synchronous middleware — an async handler
    is silently dropped in favour of slowapi's default, so the body would revert to the
    above for any limit caught in the middleware.

    `_inject_headers` is private, but it is what slowapi's own reference handler calls, and
    it is what puts `Retry-After` on the response.
    """
    detail = cast(RateLimitExceeded, exc).detail
    response: Response = JSONResponse(status_code=429, content={"detail": detail})
    return cast(Response, request.app.state.limiter._inject_headers(response, request.state.view_rate_limit))


def setup_rate_limiter(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _too_many_requests_handler)
    app.add_middleware(SlowAPIMiddleware)
