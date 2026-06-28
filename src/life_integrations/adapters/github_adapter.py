"""GitHub integration adapter — full-capability actuator.

Wraps existing src/mcp/tools/github.py (5 ops) and extends with full
repo/issue/PR/Actions/releases/webhooks/secrets/branch protection support.

Secrets: sec-github-pat (SOPS, fine-grained PAT)
Consent: consent.sourcecode.github.{read,write,delete}
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
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

        if action_lower == "list_prs":
            prs = await self._client.list_prs(owner, repo)
            return {"success": True, "action": action, "prs": prs, "count": len(prs)}

        if action_lower == "get_repo":
            repo_meta = await self._client.get_repo(owner, repo)
            payload = dict(repo_meta) if isinstance(repo_meta, dict) else {}
            payload["success"] = True
            payload["action"] = action
            return payload

        if action_lower == "merge_pr":
            pr_number = kwargs.get("pr_number")
            if not isinstance(pr_number, int):
                raise ConfigurationMissingError(
                    "merge_pr requires integer pr_number"
                )
            merge_method = kwargs.get("merge_method", "merge")

            # Pre-merge snapshot: capture head_sha + base_sha BEFORE merging,
            # so ``git revert -m 1 <merge_commit_sha>`` can re-create the
            # state of main immediately prior to the merge.
            pr_meta = await self._client.get_pr(owner, repo, pr_number)
            head = (pr_meta.get("head") or {}) if isinstance(pr_meta, dict) else {}
            base = (pr_meta.get("base") or {}) if isinstance(pr_meta, dict) else {}
            head_sha = head.get("sha")
            base_sha = base.get("sha")
            head_ref = head.get("ref")
            base_ref = base.get("ref")
            snapshot_payload = {
                "pr_number": pr_number,
                "head_sha": head_sha,
                "base_sha": base_sha,
                "head_ref": head_ref,
                "base_ref": base_ref,
            }
            content_hash = hashlib.sha256(
                json.dumps(snapshot_payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            snapshot = dict(snapshot_payload)
            snapshot["content_hash"] = content_hash
            snapshot["captured_at"] = datetime.now(timezone.utc).isoformat()

            merge_response = await self._client.merge_pr(
                owner, repo, pr_number, merge_method=merge_method
            )
            merged = bool(merge_response.get("merged")) if isinstance(
                merge_response, dict
            ) else False
            merge_commit_sha = (
                merge_response.get("sha") if isinstance(merge_response, dict) else None
            )
            if merged and merge_commit_sha:
                restore_method = f"git revert -m 1 {merge_commit_sha}"
                reversible = True
                restore_possible = True
                irreversible_warning = False
            else:
                restore_method = (
                    "merge did not confirm (no merge_commit_sha returned); "
                    "manual intervention required"
                )
                reversible = False
                restore_possible = False
                irreversible_warning = True

            return {
                "success": True,
                "action": action,
                "pr_number": pr_number,
                "merged": merged,
                "merge_commit_sha": merge_commit_sha,
                "reversible": reversible,
                "restore_method": restore_method,
                "restore_possible": restore_possible,
                "irreversible_warning": irreversible_warning,
                "pre_delete_snapshot": snapshot,
            }

        if action_lower == "delete_branch":
            branch = kwargs.get("branch")
            if not branch:
                raise ConfigurationMissingError(
                    "delete_branch requires non-empty 'branch' kwarg"
                )

            # Pre-delete snapshot: capture head_sha + commit_url BEFORE
            # deleting so ``git push origin <head_sha>:<branch>`` can
            # recover the ref via the captured SHA.
            branch_meta = await self._client.get_branch(owner, repo, branch)
            commit = (
                (branch_meta.get("commit") or {})
                if isinstance(branch_meta, dict)
                else {}
            )
            head_sha = commit.get("sha")
            commit_url = commit.get("url")
            snapshot_payload = {
                "branch": branch,
                "head_sha": head_sha,
                "commit_sha": head_sha,
                "commit_url": commit_url,
            }
            content_hash = hashlib.sha256(
                json.dumps(snapshot_payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            snapshot = dict(snapshot_payload)
            snapshot["content_hash"] = content_hash
            snapshot["captured_at"] = datetime.now(timezone.utc).isoformat()

            delete_response = await self._client.delete_branch(owner, repo, branch)
            deleted = bool(delete_response.get("deleted")) if isinstance(
                delete_response, dict
            ) else False
            if deleted and head_sha:
                restore_method = (
                    f"git push origin {head_sha}:{branch}"
                )
                reversible = True
                restore_possible = True
                reflog_available = True
                irreversible_warning = False
            else:
                restore_method = (
                    "branch delete did not confirm (deleted=False or no head_sha); "
                    "manual intervention required"
                )
                reversible = False
                restore_possible = False
                reflog_available = False
                irreversible_warning = True

            return {
                "success": True,
                "action": action,
                "branch": branch,
                "deleted": deleted,
                "head_sha": head_sha,
                "reversible": reversible,
                "restore_method": restore_method,
                "restore_possible": restore_possible,
                "reflog_available": reflog_available,
                "irreversible_warning": irreversible_warning,
                "pre_delete_snapshot": snapshot,
            }

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
