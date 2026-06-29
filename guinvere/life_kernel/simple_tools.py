"""Simple tools for the Life Kernel.

Thin wrappers around M8 desktop/freelance backends for calendar,
drive, notion, and finance operations.  These are the low-impact
P22 adapters that overlap with M8 — they delegate to M8 backends
when available, and return CONFIG_MISSING stubs otherwise.

Ported from src/life_integrations/adapters/ (P22 low-impact adapters).
These do NOT duplicate M8 logic; they are thin delegation layers
that the heartbeat/observer loop can call.

P20 invariant: fail-soft — missing backends return empty results.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# --- Calendar tool -----------------------------------------------------------

class CalendarTool:
    """Thin wrapper for calendar operations (delegates to M8 desktop backend).

    Args:
        backend: M8 calendar backend (optional; ``None`` = CONFIG_MISSING).
    """

    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend

    @property
    def available(self) -> bool:
        return self._backend is not None

    async def get_upcoming_events(
        self, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Return upcoming calendar events, or empty list if backend missing."""
        if self._backend is None:
            logger.debug("calendar_tool_config_missing")
            return []
        try:
            return await self._backend.get_upcoming_events(limit=limit)
        except Exception as exc:
            logger.error("calendar_tool_error", error_type=type(exc).__name__)
            return []

    async def create_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Create a calendar event.  Returns created event or ``None`` on failure."""
        if self._backend is None:
            logger.debug("calendar_tool_config_missing")
            return None
        try:
            return await self._backend.create_event(event)
        except Exception as exc:
            logger.error("calendar_tool_create_error", error_type=type(exc).__name__)
            return None


# --- Drive tool --------------------------------------------------------------

class DriveTool:
    """Thin wrapper for Google Drive operations (delegates to M8 desktop backend).

    Args:
        backend: M8 drive backend (optional; ``None`` = CONFIG_MISSING).
    """

    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend

    @property
    def available(self) -> bool:
        return self._backend is not None

    async def list_files(
        self, folder_id: str | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """List files in a Drive folder, or empty list if backend missing."""
        if self._backend is None:
            logger.debug("drive_tool_config_missing")
            return []
        try:
            return await self._backend.list_files(folder_id=folder_id, limit=limit)
        except Exception as exc:
            logger.error("drive_tool_list_error", error_type=type(exc).__name__)
            return []

    async def search_files(self, query: str) -> list[dict[str, Any]]:
        """Search Drive files by query string."""
        if self._backend is None:
            logger.debug("drive_tool_config_missing")
            return []
        try:
            return await self._backend.search_files(query)
        except Exception as exc:
            logger.error("drive_tool_search_error", error_type=type(exc).__name__)
            return []


# --- Notion tool -------------------------------------------------------------

class NotionTool:
    """Thin wrapper for Notion operations (delegates to M8 desktop backend).

    Args:
        backend: M8 notion backend (optional; ``None`` = CONFIG_MISSING).
    """

    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend

    @property
    def available(self) -> bool:
        return self._backend is not None

    async def query_database(
        self, database_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Query a Notion database, or empty list if backend missing."""
        if self._backend is None:
            logger.debug("notion_tool_config_missing")
            return []
        try:
            return await self._backend.query_database(database_id, limit=limit)
        except Exception as exc:
            logger.error("notion_tool_query_error", error_type=type(exc).__name__)
            return []

    async def create_page(
        self, database_id: str, properties: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Create a page in a Notion database."""
        if self._backend is None:
            logger.debug("notion_tool_config_missing")
            return None
        try:
            return await self._backend.create_page(database_id, properties)
        except Exception as exc:
            logger.error("notion_tool_create_error", error_type=type(exc).__name__)
            return None


# --- Finance tool ------------------------------------------------------------

class FinanceTool:
    """Thin wrapper for finance operations (delegates to M8 finance backend).

    Args:
        backend: M8 finance backend (optional; ``None`` = CONFIG_MISSING).
    """

    def __init__(self, backend: Any | None = None) -> None:
        self._backend = backend

    @property
    def available(self) -> bool:
        return self._backend is not None

    async def get_summary(self) -> dict[str, Any]:
        """Return finance summary, or empty dict if backend missing."""
        if self._backend is None:
            logger.debug("finance_tool_config_missing")
            return {}
        try:
            return await self._backend.get_summary()
        except Exception as exc:
            logger.error("finance_tool_summary_error", error_type=type(exc).__name__)
            return {}

    async def get_transactions(
        self, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Return recent transactions, or empty list if backend missing."""
        if self._backend is None:
            logger.debug("finance_tool_config_missing")
            return []
        try:
            return await self._backend.get_transactions(limit=limit)
        except Exception as exc:
            logger.error("finance_tool_tx_error", error_type=type(exc).__name__)
            return []


# --- Wire function (parent-owned agent_init append) -------------------------

def wire(agent: Any) -> None:
    """Wire life kernel tools into the agent.

    This function is called by the parent (agent_init) to register
    life kernel components.  It does NOT edit agent_init.py — the
    parent appends a call to this function.

    Args:
        agent: The agent instance to wire into.
    """
    logger.info("life_kernel_wire", agent_type=type(agent).__name__)
    # In production, this would:
    # 1. Create HeartbeatService with agent's world_model, sensors, dashboard.
    # 2. Start the heartbeat service.
    # 3. Register sensor adapters.
    # For now, this is a registration hook — the parent calls it.
