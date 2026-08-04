import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Vite's default dev server port (5173) and preview port (4173).
_DEFAULT_ORIGINS = "http://localhost:5173,http://localhost:4173"


def setup_cors(app: FastAPI) -> None:
    origins = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", _DEFAULT_ORIGINS).split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # `allow_headers` is about the request; this is about the response, and a browser
        # hides every header not named here from the page's JavaScript. Retry-After is the
        # one thing a 429 tells a client that it cannot work out for itself — without this
        # the frontend can see the status and not how long to wait, which turns the backoff
        # documented on /users/refresh into a guess.
        expose_headers=["Retry-After"],
    )
