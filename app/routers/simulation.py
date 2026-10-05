"""Endpoints that deliberately generate failures for monitoring validation."""

import asyncio
import random
from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.config import get_settings

router = APIRouter(tags=["simulation"])
logger = structlog.get_logger(__name__)


class SimulatedBackendError(Exception):
    """Raised to emulate a backend dependency failure."""


@router.get("/simulate-auth-error")
async def simulate_auth_error() -> JSONResponse:
    """Scenario 1: return 401 Unauthorized."""
    logger.warning("simulated_auth_failure", reason="invalid_api_key")
    return JSONResponse(
        status_code=401,
        content={"error": "Invalid API key or token"},
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/simulate-timeout")
async def simulate_timeout(
    seconds: float | None = Query(
        default=None,
        ge=0,
        le=30,
        description="Override the configured delay (defaults to 3.5s).",
    ),
) -> dict[str, float | str]:
    """Scenario 2: sleep before answering to simulate a slow upstream."""
    delay = get_settings().timeout_delay_seconds if seconds is None else seconds
    logger.warning("simulated_slow_response", delay_seconds=delay)
    await asyncio.sleep(delay)
    return {"status": "ok", "delayed_seconds": delay}


@router.get("/simulate-error")
async def simulate_error(
    mode: Literal["http", "unhandled", "random"] = Query(
        default="random",
        description="http: raise HTTPException(500); unhandled: raise "
        "RuntimeError; random: pick one.",
    ),
) -> dict[str, str]:
    """Scenario 3: produce an HTTP 500 with a logged stack trace."""
    chosen = random.choice(["http", "unhandled"]) if mode == "random" else mode

    if chosen == "unhandled":
        # Propagates to the middleware, which logs the traceback.
        raise RuntimeError(
            "Simulated unhandled failure: database connection pool exhausted"
        )

    try:
        raise SimulatedBackendError("Simulated upstream payment service failure")
    except SimulatedBackendError:
        logger.exception("simulated_server_error", mode=chosen)
    raise HTTPException(status_code=500, detail="Simulated internal server error")


@router.get("/simulate-rate-limit")
async def simulate_rate_limit() -> JSONResponse:
    """Scenario 4: return 429 with a Retry-After header."""
    retry_after = get_settings().rate_limit_retry_after_seconds
    logger.warning("simulated_rate_limit", retry_after_seconds=retry_after)
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "retry_after_seconds": retry_after,
        },
        headers={"Retry-After": str(retry_after)},
    )