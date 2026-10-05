"""Test helpers shared across test modules."""

from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY

from app.main import app


def make_client() -> AsyncClient:
    """Return an async HTTP client bound directly to the ASGI app."""
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    )


def counter_value(endpoint: str, status_code: int, method: str = "GET") -> float:
    """Read the current value of ``http_requests_total`` for one label set."""
    value = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": method, "endpoint": endpoint, "status_code": str(status_code)},
    )
    return value or 0.0