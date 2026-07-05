"""P22 Life Integration Hub — core runtime package.

Provides unified integration registry, permission model, consent enforcement,
and audit trail for all external integrations (Discord, Gmail, GitHub, Drive,
Calendar, Telegram, WhatsApp, VPS, Finance, Browser, Memory/KG, Filesystem).

All integrations inherit BaseIntegrationAdapter and declare capabilities
(read/write/delete/execute/search/sync) with L1-L4 permission tiers.
"""

from __future__ import annotations

from guinevere.life_integrations.base import BaseIntegrationAdapter
from guinevere.life_integrations.registry import IntegrationRegistry
from guinevere.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    IntegrationId,
    IntegrationStatus,
    PermissionTier,
)

__all__ = [
    "BaseIntegrationAdapter",
    "IntegrationCapability",
    "IntegrationConfig",
    "IntegrationHealth",
    "IntegrationId",
    "IntegrationRegistry",
    "IntegrationStatus",
    "PermissionTier",
]
