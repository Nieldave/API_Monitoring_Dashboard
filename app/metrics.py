"""Prometheus metric definitions for the API."""

from prometheus_client import Counter, Gauge, Histogram

LATENCY_BUCKETS: tuple[float, ...] = (0.05, 0.1, 0.5, 1.0, 3.0, 5.0, 10.0)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests processed.",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
    buckets=LATENCY_BUCKETS,
)

REQUESTS_IN_FLIGHT = Gauge(
    "http_requests_in_flight",
    "Number of HTTP requests currently being processed.",
)

API_UP = Gauge(
    "api_up",
    "1 when the API reports itself healthy, 0 otherwise.",
)


def record_request(
    method: str, endpoint: str, status_code: int, duration_seconds: float
) -> None:
    """Record counter and histogram observations for a finished request."""
    REQUEST_COUNT.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(
        duration_seconds
    )