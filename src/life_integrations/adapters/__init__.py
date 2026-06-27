"""P22 integration adapters.

Concrete adapters for each integration. Each inherits BaseIntegrationAdapter
and declares capabilities + permission tiers. Adapters without credentials
report CONFIG_MISSING status honestly, not fake success.
"""

from __future__ import annotations

from src.life_integrations.adapters.discord_adapter import DiscordIntegrationAdapter
from src.life_integrations.adapters.gmail_adapter import GmailIntegrationAdapter
from src.life_integrations.adapters.github_adapter import GitHubIntegrationAdapter
from src.life_integrations.adapters.calendar_adapter import (
    CalendarIntegrationAdapter,
)
from src.life_integrations.adapters.drive_adapter import DriveIntegrationAdapter
from src.life_integrations.adapters.notion_adapter import NotionIntegrationAdapter
from src.life_integrations.adapters.telegram_adapter import (
    TelegramIntegrationAdapter,
)
from src.life_integrations.adapters.whatsapp_adapter import (
    WhatsAppIntegrationAdapter,
)
from src.life_integrations.adapters.vps_adapter import VPSIntegrationAdapter
from src.life_integrations.adapters.finance_adapter import (
    FinanceIntegrationAdapter,
)
from src.life_integrations.adapters.browser_adapter import (
    BrowserIntegrationAdapter,
)
from src.life_integrations.adapters.memory_adapter import MemoryIntegrationAdapter
from src.life_integrations.adapters.filesystem_adapter import (
    FilesystemIntegrationAdapter,
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
]
