from __future__ import annotations

"""P12 Gmail module configuration via pydantic-settings."""

import json
from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings


def _parse_list_field(v: str | list[str]) -> list[str]:
    """Parse a ``list[str]`` env var that may be JSON, comma-separated, or empty.

    Handles:
    - ``["a", "b"]`` (JSON array)
    - ``"a,b,c"`` (comma-separated)
    - ``""`` (empty → ``[]``)
    - ``["scope"]`` (JSON single-element)
    """
    if isinstance(v, list):
        return v
    if not isinstance(v, str):
        return []
    stripped = v.strip()
    if not stripped:
        return []
    # Try JSON first
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(s).strip() for s in parsed]
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: comma-separated
    return [s.strip() for s in stripped.split(",") if s.strip()]


ListOfStrings = Annotated[list[str], BeforeValidator(_parse_list_field)]


class GmailSettings(BaseSettings):
    """Gmail integration configuration.

    All values loaded from environment variables with GMAIL_ prefix.
    Secrets are loaded from SOPS-decrypted paths at runtime.
    """

    model_config = {"env_prefix": "GMAIL_", "case_sensitive": False}

    # OAuth2
    credentials_path: Path = Field(
        default=Path("/run/guinevere/gmail-token.json"),
        description="Path to SOPS-decrypted OAuth2 credentials JSON",
    )
    client_id: str = Field(default="", description="OAuth2 client ID")
    client_secret: str = Field(
        default="", description="OAuth2 client secret (loaded from SOPS)"
    )
    scopes: ListOfStrings = Field(
        default=["https://www.googleapis.com/auth/gmail.modify"],
        description="Gmail API OAuth2 scopes",
    )

    # Pub/Sub
    pubsub_project_id: str = Field(
        default="guinevere-gmail-prod", description="GCP project ID"
    )
    pubsub_topic: str = Field(
        default="gmail-watch", description="Pub/Sub topic name"
    )
    pubsub_subscription: str = Field(
        default="gmail-watch-sub", description="Pub/Sub subscription name"
    )
    pubsub_service_account_path: Path = Field(
        default=Path("/run/guinevere/gmail-sa.json"),
        description="Path to SOPS-decrypted service account key",
    )

    # Sync
    sync_poll_interval_seconds: int = Field(
        default=300, ge=60, le=3600, description="Polling fallback interval"
    )
    sync_backfill_days: int = Field(
        default=30, ge=1, le=90, description="Days to backfill on first sync"
    )

    # Classification
    classification_confidence_threshold: float = Field(
        default=0.85, ge=0.5, le=1.0
    )
    importance_notify_threshold: int = Field(default=5, ge=1, le=15)

    # Draft
    draft_timeout_hours: int = Field(
        default=24, ge=1, le=168, description="Hours before draft expires"
    )
    draft_max_length: int = Field(default=5000, ge=100, le=20000)
    draft_min_length: int = Field(default=50, ge=10, le=500)

    # Resend (transactional email)
    resend_api_key: str = Field(
        default="", description="Resend API key (loaded from SOPS)"
    )
    resend_from_email: str = Field(
        default="noreply@guinevere.dev", description="Resend sender address"
    )
    resend_daily_limit: int = Field(default=100, ge=1, le=1000)

    # Notification
    notification_rate_limit_per_hour: int = Field(default=10, ge=1, le=100)
    quiet_hours_start: int = Field(
        default=23, ge=0, le=23, description="Quiet hours start (WIB)"
    )
    quiet_hours_end: int = Field(
        default=7, ge=0, le=23, description="Quiet hours end (WIB)"
    )

    # Briefing
    briefing_hour: int = Field(
        default=8, ge=0, le=23, description="Morning briefing hour (WIB)"
    )
    briefing_timezone: str = Field(default="Asia/Jakarta")

    # Health
    health_port: int = Field(default=8096, ge=1024, le=65535)
    health_host: str = Field(default="127.0.0.1")
    metrics_port: int = Field(default=9101, ge=1024, le=65535)

    # API Quota
    api_quota_limit_per_minute: int = Field(
        default=6000, description="Gmail API quota units/min"
    )

    # Whitelist (comma-separated emails for importance scoring)
    sender_whitelist: ListOfStrings = Field(
        default_factory=list, description="Whitelisted sender emails"
    )


_settings: GmailSettings | None = None


def get_gmail_settings() -> GmailSettings:
    """Return the module-level singleton GmailSettings instance."""
    global _settings
    if _settings is None:
        _settings = GmailSettings()
    return _settings
