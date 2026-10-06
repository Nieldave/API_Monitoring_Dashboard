"""Tests for /health, /metrics and request-ID handling."""

import pytest
from prometheus_client import REGISTRY

from app.config import get_settings
from app.metrics import API_UP
from tests import make_client

pytestmark = pytest.mark.asyncio

async def test_health_unhealthy_when_database_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(get_settings(), "database_path", str(tmp_path))
    try:
        async with make_client() as client:
            response = await client.get("/health")

        assert response.status_code == 503
        assert response.json()["dependencies"]["database"] == "unavailable"
    finally:
        API_UP.set(1)
        
async def test_health_returns_ok_payload() -> None:
    async with make_client() as client:
        response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["uptime_seconds"] >= 0
    assert "started_at" in body and "timestamp" in body
    assert all(value == "ok" for value in body["dependencies"].values())
    assert REGISTRY.get_sample_value("api_up") == 1.0


async def test_health_reports_failure_when_dependency_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "health_force_failure", True)
    try:
        async with make_client() as client:
            response = await client.get("/health")

        assert response.status_code == 503
        assert response.json()["status"] == "unhealthy"
        assert response.json()["dependencies"]["simulated_dependency"] == "unavailable"
        assert REGISTRY.get_sample_value("api_up") == 0.0
    finally:
        API_UP.set(1)


async def test_request_id_is_generated_and_echoed() -> None:
    async with make_client() as client:
        generated = await client.get("/health")
        echoed = await client.get("/health", headers={"X-Request-ID": "trace-abc-123"})

    assert len(generated.headers["X-Request-ID"]) == 32
    assert echoed.headers["X-Request-ID"] == "trace-abc-123"


async def test_metrics_endpoint_exposes_custom_metrics() -> None:
    async with make_client() as client:
        await client.get("/users")
        response = await client.get("/metrics")

    assert response.status_code == 200
    text = response.text
    for name in (
        "http_requests_total",
        "http_request_duration_seconds_bucket",
        "http_requests_in_flight",
        "api_up",
    ):
        assert name in text


async def test_in_flight_gauge_returns_to_zero() -> None:
    async with make_client() as client:
        await client.get("/health")

    assert REGISTRY.get_sample_value("http_requests_in_flight") == 0.0