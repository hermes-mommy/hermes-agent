"""Browser/research integration adapter — wraps existing search/fetch tools.

Wraps guinevere/mcp/tools/brave_search.py, exa_search.py, websearch.py, fetch.py,
obscura_cdp.py. No secrets sent to web tools. Read/search = L1, fill/click = L2.

Consent: consent.research.browser.{read,write}
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from guinevere.life_integrations.base import BaseIntegrationAdapter
from guinevere.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
)
from guinevere.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)

logger = structlog.get_logger(__name__)


class BrowserIntegrationAdapter(BaseIntegrationAdapter):
    """Browser/research integration adapter (wraps existing MCP tools).

    Actions:
        search (L1): Web search (brave/exa/websearch)
        fetch_url (L1): Fetch URL content (1MB limit)
        navigate (L1): Navigate to a page (obscura)
        get_markdown (L1): Get page as markdown
        fill_form (L2): Fill a form field
        click (L2): Click an element

    Note: No secrets/personal data sent to web tools (AGENTS.md §12).
    """

    def __init__(
        self,
        search_client: Any | None = None,
        fetch_client: Any | None = None,
        browser_client: Any | None = None,
    ) -> None:
        """Initialize with optional search/fetch/browser clients.

        Args:
            search_client: Search tool wrapper (None = CONFIG_MISSING).
            fetch_client: Fetch tool wrapper (None = CONFIG_MISSING).
            browser_client: Obscura CDP wrapper (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="browser",
            name="Browser/Research",
            provider="Brave/Exa/Obscura",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.SEARCH,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-brave-api", "sec-exa-api"),
            consent_scopes=(
                "consent.research.browser.read",
                "consent.research.browser.write",
            ),
            risk_tier="low",
        )
        super().__init__(config)
        self._search = search_client
        self._fetch = fetch_client
        self._browser = browser_client

    async def health_check(self) -> IntegrationHealth:
        """Check browser/research connectivity."""
        if self._search is None and self._fetch is None and self._browser is None:
            return IntegrationHealth.UNKNOWN
        return IntegrationHealth.OK

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a browser/research action."""
        action_lower = action.lower()

        if action_lower == "search":
            # L1 search — fail-closed-but-actionable. When no search client
            # (no BRAVE_API_KEY/EXA_API_KEY provisioned), return an HONEST
            # structured config_missing result instead of raising. The router
            # routes this to operator provisioning. Never fake success.
            if self._search is None:
                logger.info(
                    "browser.config_missing",
                    action=action,
                    reason="BRAVE_API_KEY/EXA_API_KEY not provisioned",
                )
                return {
                    "success": False,
                    "config_missing": True,
                    "reason": "BRAVE_API_KEY/EXA_API_KEY not provisioned",
                    "action": action,
                }
            query = kwargs.get("query", "")
            results = await self._search.search(query)
            return {
                "success": True,
                "action": action,
                "results": results,
                "count": len(results),
            }

        if action_lower == "fetch_url":
            if self._fetch is None:
                raise ConfigurationMissingError("Fetch client not configured")
            url = kwargs.get("url")
            content = await self._fetch.fetch(url)
            return {
                "success": True,
                "action": action,
                "content": (
                    content[:1000] + "..."
                    if len(content) > 1000 else content
                ),
            }

        if action_lower == "navigate":
            if self._browser is None:
                raise ConfigurationMissingError("Browser client not configured")
            url = kwargs.get("url")
            await self._browser.navigate(url)
            return {"success": True, "action": action, "url": url}

        if action_lower == "fill_form":
            # L2 write — must NEVER silently fake success. Raises
            # ConfigurationMissingError when no browser client is wired.
            if self._browser is None:
                raise ConfigurationMissingError("Browser client not configured")
            url = kwargs.get("url")
            selector = kwargs.get("selector")
            value = kwargs.get("value")
            await self._browser.fill_form(url, selector, value)
            return {
                "success": True,
                "action": action,
                "reversible": False,
                "url": url,
                "selector": selector,
            }

        if action_lower == "click":
            # L2 write — must NEVER silently fake success. Raises
            # ConfigurationMissingError when no browser client is wired.
            if self._browser is None:
                raise ConfigurationMissingError("Browser client not configured")
            url = kwargs.get("url")
            selector = kwargs.get("selector")
            await self._browser.click(url, selector)
            return {
                "success": True,
                "action": action,
                "url": url,
                "selector": selector,
            }

        raise ActionNotSupportedError(
            f"Browser adapter does not support action: {action}"
        )
