"""Pydantic v2 typed configuration models for the Guinevere fork.

Every field has a sensible default so that configs load without real
secrets (Decision D2 — local-runtime-only).  Secret-bearing fields are
*references* (env-var names as plain strings), never secret values.

Downstream waves append additional nested models; treat this file as
appends-only.
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ── Nested config sections ──────────────────────────────────────────────

class DatabaseConfig(BaseModel):
    """PostgreSQL connection and row-level security settings."""

    pg_dsn: str = "postgresql://localhost:5432/guinevere"
    pg_agent_id: str = ""
    pool_size: int = 5
    rls_enabled: bool = False


class RedisConfig(BaseModel):
    """Redis pub/sub channels and caching configuration."""

    url: str = "redis://localhost:6379"
    db_offset: int = 0
    channels_g2p: str = "guinevere:to:pharsa"
    channels_p2g: str = "pharsa:to:guinevere"
    channels_gp_broadcast: str = "guinevere:pharsa:broadcast"


class AgentConfig(BaseModel):
    """Core agent identity and runtime behaviour."""

    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Guinevere"
    model: str = "gpt-4o-mini"
    provider: str = "openai"
    max_iterations: int = 25
    personality_profile: str = "default"


class HttpConfig(BaseModel):
    """HTTP / gateway server settings."""

    host: str = "127.0.0.1"
    port: int = 8080
    workers: int = 1
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class DelegationConfig(BaseModel):
    """Sub-agent delegation limits."""

    max_concurrent_children: int = 10
    max_depth: int = 5
    max_spawn_depth_cap: int = 5
    spawn_cap: int = 5


class CircuitBreakerConfig(BaseModel):
    """Cost and loop-detection circuit breaker thresholds."""

    cost_threshold: float = 10.0
    loop_fingerprint_threshold: int = 5
    dream_cap_per_hour: int = 5
    subagent_cap: int = 10


class MemoryConfig(BaseModel):
    """Encrypted memory storage configuration.

    ``s4_aes_gcm_256_key_ref`` and ``argon2id_*`` fields are operational
    parameters — the key itself is read from the env var named by the ref
    at runtime, never stored here.
    """

    provider: str = "encrypted"
    s4_aes_gcm_256_key_ref: str = "MEMORY_S4_AES_KEY"
    argon2id_time_cost: int = 3
    argon2id_memory_cost: int = 65536
    argon2id_parallelism: int = 1
    rls_agent_id: str = ""


class ConsciousnessConfig(BaseModel):
    """Consciousness thought-stream configuration.

    Controls the unified thought stream (replaces 7-substrate pattern).
    ``thought_type_weights`` maps ThoughtType values to base selection
    weights (affect-based modulation applied at runtime).
    """

    enabled: bool = True
    continuous_stream: bool = True
    heartbeat_intervals: list[int] = Field(
        default_factory=lambda: [60, 300, 900],
    )
    dreaming_pct: float = 0.05
    thought_type_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "cognition": 0.30,
            "reflection": 0.15,
            "planning": 0.10,
            "dreaming": 0.10,
            "meta": 0.20,
            "heartbeat": 0.15,
        },
    )


class EmotionConfig(BaseModel):
    """Emotional state classification settings."""

    moods: list[str] = Field(
        default_factory=lambda: [
            "joy", "sadness", "anger", "fear", "surprise", "disgust",
            "trust", "anticipation", "love", "guilt", "shame", "pride",
            "envy", "jealousy", "nostalgia", "serenity",
        ],
    )
    classification_mode: str = "mock"


class GovernanceConfig(BaseModel):
    """Multi-CEO governance and department structure."""

    departments: list[str] = Field(default_factory=list)
    co_ceos: dict[str, list[str]] = Field(default_factory=dict)
    multisig_threshold: int = 2


class TailscaleConfig(BaseModel):
    """Tailscale VPN and network hardening."""

    enabled: bool = False
    auth_key_ref: str = "TAILSCALE_AUTH_KEY"
    hardening: str = "ufw-tailscale0-only"


class PersonalityConfig(BaseModel):
    """Personality drift monitoring and calibration."""

    drift_threshold: float = 0.68
    peer_monitor_interval: int = 300
    signature_calibration: dict[str, Any] = Field(default_factory=dict)


# ── Top-level settings ──────────────────────────────────────────────────

class GuinevereConfig(BaseSettings):
    """Root configuration for a Guinevere instance.

    Config priority (pydantic-settings default):
        constructor init  >  env vars  >  YAML file  >  .env

    ``_yaml_file`` is accepted as a constructor kwarg to point at the
    instance YAML (e.g. ``config/guinevere.yaml``).
    """

    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    # ── Instance identity ──
    instance_role: str = "guinevere"
    enabled_modules: list[str] = Field(
        default_factory=lambda: [
            "m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8",
            "m9", "m10", "m11", "m12", "m13", "m14", "m15", "m16", "m17",
        ],
    )
    soul_md_path: str = "config/souls/guinevere-soul.md"
    discord_bot_token_ref: str = "DISCORD_BOT_TOKEN"

    # ── Nested sections ──
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    http: HttpConfig = Field(default_factory=HttpConfig)
    delegation: DelegationConfig = Field(default_factory=DelegationConfig)
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig,
    )
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    consciousness: ConsciousnessConfig = Field(
        default_factory=ConsciousnessConfig,
    )
    emotion: EmotionConfig = Field(default_factory=EmotionConfig)
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    tailscale: TailscaleConfig = Field(default_factory=TailscaleConfig)
    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)
