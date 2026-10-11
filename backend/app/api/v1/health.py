"""Health endpoint.

This is the smallest thing that can prove the whole chain works: HTTP reaches
FastAPI, and FastAPI reaches PostgreSQL. It returns 503 rather than 200 when
the database is unreachable, so a container orchestrator or a CI smoke test
can distinguish "process is up" from "service is usable".
"""

import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "A dependency is unavailable"}},
)
def health(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
    settings = get_settings()

    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except SQLAlchemyError:
        # Logged with the traceback; the response stays free of internals so a
        # failed probe cannot leak connection strings.
        logger.exception("Health check could not reach the database")
        database_ok = False

    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status="ok" if database_ok else "degraded",
        environment=settings.environment,
        database=database_ok,
        rubric_version=settings.active_rubric_version,
        model_version=settings.active_model_version,
    )
