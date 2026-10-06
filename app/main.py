"""FastAPI application factory, middleware and route registration."""

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import get_settings
from app.database import init_db
from app.logging_config import configure_logging
from app.metrics import API_UP, REQUESTS_IN_FLIGHT, record_request
from app.routers import health, products, simulation, users

settings = get_settings()
configure_logging(settings.log_level)

logger = structlog.get_logger("app.access")

REQUEST_ID_HEADER = "X-Request-ID"
UNMATCHED_ENDPOINT = "unmatched"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Mark the service up on startup and down on graceful shutdown."""
    init_db()
    API_UP.set(1)
    logger.info(
        "service_started",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
    yield
    API_UP.set(0)
    logger.info("service_stopped")


def _resolve_endpoint(request: Request) -> str:
    """Return the route template (low-cardinality) for metric labels."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else UNMATCHED_ENDPOINT


async def observability_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Attach a request ID, record Prometheus metrics and emit a JSON log line."""
    if request.url.path == "/metrics":
        return await call_next(request)

    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    request.state.request_id = request_id

    start = time.perf_counter()
    status_code = 500
    response: Response

    REQUESTS_IN_FLIGHT.inc()
    try:
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # Unhandled exception: capture the full stack trace in the log and
            # return a controlled 500 so the failure is still measured.
            logger.exception(
                "unhandled_exception",
                method=request.method,
                path=request.url.path,
            )
            response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "request_id": request_id,
                },
            )
            status_code = 500
    finally:
        REQUESTS_IN_FLIGHT.dec()

    duration = time.perf_counter() - start
    endpoint = _resolve_endpoint(request)
    record_request(request.method, endpoint, status_code, duration)

    response.headers[REQUEST_ID_HEADER] = request_id

    log = logger.info
    if status_code >= 500:
        log = logger.error
    elif status_code >= 400:
        log = logger.warning
    log(
        "http_request",
        method=request.method,
        path=request.url.path,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=round(duration * 1000, 2),
        client=request.client.host if request.client else None,
    )

    structlog.contextvars.clear_contextvars()
    return response


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Sample API used to demonstrate monitoring and alerting.",
        lifespan=lifespan,
    )
    application.middleware("http")(observability_middleware)

    application.include_router(health.router)
    application.include_router(users.router)
    application.include_router(products.router)
    application.include_router(simulation.router)

    @application.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        """Expose Prometheus metrics."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return application


app = create_app()