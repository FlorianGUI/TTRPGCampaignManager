from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

_limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


def setup_rate_limiter(app: FastAPI) -> None:
    app.state.limiter = _limiter  # type: ignore[attr-defined]
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)  # type: ignore[arg-type]