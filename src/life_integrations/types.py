"""P22 integration type definitions.

Defines the permission tier model, capability flags, health status,
and configuration structures used by all integration adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


class PermissionTier(IntEnum):
    """L1-L4 permission tiers matching AGENTS.md and P22 plan.

    L1 = read-only, no side effects
    L2 = write-notify (non-destructive)
    L3 = destructive-approval (requires explicit consent)
    L4 = forbidden (never autonomous)
    """
    L1_READ = 1
    L2_WRITE = 2
    L3_DESTRUCTIVE = 3
    L4_FORBIDDEN = 4


class IntegrationCapability(str, Enum):
    """Capabilities an integration can declare."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    SEARCH = "search"
    SYNC = "sync"


class IntegrationStatus(str, Enum):
    """Runtime status of an integration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CONFIG_MISSING = "config_missing"
    CONSENT_REVOKED = "consent_revoked"
    HARD_STOP = "hard_stop"
    DISABLED = "disabled"


class IntegrationHealth(str, Enum):
    """Health check result."""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


IntegrationId = str


@dataclass(frozen=True)
class IntegrationConfig:
    """Configuration for a single integration.

    Attributes:
        integration_id: Unique identifier (e.g., "discord", "gmail").
        name: Human-readable name.
        provider: Provider name (e.g., "Google", "GitHub").
        capabilities: Set of declared capabilities.
        default_tier: Default permission tier (typically L1).
        secret_refs: List of secret_id references (no values).
        project_aware: Whether integration supports project_id scoping.
        consent_scopes: Required consent scopes for write/delete.
        risk_tier: Overall risk classification (low/medium/high/critical).
    """
    integration_id: IntegrationId
    name: str
    provider: str
    capabilities: frozenset[IntegrationCapability]
    default_tier: PermissionTier = PermissionTier.L1_READ
    secret_refs: tuple[str, ...] = ()
    project_aware: bool = True
    consent_scopes: tuple[str, ...] = ()
    risk_tier: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)
