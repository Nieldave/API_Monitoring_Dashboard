"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Override any field with an ``APP_`` prefixed env var."""

    model_config = SettingsConfigDict(
        env_prefix="APP_", env_file=".env", extra="ignore"
    )

    app_name: str = "fastapi-monitoring-demo"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # /simulate-timeout sleeps this long (seconds) unless ?seconds= is given.
    timeout_delay_seconds: float = 3.5
    # Value of the Retry-After header returned by /simulate-rate-limit.
    rate_limit_retry_after_seconds: int = 30
    # When true, /health reports a failed dependency (503, api_up=0).
    health_force_failure: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()