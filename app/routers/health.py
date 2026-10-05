"""Health check endpoint."""

import time
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest
from pydantic import BaseModel

from app.config import get_settings
from app.metrics import API_UP
from app.routers.products import PRODUCTS
from app.routers.users import USERS

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


def _check_dependencies() -> dict[str, str]:
    """Probe the service's dependencies.

    The sample API keeps its data in memory, so the probes verify the data
    stores are loaded and the metrics registry is serialisable. Replace or
    extend these with real DB/cache checks when connecting a backend.
    """
    settings = get_settings()
    return {
        "user_store": "ok" if USERS else "unavailable",
        "product_store": "ok" if PRODUCTS else "unavailable",
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