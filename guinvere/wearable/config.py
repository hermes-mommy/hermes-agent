"""Wearable configuration loaded from environment variables."""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass

from structlog.stdlib import BoundLogger, get_logger

logger: BoundLogger = get_logger(__name__)

_ALLOWED_REGIONS = {"cn", "de", "ru", "us", "global"}


@dataclass(slots=True)
class WearableConfig:
    """Configuration for Mi Fitness Cloud wearable sync."""

    mi_fitness_user_id: str = ""
    mi_fitness_pass_token: str = ""
    mi_fitness_region: str = "cn"
    mi_fitness_token_path: str = "/run/secrets/mi_fitness_token.json"
    mi_fitness_relative_uid: str = ""

    # Data source selection: "mi_fitness" or "gadgetbridge"
    wearable_data_source: str = "mi_fitness"
    # Gadgetbridge SQLite export path
    gadgetbridge_db_path: str = "/run/secrets/gadgetbridge_export/Gadgetbridge"
    # Gadgetbridge device name for tagging
    gadgetbridge_device_name: str = ""
    # Health Connect JSON export path
    health_connect_json_path: str = "/var/lib/guinevere/health-connect-export/export.json"
    # Health Connect device name for tagging
    health_connect_device_name: str = ""

    wearable_device_id: str = ""
    wearable_owner_id: str = ""

    wearable_sync_interval_sec: int = 1800
    wearable_sync_lookback_hours: int = 2

    wearable_circuit_breaker_threshold: int = 3
    wearable_circuit_breaker_recovery_sec: int = 1800

    wearable_quiet_hours_start: str = "23:00"
    wearable_quiet_hours_end: str = "07:00"
    wearable_alert_rate_limit: int = 5
    wearable_timezone: str = "Asia/Shanghai"

    wearable_ghi_suppression_threshold: float = 0.4
    wearable_ghi_penalty_cap: float = 0.15
    wearable_ghi_decay_days: int = 3

    redis_host: str = "localhost"
    redis_port: int = 6380
    redis_password: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "guinevere"
    postgres_user: str = "guinevere"
    postgres_password: str = ""

    @classmethod
    def from_env(cls) -> WearableConfig:
        """Load wearable configuration from environment variables."""

        config = cls(
            mi_fitness_user_id=os.getenv("MI_FITNESS_USER_ID", ""),
            mi_fitness_pass_token=os.getenv("MI_FITNESS_PASS_TOKEN", ""),
            mi_fitness_region=os.getenv("MI_FITNESS_REGION", "cn"),
            mi_fitness_token_path=os.getenv("MI_FITNESS_TOKEN_PATH", "/run/secrets/mi_fitness_token.json"),
            mi_fitness_relative_uid=os.getenv("MI_FITNESS_RELATIVE_UID", ""),
            wearable_data_source=os.getenv("WEARABLE_DATA_SOURCE", "mi_fitness"),
            gadgetbridge_db_path=os.getenv("GADGETBRIDGE_DB_PATH", "/run/secrets/gadgetbridge_export/Gadgetbridge"),
            gadgetbridge_device_name=os.getenv("GADGETBRIDGE_DEVICE_NAME", ""),
            health_connect_json_path=os.getenv("HEALTH_CONNECT_JSON_PATH", "/var/lib/guinevere/health-connect-export/export.json"),
            health_connect_device_name=os.getenv("HEALTH_CONNECT_DEVICE_NAME", ""),
            wearable_device_id=os.getenv("WEARABLE_DEVICE_ID", ""),
            wearable_owner_id=os.getenv("WEARABLE_OWNER_ID", ""),
            wearable_sync_interval_sec=int(os.getenv("WEARABLE_SYNC_INTERVAL_SEC", "1800")),
            wearable_sync_lookback_hours=int(os.getenv("WEARABLE_SYNC_LOOKBACK_HOURS", "2")),
            wearable_circuit_breaker_threshold=int(os.getenv("WEARABLE_CIRCUIT_BREAKER_THRESHOLD", "3")),
            wearable_circuit_breaker_recovery_sec=int(os.getenv("WEARABLE_CIRCUIT_BREAKER_RECOVERY_SEC", "1800")),
            wearable_quiet_hours_start=os.getenv("WEARABLE_QUIET_HOURS_START", "23:00"),
            wearable_quiet_hours_end=os.getenv("WEARABLE_QUIET_HOURS_END", "07:00"),
            wearable_alert_rate_limit=int(os.getenv("WEARABLE_ALERT_RATE_LIMIT", "5")),
            wearable_timezone=os.getenv("WEARABLE_TIMEZONE", "Asia/Shanghai"),
            wearable_ghi_suppression_threshold=float(os.getenv("WEARABLE_GHI_SUPPRESSION_THRESHOLD", "0.4")),
            wearable_ghi_penalty_cap=float(os.getenv("WEARABLE_GHI_PENALTY_CAP", "0.15")),
            wearable_ghi_decay_days=int(os.getenv("WEARABLE_GHI_DECAY_DAYS", "3")),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6380")),
            redis_password=os.getenv("REDIS_PASSWORD", ""),
            postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
            postgres_port=int(os.getenv("POSTGRES_PORT", "5433")),
            postgres_db=os.getenv("POSTGRES_DB", "guinevere"),
            postgres_user=os.getenv("POSTGRES_USER", "guinevere"),
            postgres_password=os.getenv("POSTGRES_PASSWORD", ""),
        )

        if config.mi_fitness_region not in _ALLOWED_REGIONS:
            allowed_regions = ", ".join(sorted(_ALLOWED_REGIONS))
            raise ValueError(
                f"Invalid MI_FITNESS_REGION={config.mi_fitness_region!r}; expected one of {allowed_regions}"
            )

        if config.wearable_data_source not in ("mi_fitness", "gadgetbridge", "health_connect"):
            raise ValueError(
                f"Invalid WEARABLE_DATA_SOURCE={config.wearable_data_source!r}; expected 'mi_fitness', 'gadgetbridge', or 'health_connect'"
            )

        logger.info(
            "wearable_config_loaded",
            mi_fitness_region=config.mi_fitness_region,
            wearable_data_source=config.wearable_data_source,
            wearable_device_id_present=bool(config.wearable_device_id),
            wearable_owner_id_present=bool(config.wearable_owner_id),
            redis_host=config.redis_host,
            postgres_host=config.postgres_host,
        )
        return config


@functools.lru_cache()
def get_wearable_config() -> WearableConfig:
    """Return cached wearable configuration."""

    return WearableConfig.from_env()
