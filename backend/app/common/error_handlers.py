from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.common.errors import NotAvailable


class NotAvailableResponse(BaseModel):
    """The body every `NotAvailable` becomes. One shape for all of them, on purpose."""

    detail: str


def not_available_responses(*details: str) -> dict[int | str, dict[str, Any]]:
    """Declare the 404 a route can answer with, for the OpenAPI schema.

    This has to be written out because nothing infers it. The routes raise domain
    exceptions and a handler turns them into responses, so there is no `HTTPException` in
    a signature for FastAPI to read — the docs would silently claim these endpoints only
    ever succeed.

    The description is worth stating in the published schema rather than only in the
    code: a caller needs to know that a 404 here does not mean the id is unused. That is
    the whole of the #12 decision, and it is the sort of thing an integrator otherwise
    discovers by guessing.

    Pass every detail a route can produce. The ones under a campaign can answer for the
    table as well as for the thing at it, and showing both is the honest documentation.
    """
    examples = {detail: {"value": {"detail": detail}} for detail in details}
    return {
        404: {
            "model": NotAvailableResponse,
            "description": (
                "Not found, or not yours — the two are deliberately indistinguishable. "
                "A record belonging to someone else answers exactly as one that never "
                "existed, so probing ids reveals nothing about what other users own."
            ),
            "content": {"application/json": {"examples": examples}},
        }
    }


async def not_available_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": cast(NotAvailable, exc).detail})


def setup_error_handlers(app: FastAPI) -> None:
    """Turn the domain's "you cannot have that" into the one answer it is allowed to give.

    Registered against the base class, and Starlette walks the MRO looking for a handler,
    so every context that raises a `NotAvailable` subclass is covered without touching
    this file — #52 and #29 included. That also makes the 404-not-403 rule structural:
    there is one place that decides the status, rather than three router modules holding
    matching constants and staying in step by hand.

    Note the schema side does not come along for free: a new route still has to declare
    `responses=not_available_responses(...)` or the docs will not mention the 404 it can
    return.
    """
    app.add_exception_handler(NotAvailable, not_available_handler)
