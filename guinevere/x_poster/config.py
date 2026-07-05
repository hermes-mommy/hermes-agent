from __future__ import annotations

"""P13 X Auto Poster configuration via pydantic-settings."""

import functools
import json
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_list_field(v: str | list[str]) -> list[str]:
    """Parse a ``list[str]`` env var that may be JSON, comma-separated, or empty."""
    if isinstance(v, list):
        return v
    if not isinstance(v, str):
        return []
    stripped = v.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
    return [s.strip() for s in stripped.split(",") if s.strip()]


ListOfStrings = Annotated[list[str], BeforeValidator(_parse_list_field)]


class XPosterSettings(BaseSettings):
    """X Auto Poster configuration.

    All values loaded from environment variables with X_POSTER_ prefix.
    Secrets are loaded from SOPS-decrypted paths at runtime.
    """

    model_config = SettingsConfigDict(env_prefix="X_POSTER_", case_sensitive=False)

    # Database
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="guinevere", description="PostgreSQL database name")
    postgres_user: str = Field(default="guinevere", description="PostgreSQL user")
    postgres_password: str = Field(default="", description="PostgreSQL password (loaded from SOPS)")
    db_pool_min: int = Field(default=2, ge=1, description="Minimum DB pool connections")
    db_pool_max: int = Field(default=10, ge=1, description="Maximum DB pool connections")

    # Schedule
    schedule_slots: ListOfStrings = Field(
        default=["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"],
        description="Posting time slots in HH:MM format",
    )
    schedule_timezone: str = Field(default="Asia/Jakarta", description="Timezone for schedule evaluation")
    schedule_look_ahead_days: int = Field(default=365, ge=1, description="Days ahead to allocate posting slots")
    min_gap_seconds: int = Field(default=180, ge=60, description="Minimum gap between slots in seconds")
    rapid_test_mode: bool = Field(default=False, description="Enable 1-minute interval slots for testing")

    # Media Storage
    media_root: str = Field(default="/home/guinevere/data/x-media", description="Root directory for media assets")

    # Official X API v2 (OAuth 2.0 Bearer Token + auto-refresh)
    x_access_token: str = Field(default="", description="X API OAuth 2.0 Access Token")
    x_refresh_token: str = Field(default="", description="X API OAuth 2.0 Refresh Token")
    x_client_id: str = Field(default="", description="X API OAuth 2.0 Client ID")
    x_client_secret: str = Field(default="", description="X API OAuth 2.0 Client Secret (optional for PKCE)")

    # X media upload fallback (OAuth 1.0a user context; required when OAuth2 media.write is unavailable)
    x_api_key: str = Field(default="", description="X API OAuth 1.0a Consumer/API Key for media upload")
    x_api_secret: str = Field(default="", description="X API OAuth 1.0a Consumer/API Secret for media upload")
    x_oauth1_access_token: str = Field(default="", description="X API OAuth 1.0a Access Token for media upload")
    x_oauth1_access_token_secret: str = Field(default="", description="X API OAuth 1.0a Access Token Secret for media upload")
    x_post_delay_seconds: int = Field(default=2, ge=0, description="Delay in seconds after posting")

    # Caption
    caption_max_length: int = Field(default=200, ge=1, le=280, description="Maximum caption length in characters")
    caption_language: str = Field(default="en", description="Caption language code")
    caption_hashtags: bool = Field(default=False, description="Include hashtags in captions")

    # Moderation
    moderation_fail_safe: bool = Field(default=True, description="Allow posting when Hermes moderation is unavailable")

    # Notifications
    discord_upload_channel_id: str = Field(default="", description="Discord channel for upload notifications")
    discord_dashboard_channel_id: str = Field(default="", description="Discord channel for dashboard notifications")
    discord_guild_id: str = Field(default="", description="Discord guild ID")
    notification_webhook_url: str = Field(default="", description="Webhook URL for notifications")
    owner_user_id: str = Field(default="1146639950654214264", description="Owner Discord user ID")

    # Cleanup
    posted_retention_days: int = Field(default=30, ge=1, description="Days to retain posted media")
    failed_retention_days: int = Field(default=7, ge=1, description="Days to retain failed upload artifacts")

    # Health + Metrics
    health_host: str = Field(default="127.0.0.1", description="Health endpoint bind host")
    health_port: int = Field(default=8097, ge=1024, le=65535, description="Health endpoint bind port")
    metrics_port: int = Field(default=9102, ge=1024, le=65535, description="Prometheus metrics port")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log output format")
    log_output_path: str = Field(default="", description="Log file path (empty for stdout)")


@functools.lru_cache()
def get_xposter_settings() -> XPosterSettings:
    """Return the cached singleton XPosterSettings instance."""
    return XPosterSettings()
