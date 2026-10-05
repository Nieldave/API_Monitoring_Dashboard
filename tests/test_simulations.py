"""Tests verifying the 401, 500, 429 and delay behaviours."""

import time

import pytest

from app.config import get_settings
from tests import counter_value, make_client

pytestmark = pytest.mark.asyncio


async def test_auth_error_returns_401() -> None:
    before = counter_value("/simulate-auth-error", 401)
    async with make_client() as client:
        response = await client.get("/simulate-auth-error")

    assert response.status_code == 401
    assert response.json() == {"error": "Invalid API key or token"}
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert counter_value("/simulate-auth-error", 401) == before + 1


async def test_server_error_http_mode_returns_500() -> None:
    before = counter_value("/simulate-error", 500)
    async with make_client() as client:
        response = await client.get("/simulate-error", params={"mode": "http"})

    assert response.status_code == 500
    assert counter_value("/simulate-error", 500) == before + 1


async def test_server_error_unhandled_mode_returns_500_with_request_id() -> None:
    before = counter_value("/simulate-error", 500)
    async with make_client() as client:
        response = await client.get("/simulate-error", params={"mode": "unhandled"})

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "Internal Server Error"
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert counter_value("/simulate-error", 500) == before + 1


async def test_server_error_random_mode_always_fails() -> None:
    async with make_client() as client:
        statuses = {
            (await client.get("/simulate-error")).status_code for _ in range(6)
        }

    assert statuses == {500}


async def test_rate_limit_returns_429_with_retry_after() -> None:
    before = counter_value("/simulate-rate-limit", 429)
    async with make_client() as client:
        response = await client.get("/simulate-rate-limit")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == str(
        get_settings().rate_limit_retry_after_seconds
    )
    assert response.json()["error"] == "Rate limit exceeded"
    assert counter_value("/simulate-rate-limit", 429) == before + 1


async def test_timeout_respects_seconds_override() -> None:
    async with make_client() as client:
        start = time.perf_counter()
        response = await client.get("/simulate-timeout", params={"seconds": 0.2})
        elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed >= 0.2


async def test_timeout_default_delay_is_3_5_seconds() -> None:
    assert get_settings().timeout_delay_seconds == 3.5
    async with make_client() as client:
        start = time.perf_counter()
        response = await client.get("/simulate-timeout")
        elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed >= 3.5
    assert response.json()["delayed_seconds"] == 3.5


async def test_timeout_rejects_out_of_range_seconds() -> None:
    async with make_client() as client:
        response = await client.get("/simulate-timeout", params={"seconds": 99})

    assert response.status_code == 422