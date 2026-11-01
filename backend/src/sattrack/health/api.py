"""Health endpoint: database reachability and freshness of the ingested data."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from sattrack.ingest import DataState, get_data_status
from sattrack.shared import Clock
from sattrack.shared.web import SessionDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["health"])


class HealthOut(BaseModel):
    status: str
    data_state: DataState | None
    last_successful_fetch_at: datetime | None
    data_age_seconds: int | None


@router.get(
    "/health",
    response_model=HealthOut,
    summary="Service health and data freshness",
    responses={503: {"description": "Database unreachable"}},
)
def health(request: Request, response: Response, session: SessionDep) -> HealthOut:
    clock: Clock = request.app.state.clock
    try:
        data = get_data_status(session, clock())
    except SQLAlchemyError:
        logger.exception("Health check could not query the database")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthOut(
            status="unavailable",
            data_state=None,
            last_successful_fetch_at=None,
            data_age_seconds=None,
        )
    return HealthOut(
        status="ok",
        data_state=data.state,
        last_successful_fetch_at=data.last_success_at,
        data_age_seconds=data.age_seconds,
    )
