"""FastAPI application factory. All wiring of concrete dependencies happens here."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sattrack import catalog, health
from sattrack.config import Settings, load_settings
from sattrack.shared import Clock, utc_now
from sattrack.shared.db import create_db_engine, create_session_factory
from sattrack.shared.logging import configure_logging

logger = logging.getLogger(__name__)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


def create_app(settings: Settings | None = None, clock: Clock = utc_now) -> FastAPI:
    """Build the API application. Settings are validated before anything else happens."""
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(str(settings.database_url))

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(
        title="Satellite Tracker API",
        version="0.1.0",
        description="Orbital element sets and satellite metadata from CelesTrak.",
        lifespan=lifespan,
        # Interactive docs stay available; they are read-only and contain no secrets.
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.state.session_factory = create_session_factory(engine)
    app.state.clock = clock

    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_allowed_origins),
            allow_methods=["GET"],
            allow_headers=["If-None-Match"],
            expose_headers=["ETag"],
        )
    app.middleware("http")(_add_security_headers)
    app.add_exception_handler(Exception, _handle_unexpected_error)
    app.include_router(catalog.router)
    app.include_router(health.router)
    return app


async def _add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    return response


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Boundary handler: details go to the server log, the client only gets a correlation ID.
    correlation_id = uuid.uuid4().hex
    logger.error(
        "Unhandled error correlation_id=%s method=%s path=%s",
        correlation_id,
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "correlation_id": correlation_id},
    )
