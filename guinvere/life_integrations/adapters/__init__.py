"""P22 integration adapters.

Concrete adapters for each integration. Each inherits BaseIntegrationAdapter
and declares capabilities + permission tiers. Adapters without credentials
report CONFIG_MISSING status honestly, not fake success.
"""

from __future__ import annotations

from guinvere.life_integrations.adapters.discord_adapter import DiscordIntegrationAdapter
from guinvere.life_integrations.adapters.gmail_adapter import GmailIntegrationAdapter
from guinvere.life_integrations.adapters.github_adapter import GitHubIntegrationAdapter
from guinvere.life_integrations.adapters.calendar_adapter import (
    CalendarIntegrationAdapter,
)
from guinvere.life_integrations.adapters.drive_adapter import DriveIntegrationAdapter
from guinvere.life_integrations.adapters.notion_adapter import NotionIntegrationAdapter
from guinvere.life_integrations.adapters.telegram_adapter import (
    TelegramIntegrationAdapter,
)
from guinvere.life_integrations.adapters.whatsapp_adapter import (
    WhatsAppIntegrationAdapter,
)
from guinvere.life_integrations.adapters.vps_adapter import VPSIntegrationAdapter
from guinvere.life_integrations.adapters.finance_adapter import (
    FinanceIntegrationAdapter,
)
from guinvere.life_integrations.adapters.browser_adapter import (
    BrowserIntegrationAdapter,
)
from guinvere.life_integrations.adapters.memory_adapter import MemoryIntegrationAdapter
from guinvere.life_integrations.adapters.filesystem_adapter import (
    FilesystemIntegrationAdapter,
)

# P22.3 onboarding manifest (B5) — re-exported for /integrations/missing.
from guinvere.life_integrations.adapters.onboarding_manifest import (  # noqa: E402
    ONBOARDING_MANIFEST,
    AdapterOnboarding,
    EnvVarHint,
)

__all__ = [
    "BrowserIntegrationAdapter",
    "CalendarIntegrationAdapter",
    "DiscordIntegrationAdapter",
    "DriveIntegrationAdapter",
    "FilesystemIntegrationAdapter",
    "FinanceIntegrationAdapter",
    "GitHubIntegrationAdapter",
    "GmailIntegrationAdapter",
    "MemoryIntegrationAdapter",
    "NotionIntegrationAdapter",
    "TelegramIntegrationAdapter",
    "VPSIntegrationAdapter",
    "WhatsAppIntegrationAdapter",
    # P22.3 onboarding manifest (B5)
    "ONBOARDING_MANIFEST",
    "AdapterOnboarding",
    "EnvVarHint",
]
