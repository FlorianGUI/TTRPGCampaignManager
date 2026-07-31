from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.common.errors import NotAvailable


async def not_available_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": cast(NotAvailable, exc).detail})


def setup_error_handlers(app: FastAPI) -> None:
    """Turn the domain's "you cannot have that" into the one answer it is allowed to give.

    Registered against the base class, and Starlette walks the MRO looking for a handler,
    so every context that raises a `NotAvailable` subclass is covered without touching
    this file — #52 and #29 included. That also makes the 404-not-403 rule structural:
    there is one place that decides the status, rather than three router modules holding
    matching constants and staying in step by hand.
    """
    app.add_exception_handler(NotAvailable, not_available_handler)
