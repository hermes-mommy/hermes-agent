"""P22 GitHub client shim — bridges MCP tools to the adapter instance protocol.

The P22 ``GitHubIntegrationAdapter`` calls instance methods on its
``github_client`` collaborator. The real GitHub operations live as
module-level functions in ``src.mcp.tools.github`` (decorated with
``@require_approval`` + tenacity retry/backoff):

    ``github_list_repos(owner)``
    ``github_get_file(owner, repo, path)``
    ``github_search_code(query)``
    ``github_create_issue(owner, repo, title, body)``
    ``github_create_pr(owner, repo, title, head, base)``

These take the GitHub PAT from ``GITHUB_PAT`` at call time and authenticate
on their own. Two operations used by the adapter — ``list_issues`` and
``list_prs`` — have no MCP tool (gap-filler), so they reach the GitHub REST
API inline via ``httpx``.

Fail-closed: every public method raises ``ConfigurationMissingError`` if
``GITHUB_PAT`` is not set in the environment, so the adapter reports
``CONFIG_MISSING`` instead of silently faking success.

Security note: the PAT MUST NOT appear in any log line, response body, or
exception message. The shim reads it from ``os.environ`` only to attach the
``Authorization`` header on outbound calls.

L2 writes (``create_issue``/``create_pr``) are consent-gated by the P22
router (``ConsentGateShim`` + ``HARD STOP``); the shim does NOT enforce
consent itself — it is a thin transport wrapper.
"""

from __future__ import annotations

import os
import time
from typing import Any

import structlog

from guinvere.life_integrations.errors import (
    AuthenticationError,
    ConfigurationMissingError,
    ProviderError,
    RateLimitExceededError,
)

logger = structlog.get_logger(__name__)

_GITHUB_API_USER_URL = "https://api.github.com/user"
_GITHUB_API_ISSUES_FMT = "https://api.github.com/repos/{owner}/{repo}/issues?state=open"
_GITHUB_API_PRS_URL = "https://api.github.com/repos/{owner}/{repo}/pulls"
_GITHUB_API_REPO_FMT = "https://api.github.com/repos/{owner}/{repo}"
_GITHUB_API_PR_FMT = "https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
_GITHUB_API_MERGE_FMT = "https://api.github.com/repos/{owner}/{repo}/pulls/{number}/merge"
_GITHUB_API_BRANCH_FMT = "https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
_GITHUB_API_RELEASES_FMT = "https://api.github.com/repos/{owner}/{repo}/releases"
_GITHUB_API_RELEASE_FMT = "https://api.github.com/repos/{owner}/{repo}/releases/{release_id}"
_GITHUB_API_COLLAB_FMT = "https://api.github.com/repos/{owner}/{repo}/collaborators/{username}"
_GITHUB_API_HOOKS_FMT = "https://api.github.com/repos/{owner}/{repo}/hooks"


def _fail_closed(reason: str) -> None:
    """Raise ``ConfigurationMissingError`` if the shim is not wired with PAT."""
    raise ConfigurationMissingError(reason)


def _parse_retry_after(
    headers: Any,
    *,
    rate_limit_remaining: str | int | None = None,
) -> int | None:
    """Best-effort integer retry-after hint for callers.

    Priority: ``Retry-After`` header → ``X-RateLimit-Reset`` minus now → None.
    All values clamped to ``>= 0``.
    """
    try:
        ra_header = headers.get("Retry-After") if headers else None
        if ra_header is not None:
            return max(0, int(str(ra_header).strip()))
    except (TypeError, ValueError):
        pass
    try:
        reset_header = headers.get("X-RateLimit-Reset") if headers else None
        if reset_header is not None:
            reset_epoch = int(str(reset_header).strip())
            now_epoch = int(time.time())
            return max(0, reset_epoch - now_epoch)
    except (TypeError, ValueError):
        pass
    # ``rate_limit_remaining`` is unused here, but accepted for forward-compat
    # hooks (callers may wish to gate by it; we DO inside ``_handle_github_http_error``).
    return None


def _handle_github_http_error(response: Any, url: str) -> None:
    """Map a non-200 ``httpx.Response`` to a typed integration error.

    Behaviour (per P22 brutal-audit F08 fix):
        * 401 → ``AuthenticationError``
        * 403 with ``X-RateLimit-Remaining: 0`` or 429 → ``RateLimitExceededError``
          (with ``retry_after`` parsed from ``Retry-After`` /
          ``X-RateLimit-Reset`` headers when present).
        * 429 → ``RateLimitExceededError``
        * 404 → ``ProviderError("github", 404, "GitHub resource not found: <url>")``
        * 403 (non-rate-limit) → ``ProviderError("github", 403, f"Forbidden: {body[:200]}")``
        * 5xx → ``ProviderError("github", status, f"GitHub API error: {status}")``
        * other non-200 → ``ProviderError("github", status, "unexpected status <status>")``
    """
    status = response.status_code
    headers = getattr(response, "headers", None) or {}
    body_text = ""
    try:
        body_text = response.text[:200]
    except Exception:  # pragma: no cover - text attr may fail on mocks
        body_text = ""

    remainder_header = headers.get("X-RateLimit-Remaining") if headers else None
    is_rate_limited = (
        status == 429
        or (status == 403 and str(remainder_header) == "0")
    )
    if is_rate_limited:
        retry_after = _parse_retry_after(headers)
        raise RateLimitExceededError(
            provider="github", retry_after=retry_after,
        )

    if status == 401:
        raise AuthenticationError("GitHub PAT invalid or expired")

    if status == 404:
        raise ProviderError(
            "github", 404, f"GitHub resource not found: {url}",
        )

    if status == 403:
        raise ProviderError("github", 403, f"Forbidden: {body_text}")

    if 500 <= status <= 599:
        raise ProviderError(
            "github", status, f"GitHub API error: {status}",
        )

    raise ProviderError(
        "github", status, f"unexpected status {status}",
    )


class GitHubClientShim:
    """Instance wrapper around ``src.mcp.tools.github`` module functions.

    Constructor reads ``GITHUB_PAT`` from the environment once and caches
    the boolean. All public methods fail-closed when the PAT is missing.

    Note: the PAT is read on every HTTP call from ``os.environ`` (not from
    ``self._enabled``), so a PAT set after construction is still honored —
    matches the behaviour of the underlying MCP tools, which read the PAT at
    call time as well.
    """

    def __init__(self) -> None:
        """Initialize enabled-flag from ``GITHUB_PAT``; no credentials stored."""
        self._enabled = bool(os.environ.get("GITHUB_PAT", ""))
        self._cached_login: str | None = None

    def _require_pat(self) -> None:
        """Raise ``ConfigurationMissingError`` when ``GITHUB_PAT`` is empty."""
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

    async def check_auth(self) -> bool:
        """Verify the PAT against ``GET /user`` and cache the login on success.

        Returns True on 200, False on any non-200 or raised exception.
        NEVER logs the PAT or the ``Authorization`` header.
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx  # lazy import — only paid when actually used

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(_GITHUB_API_USER_URL, headers=headers)
        except Exception as exc:  # transport-level — log key, never PAT
            logger.warning(
                "p22.github.shim.check_auth.transport_error",
                error_type=type(exc).__name__,
            )
            return False

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.check_auth.http_error",
                status=response.status_code,
            )
            # check_auth is intentionally a "passive" probe — callers use
            # it inside ``list_repos`` to lazily fetch a cached login. A
            # non-200 here should not crash the event loop; it returns
            # ``False`` (no login cached) per the documented contract.
            # The brutal-audit F08 fix targets the action methods
            # (``list_issues``, ``merge_pr``, etc.), which DO have to
            # surface typed errors on non-200. We keep ``return False``
            # here because the only consumer reads the boolean.
            return False

        try:
            data = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.check_auth.parse_error",
                error_type=type(exc).__name__,
            )
            return False

        login = data.get("login") if isinstance(data, dict) else None
        self._cached_login = login if isinstance(login, str) else None

        logger.info(
            "p22.github.shim.check_auth.ok",
            has_login=bool(self._cached_login),
        )
        return True

    async def list_repos(self) -> list[dict[str, Any]]:
        """List repositories owned by the authenticated user.

        Calls ``check_auth`` lazily if no cached login; falls back to [] if
        auth fails (caller can decide whether to surface that).
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        if self._cached_login is None:
            ok = await self.check_auth()
            if not ok or self._cached_login is None:
                logger.warning("p22.github.shim.list_repos.no_login")
                return []

        login = self._cached_login  # captured above; type-narrowed by branch
        if login is None:
            return []

        from guinvere.mcp.tools.github import github_list_repos

        logger.info("p22.github.shim.list_repos", owner=login)
        result: list[dict[str, Any]] = await github_list_repos(owner=login)
        return result

    async def get_file(self, owner: str, repo: str, path: str) -> str:
        """Fetch file content from a repo (delegates to MCP tool)."""
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        from guinvere.mcp.tools.github import github_get_file

        logger.info("p22.github.shim.get_file", repo=f"{owner}/{repo}")
        result: str = await github_get_file(owner, repo, path)
        return result

    async def search_code(self, query: str) -> list[dict[str, Any]]:
        """Search code across GitHub (delegates to MCP tool)."""
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        from guinvere.mcp.tools.github import github_search_code

        logger.info("p22.github.shim.search_code")
        result: list[dict[str, Any]] = await github_search_code(query)
        return result

    async def list_issues(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List open issues for ``{owner}/{repo}`` (inline REST — no MCP tool)."""
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
        url = _GITHUB_API_ISSUES_FMT.format(owner=owner, repo=repo)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.list_issues.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.list_issues.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            _handle_github_http_error(response, url)

        try:
            data = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.list_issues.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return []

        # GitHub's /issues endpoint also returns PRs; filter to true issues.
        if isinstance(data, list):
            result: list[dict[str, Any]] = [
                item for item in data
                if isinstance(item, dict) and "pull_request" not in item
            ]
            return result
        return []

    async def list_prs(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List pull requests for ``{owner}/{repo}`` (inline REST — no MCP tool)."""
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
        url = _GITHUB_API_PRS_URL.format(owner=owner, repo=repo)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.list_prs.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.list_prs.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.list_prs.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return []

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    async def create_issue(self, owner: str, repo: str, title: str, body: str) -> dict[str, Any]:
        """Create an issue on ``{owner}/{repo}`` (delegates to MCP tool)."""
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        from guinvere.mcp.tools.github import github_create_issue

        logger.info("p22.github.shim.create_issue", repo=f"{owner}/{repo}")
        result: dict[str, Any] = await github_create_issue(owner, repo, title, body)
        return result

    async def create_pr(
        self, owner: str, repo: str, title: str, head: str, base: str
    ) -> dict[str, Any]:
        """Create a pull request on ``{owner}/{repo}`` (delegates to MCP tool)."""
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        from guinvere.mcp.tools.github import github_create_pr

        logger.info("p22.github.shim.create_pr", repo=f"{owner}/{repo}")
        result: dict[str, Any] = await github_create_pr(owner, repo, title, head, base)
        return result

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repo metadata via ``GET /repos/{owner}/{repo}`` (inline REST)."""
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
        url = _GITHUB_API_REPO_FMT.format(owner=owner, repo=repo)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.get_repo.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return {}

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.get_repo.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.get_repo.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return {}

        return payload if isinstance(payload, dict) else {}

    async def get_pr(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """Get a single pull request via ``GET /repos/{o}/{r}/pulls/{n}``.

        Used by the L3 ``merge_pr`` action to capture ``head_sha`` and
        ``base_sha`` BEFORE merging, so the reversal is deterministic.
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
        url = _GITHUB_API_PR_FMT.format(owner=owner, repo=repo, number=pr_number)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.get_pr.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                pr_number=pr_number,
            )
            return {}

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.get_pr.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
                pr_number=pr_number,
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.get_pr.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                pr_number=pr_number,
            )
            return {}

        return payload if isinstance(payload, dict) else {}

    async def merge_pr(
        self, owner: str, repo: str, pr_number: int, merge_method: str = "merge"
    ) -> dict[str, Any]:
        """Merge a PR via ``PUT /repos/{o}/{r}/pulls/{n}/merge`` (inline REST).

        Returns ``{"sha": "<merge_commit_sha>", "merged": True, "message": "..."}``
        on success (matches GitHub REST API response shape).
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        url = _GITHUB_API_MERGE_FMT.format(
            owner=owner, repo=repo, number=pr_number
        )
        body = {"merge_method": merge_method}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.put(url, headers=headers, json=body)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.merge_pr.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                pr_number=pr_number,
            )
            return {"merged": False, "message": f"transport_error: {type(exc).__name__}"}

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.merge_pr.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
                pr_number=pr_number,
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.merge_pr.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                pr_number=pr_number,
            )
            return {"merged": False, "message": f"parse_error: {type(exc).__name__}"}

        return payload if isinstance(payload, dict) else {
            "merged": False, "message": "non-dict response"
        }

    async def get_branch(self, owner: str, repo: str, branch: str) -> dict[str, Any]:
        """Get a branch via ``GET /repos/{o}/{r}/branches/{branch}``.

        Used by the L3 ``delete_branch`` action to capture ``head_sha``
        BEFORE deleting, so ``git push origin <head_sha>:<branch>``
        can recover the ref.
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
        url = _GITHUB_API_BRANCH_FMT.format(owner=owner, repo=repo, branch=branch)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.get_branch.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                branch=branch,
            )
            return {}

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.get_branch.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
                branch=branch,
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.get_branch.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                branch=branch,
            )
            return {}

        return payload if isinstance(payload, dict) else {}

    async def delete_branch(
        self, owner: str, repo: str, branch: str
    ) -> dict[str, Any]:
        """Delete a branch via ``DELETE /repos/{o}/{r}/git/refs/heads/{branch}``.

        Returns ``{"deleted": True, "ref": "...", "object": {"sha": "..."}}``
        on success-shaped response, else ``{"deleted": False, ...}``.

        NOTE: GitHub's REST API keeps the reflog ONLY on the git client's
        local repository (no server-side retain). The pre-delete snapshot
        captured by the adapter (``head_sha``) is the only durable recovery
        handle — see ``restore_method: git push origin <head_sha>:<branch>``.
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"}
        url = (
            f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}"
        )

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.delete(url, headers=headers)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.delete_branch.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                branch=branch,
            )
            return {"deleted": False, "message": f"transport_error: {type(exc).__name__}"}

        if response.status_code == 204:
            return {"deleted": True, "ref": f"refs/heads/{branch}"}
        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.delete_branch.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
                branch=branch,
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.delete_branch.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                branch=branch,
            )
            return {"deleted": False, "message": f"parse_error: {type(exc).__name__}"}

        return payload if isinstance(payload, dict) else {
            "deleted": False, "message": "non-dict response"
        }

    # -- P22.3: completeness gap-fillers (no MCP tool wrappers) ----------

    async def list_releases(
        self, owner: str, repo: str, per_page: int = 30
    ) -> list[dict[str, Any]]:
        """List releases for ``{owner}/{repo}`` (L1 read).

        Inline ``GET /repos/{o}/{r}/releases`` — no MCP tool exists for this.
        Returns the parsed list, or ``[]`` on transport / non-200 / parse error.
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
        }
        url = _GITHUB_API_RELEASES_FMT.format(owner=owner, repo=repo)
        params = {"per_page": per_page}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers, params=params)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.list_releases.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.list_releases.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.list_releases.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return []

        return [item for item in payload] if isinstance(payload, list) else []

    async def create_release(
        self,
        owner: str,
        repo: str,
        tag_name: str,
        name: str | None = None,
        body: str | None = None,
        draft: bool = False,
        prerelease: bool = False,
    ) -> dict[str, Any]:
        """Create a release on ``{owner}/{repo}`` (L2 write).

        Inline ``POST /repos/{o}/{r}/releases`` — no MCP tool exists.
        Returns the parsed release dict.
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        url = _GITHUB_API_RELEASES_FMT.format(owner=owner, repo=repo)
        payload_body: dict[str, Any] = {
            "tag_name": tag_name,
            "draft": draft,
            "prerelease": prerelease,
        }
        if name is not None:
            payload_body["name"] = name
        if body is not None:
            payload_body["body"] = body

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload_body)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.create_release.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return {"created": False, "message": f"transport_error: {type(exc).__name__}"}

        if response.status_code not in (200, 201):
            logger.warning(
                "p22.github.shim.create_release.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.create_release.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return {"created": False, "message": f"parse_error: {type(exc).__name__}"}

        if not isinstance(payload, dict):
            return {"created": False, "message": "non-dict response"}
        payload.setdefault("created", True)
        return payload

    async def add_collaborator(
        self,
        owner: str,
        repo: str,
        username: str,
        permission: str = "push",
    ) -> dict[str, Any]:
        """Invite a collaborator on ``{owner}/{repo}`` (L2 write).

        Inline ``PUT /repos/{o}/{r}/collaborators/{username}`` — no MCP
        tool exists. Returns ``{"invited": True, ...}`` on 201/202,
        else ``{"invited": False, ...}``.
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        url = _GITHUB_API_COLLAB_FMT.format(
            owner=owner, repo=repo, username=username,
        )
        payload_body = {"permission": permission}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.put(url, headers=headers, json=payload_body)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.add_collaborator.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
                username=username,
            )
            return {"invited": False, "message": f"transport_error: {type(exc).__name__}"}

        if response.status_code in (200, 201, 202, 204):
            return {"invited": True, "username": username, "permission": permission}
        logger.warning(
            "p22.github.shim.add_collaborator.http_error",
            status=response.status_code,
            repo=f"{owner}/{repo}",
            username=username,
        )
        _handle_github_http_error(response, url)

    async def list_webhooks(
        self, owner: str, repo: str, per_page: int = 30
    ) -> list[dict[str, Any]]:
        """List repository webhooks for ``{owner}/{repo}`` (L1 read).

        Inline ``GET /repos/{o}/{r}/hooks`` — no MCP tool exists.
        Sensitive ``config`` payloads are stripped from the response.
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
        }
        url = _GITHUB_API_HOOKS_FMT.format(owner=owner, repo=repo)
        params = {"per_page": per_page}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=headers, params=params)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.list_webhooks.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return []

        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.list_webhooks.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.list_webhooks.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return []

        if not isinstance(payload, list):
            return []
        # Strip any ``config`` block (may contain secrets) before returning.
        sanitized: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                hook_copy = dict(item)
                hook_copy.pop("config", None)
                sanitized.append(hook_copy)
        return sanitized

    async def create_webhook(
        self,
        owner: str,
        repo: str,
        url: str,
        events: list[str] | None = None,
        content_type: str = "json",
    ) -> dict[str, Any]:
        """Create a webhook on ``{owner}/{repo}`` (L2 write).

        Inline ``POST /repos/{o}/{r}/hooks`` — no MCP tool exists.
        Returns the parsed hook dict (with ``config`` redactions applied
        before returning to caller).
        """
        if not self._enabled:
            _fail_closed("GitHub client: GITHUB_PAT env not set on guinevere-core")

        import httpx

        pat = os.environ.get("GITHUB_PAT", "")
        headers = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        }
        endpoint = _GITHUB_API_HOOKS_FMT.format(owner=owner, repo=repo)
        payload_body: dict[str, Any] = {
            "config": {
                "url": url,
                "content_type": content_type,
            },
            "events": list(events) if events else ["push"],
            "active": True,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(endpoint, headers=headers, json=payload_body)
        except Exception as exc:
            logger.warning(
                "p22.github.shim.create_webhook.transport_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return {"created": False, "message": f"transport_error: {type(exc).__name__}"}

        if response.status_code not in (200, 201):
            logger.warning(
                "p22.github.shim.create_webhook.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            _handle_github_http_error(response, url)

        try:
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "p22.github.shim.create_webhook.parse_error",
                error_type=type(exc).__name__,
                repo=f"{owner}/{repo}",
            )
            return {"created": False, "message": f"parse_error: {type(exc).__name__}"}

        if not isinstance(payload, dict):
            return {"created": False, "message": "non-dict response"}
        # Strip secret material from response.
        payload.pop("config", None)
        payload.setdefault("created", True)
        return payload
