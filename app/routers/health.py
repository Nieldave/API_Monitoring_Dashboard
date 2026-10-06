"""Health check endpoint."""

import sqlite3
import time
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest
from pydantic import BaseModel

from app.config import get_settings
from app.database import get_connection
from app.metrics import API_UP

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)

_STARTED_AT = datetime.now(timezone.utc)
_STARTED_MONOTONIC = time.monotonic()


class HealthResponse(BaseModel):
    """Payload returned by GET /health."""

    status: str
    service: str
    version: str
    environment: str
    started_at: datetime
    uptime_seconds: float
    timestamp: datetime
    dependencies: dict[str, str]


def _check_database() -> str:
    """Run real queries against SQLite; 'unavailable' on any failure."""
    try:
        with get_connection() as connection:
            connection.execute("SELECT COUNT(*) FROM users").fetchone()
            connection.execute("SELECT COUNT(*) FROM products").fetchone()
    except (sqlite3.Error, OSError):
        logger.exception("database_health_check_failed")
        return "unavailable"
    return "ok"


def _check_dependencies() -> dict[str, str]:
    """Probe the service's dependencies."""
    settings = get_settings()
    return {
        "database": _check_database(),
        "metrics_registry": "ok" if generate_latest() else "unavailable",
        "simulated_dependency": (
            "unavailable" if settings.health_force_failure else "ok"
        ),
    }


@router.get("/health", response_model=HealthResponse)
async def health() -> JSONResponse:
    """Return service health; responds 503 and sets ``api_up=0`` if unhealthy."""
    settings = get_settings()
    dependencies = _check_dependencies()
    healthy = all(value == "ok" for value in dependencies.values())

    API_UP.set(1 if healthy else 0)
    if not healthy:
        logger.error("health_check_failed", dependencies=dependencies)

    now = datetime.now(timezone.utc)
    payload = HealthResponse(
        status="ok" if healthy else "unhealthy",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        started_at=_STARTED_AT,
        uptime_seconds=round(time.monotonic() - _STARTED_MONOTONIC, 3),
        timestamp=now,
        dependencies=dependencies,
    )
    return JSONResponse(
        status_code=200 if healthy else 503,
        content=payload.model_dump(mode="json"),
    )