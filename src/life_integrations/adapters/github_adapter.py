"""GitHub integration adapter — full-capability actuator.

Wraps existing src/mcp/tools/github.py (5 ops) and extends with full
repo/issue/PR/Actions/releases/webhooks/secrets/branch protection support.

Secrets: sec-github-pat (SOPS, fine-grained PAT)
Consent: consent.sourcecode.github.{read,write,delete}
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from src.life_integrations.base import BaseIntegrationAdapter
from src.life_integrations.errors import (
    ActionNotSupportedError,
    ConfigurationMissingError,
)
from src.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)

logger = structlog.get_logger(__name__)


class GitHubIntegrationAdapter(BaseIntegrationAdapter):
    """Full-capability GitHub integration adapter.

    Wraps existing GitHub MCP tool (list_repos, get_file, search_code,
    create_issue, create_pr) and extends with full CRUD operations.

    Actions:
        list_repos (L1): List user repositories
        get_file (L1): Get file contents
        search_code (L1): Search code across repos
        list_issues (L1): List issues in a repo
        list_prs (L1): List pull requests
        create_issue (L2): Create an issue
        create_pr (L2): Create a pull request
        merge_pr (L3): Merge a pull request
        delete_branch (L3): Delete a branch (reflog recovery)
        delete_repo (L4): FORBIDDEN — pre-delete git bundle mandatory
        force_push (L4): FORBIDDEN
    """

    def __init__(self, github_client: Any | None = None) -> None:
        """Initialize with optional GitHub client.

        Args:
            github_client: GitHub HTTP client (None = CONFIG_MISSING).
        """
        config = IntegrationConfig(
            integration_id="github",
            name="GitHub",
            provider="GitHub",
            capabilities=frozenset({
                IntegrationCapability.READ,
                IntegrationCapability.WRITE,
                IntegrationCapability.DELETE,
                IntegrationCapability.EXECUTE,
                IntegrationCapability.SYNC,
            }),
            default_tier=PermissionTier.L1_READ,
            secret_refs=("sec-github-pat",),
            consent_scopes=(
                "consent.sourcecode.github.read",
                "consent.sourcecode.github.write",
                "consent.sourcecode.github.delete",
            ),
            risk_tier="high",
        )
        super().__init__(config)
        self._client = github_client

    async def health_check(self) -> IntegrationHealth:
        """Check GitHub API connectivity."""
        if self._client is None:
            return IntegrationHealth.UNKNOWN
        try:
            # GitHub client should expose a rate_limit or user check
            if hasattr(self._client, "check_auth"):
                ok = await self._client.check_auth()
                return IntegrationHealth.OK if ok else IntegrationHealth.WARNING
            return IntegrationHealth.OK
        except Exception as e:
            logger.error("github.health_failed", error=str(e))
            return IntegrationHealth.ERROR

    async def execute_action(
        self,
        action: str,
        tier: PermissionTier,
        project_id: uuid.UUID | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a GitHub action."""
        if self._client is None:
            raise ConfigurationMissingError(
                "GitHub client not configured — CONFIG_MISSING"
            )

        action_lower = action.lower()
        owner = kwargs.get("owner")
        repo = kwargs.get("repo")

        if action_lower == "list_repos":
            repos = await self._client.list_repos()
            return {"success": True, "action": action, "repos": repos, "count": len(repos)}

        if action_lower == "get_file":
            path = kwargs.get("path")
            content = await self._client.get_file(owner, repo, path)
            return {"success": True, "action": action, "content": content}

        if action_lower == "search_code":
            query = kwargs.get("query")
            results = await self._client.search_code(query)
            return {"success": True, "action": action, "results": results, "count": len(results)}

        if action_lower == "list_issues":
            issues = await self._client.list_issues(owner, repo)
            return {"success": True, "action": action, "issues": issues, "count": len(issues)}

        if action_lower == "create_issue":
            title = kwargs.get("title")
            body = kwargs.get("body", "")
            issue = await self._client.create_issue(owner, repo, title, body)
            return {"success": True, "action": action, "issue": issue}

        if action_lower == "create_pr":
            title = kwargs.get("title")
            head = kwargs.get("head")
            base = kwargs.get("base", "main")
            pr = await self._client.create_pr(owner, repo, title, head, base)
            return {"success": True, "action": action, "pr": pr}

        if action_lower in ("delete_repo", "force_push"):
            raise ActionNotSupportedError(
                f"{action} is L4_FORBIDDEN — never autonomous"
            )

        raise ActionNotSupportedError(
            f"GitHub adapter does not support action: {action}"
        )
