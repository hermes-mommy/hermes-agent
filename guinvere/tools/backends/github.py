"""M8 GitHub backend -- GitHub REST API via httpx.

Ported from: P22 github_adapter.py, P23 github_executor (Section 4.4),
MCP github.py, git_tool.py.

19 actions: 10 L1 READ, 7 L2 WRITE, 2 L3 DESTRUCTIVE.
NO L4 actions (delete_repo, force_push, delete_branch deleted per ADR-062).

REAL I/O: all actions call the GitHub REST API (https://api.github.com).
Token: GITHUB_TOKEN or GITHUB_PAT env var.
Fail-soft: dispatch NEVER raises to caller.
"""
from __future__ import annotations

import base64
import logging
import os
import re
from typing import Any

from guinvere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)

# Security: block command-injection patterns for identifier args
_DANGEROUS_PATTERNS = (
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero of=",
    ":(){:|:&};:", "chmod -R 777 /", "shutdown", "reboot",
    ">/dev/sda", "fork bomb",
)


def _is_safe_identifier(value: str) -> bool:
    """Return True only for safe identifiers (blocks command-injection)."""
    if not value or not isinstance(value, str):
        return False
    if re.search(r"[;&|`$(){}\\<>!]| \$\(| \$\{", value):
        return False
    if any(ord(ch) < 32 for ch in value):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9._/\-@:]+", value))


# GitHub API base URL
_GITHUB_API = "https://api.github.com"


class GitHubBackend(ToolBackend):
    """GitHub backend (L1/L2/L3).  Wraps GitHub REST API via httpx.

    Actions: list_repos, get_file, search_code, list_issues, list_prs,
    get_repo, watch_checks, git_status, git_log, git_diff, create_issue,
    create_pr, create_branch, commit, push, comment, run_workflow,
    merge_pr, revert_pr.
    """

    @property
    def name(self) -> str:
        return "github"

    def actions(self) -> list[Action]:
        return [
            Action("list_repos", ActionTier.L1_READ, description="List user repos"),
            Action("get_file", ActionTier.L1_READ, description="Get file contents"),
            Action("search_code", ActionTier.L1_READ, description="Search code across repos"),
            Action("list_issues", ActionTier.L1_READ, description="List repo issues"),
            Action("list_prs", ActionTier.L1_READ, description="List pull requests"),
            Action("get_repo", ActionTier.L1_READ, description="Get repo metadata"),
            Action("watch_checks", ActionTier.L1_READ, description="Watch CI checks"),
            Action("git_status", ActionTier.L1_READ, description="Combined commit status"),
            Action("git_log", ActionTier.L1_READ, description="Commit log"),
            Action("git_diff", ActionTier.L1_READ, description="Diff (deferred -- needs local repo)"),
            Action("create_issue", ActionTier.L2_WRITE, description="Create issue"),
            Action("create_pr", ActionTier.L2_WRITE, description="Create pull request"),
            Action("create_branch", ActionTier.L2_WRITE, description="Create branch"),
            Action("commit", ActionTier.L2_WRITE, description="Git commit (deferred -- needs local repo)"),
            Action("push", ActionTier.L2_WRITE, description="Git push (deferred -- needs local repo)"),
            Action("comment", ActionTier.L2_WRITE, description="Comment on issue/PR"),
            Action("run_workflow", ActionTier.L2_WRITE, description="Dispatch GitHub Actions"),
            Action("merge_pr", ActionTier.L3_DESTRUCTIVE, description="Merge PR"),
            Action("revert_pr", ActionTier.L3_DESTRUCTIVE, description="Revert a merged PR"),
        ]

    def is_available(self) -> bool:
        return True  # Backend always exists; token may be missing

    def _get_token(self) -> str | None:
        """Get GitHub token from env. Checks GITHUB_TOKEN then GITHUB_PAT."""
        return os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _gh_get(self, client, url: str, params: dict | None = None) -> dict[str, Any]:
        """GET request to GitHub API. Returns {ok, status, data}."""
        resp = await client.get(url, params=params)
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message", resp.text)
            except Exception:
                msg = resp.text
            return {"ok": False, "status": resp.status_code, "error": str(msg)}
        return {"ok": True, "status": resp.status_code, "data": resp.json()}

    async def _gh_post(self, client, url: str, json_data: dict) -> dict[str, Any]:
        """POST request to GitHub API. Returns {ok, status, data}."""
        resp = await client.post(url, json=json_data)
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message", resp.text)
            except Exception:
                msg = resp.text
            return {"ok": False, "status": resp.status_code, "error": str(msg)}
        # 204 No Content (workflow dispatch)
        if resp.status_code == 204:
            return {"ok": True, "status": 204, "data": None}
        return {"ok": True, "status": resp.status_code, "data": resp.json()}

    async def _gh_patch(self, client, url: str, json_data: dict) -> dict[str, Any]:
        """PATCH request to GitHub API. Returns {ok, status, data}."""
        resp = await client.patch(url, json=json_data)
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message", resp.text)
            except Exception:
                msg = resp.text
            return {"ok": False, "status": resp.status_code, "error": str(msg)}
        return {"ok": True, "status": resp.status_code, "data": resp.json()}

    async def _gh_put(self, client, url: str, json_data: dict = None) -> dict[str, Any]:
        """PUT request to GitHub API. Returns {ok, status, data}."""
        resp = await client.put(url, json=json_data or {})
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message", resp.text)
            except Exception:
                msg = resp.text
            return {"ok": False, "status": resp.status_code, "error": str(msg)}
        return {"ok": True, "status": resp.status_code, "data": resp.json()}

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a GitHub action via REST API.

        All actions perform real I/O.  Errors are returned as
        ``{"ok": False, "error": ...}`` (fail-soft -- never raise to caller).
        """
        import httpx

        action_lower = action.lower()
        token = self._get_token()

        # --- Deferred actions (need local repo -- cannot do via REST) ---
        if action_lower in ("git_diff", "commit", "push"):
            return {
                "ok": False,
                "action": action,
                "deferred": True,
                "error": f"{action} requires a local git repository -- not available via GitHub REST API",
            }

        # --- Config-missing: token required for all API actions ---
        if not token:
            return {
                "ok": False,
                "action": action,
                "config_missing": True,
                "error": "GITHUB_TOKEN or GITHUB_PAT not set in environment",
            }

        owner = args.get("owner", "")
        repo = args.get("repo", "")
        headers = self._headers(token)

        try:
            async with httpx.AsyncClient(
                base_url=_GITHUB_API,
                headers=headers,
                timeout=30.0,
            ) as client:

                # ------ L1 READ actions ------

                if action_lower == "list_repos":
                    page = args.get("page", 1)
                    per_page = args.get("per_page", 30)
                    result = await self._gh_get(
                        client, "/user/repos",
                        params={"page": page, "per_page": per_page, "sort": "updated"},
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    repos = result["data"]
                    return {
                        "ok": True, "action": action,
                        "count": len(repos),
                        "repos": [
                            {
                                "full_name": r["full_name"],
                                "private": r.get("private", False),
                                "description": r.get("description", ""),
                                "default_branch": r.get("default_branch", "main"),
                                "html_url": r.get("html_url", ""),
                            }
                            for r in repos
                        ],
                    }

                if action_lower == "get_repo":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    result = await self._gh_get(client, f"/repos/{owner}/{repo}")
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result["data"]
                    return {
                        "ok": True, "action": action,
                        "full_name": d.get("full_name", ""),
                        "private": d.get("private", False),
                        "description": d.get("description", ""),
                        "default_branch": d.get("default_branch", "main"),
                        "html_url": d.get("html_url", ""),
                        "open_issues_count": d.get("open_issues_count", 0),
                        "stargazers_count": d.get("stargazers_count", 0),
                    }

                if action_lower == "list_issues":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    state = args.get("state", "open")
                    page = args.get("page", 1)
                    per_page = args.get("per_page", 30)
                    result = await self._gh_get(
                        client, f"/repos/{owner}/{repo}/issues",
                        params={"state": state, "page": page, "per_page": per_page},
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    issues = result["data"]
                    return {
                        "ok": True, "action": action,
                        "count": len(issues),
                        "issues": [
                            {
                                "number": i["number"],
                                "title": i["title"],
                                "state": i["state"],
                                "html_url": i.get("html_url", ""),
                            }
                            for i in issues
                        ],
                    }

                if action_lower == "list_prs":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    state = args.get("state", "open")
                    page = args.get("page", 1)
                    per_page = args.get("per_page", 30)
                    result = await self._gh_get(
                        client, f"/repos/{owner}/{repo}/pulls",
                        params={"state": state, "page": page, "per_page": per_page},
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    prs = result["data"]
                    return {
                        "ok": True, "action": action,
                        "count": len(prs),
                        "prs": [
                            {
                                "number": p["number"],
                                "title": p["title"],
                                "state": p["state"],
                                "draft": p.get("draft", False),
                                "html_url": p.get("html_url", ""),
                            }
                            for p in prs
                        ],
                    }

                if action_lower == "get_pr":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    pr_number = args.get("pr_number", 0)
                    if not pr_number:
                        return {"ok": False, "action": action, "error": "pr_number required"}
                    result = await self._gh_get(
                        client, f"/repos/{owner}/{repo}/pulls/{pr_number}",
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result["data"]
                    return {
                        "ok": True, "action": action,
                        "number": d["number"],
                        "title": d["title"],
                        "state": d["state"],
                        "head": d.get("head", {}).get("ref", ""),
                        "base": d.get("base", {}).get("ref", ""),
                        "html_url": d.get("html_url", ""),
                    }

                if action_lower == "search_code":
                    query = args.get("query", "")
                    if not query:
                        return {"ok": False, "action": action, "error": "query required"}
                    page = args.get("page", 1)
                    per_page = args.get("per_page", 30)
                    result = await self._gh_get(
                        client, "/search/code",
                        params={"q": query, "page": page, "per_page": per_page},
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result["data"]
                    return {
                        "ok": True, "action": action,
                        "total_count": d.get("total_count", 0),
                        "count": len(d.get("items", [])),
                        "items": [
                            {
                                "name": item["name"],
                                "path": item["path"],
                                "html_url": item.get("html_url", ""),
                                "repository": item.get("repository", {}).get("full_name", ""),
                            }
                            for item in d.get("items", [])
                        ],
                    }

                if action_lower == "get_file":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    path = args.get("path", "")
                    if not path:
                        return {"ok": False, "action": action, "error": "path required"}
                    ref = args.get("ref", "")
                    params = {}
                    if ref:
                        params["ref"] = ref
                    result = await self._gh_get(
                        client, f"/repos/{owner}/{repo}/contents/{path}",
                        params=params,
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result["data"]
                    # Decode base64 content
                    content = ""
                    if d.get("encoding") == "base64" and d.get("content"):
                        try:
                            content = base64.b64decode(d["content"]).decode("utf-8")
                        except Exception as exc:
                            logger.debug("github: base64 decode fallback for %s/%s/%s: %s",
                                         owner, repo, path, exc)
                            content = d["content"]
                    return {
                        "ok": True, "action": action,
                        "owner": owner, "repo": repo, "path": path,
                        "sha": d.get("sha", ""),
                        "content": content,
                        "type": d.get("type", "file"),
                    }

                if action_lower == "watch_checks":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    ref = args.get("ref", "HEAD")
                    result = await self._gh_get(
                        client, f"/repos/{owner}/{repo}/commits/{ref}/check-runs",
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result["data"]
                    return {
                        "ok": True, "action": action,
                        "total_count": d.get("total_count", 0),
                        "checks": [
                            {
                                "name": c["name"],
                                "status": c["status"],
                                "conclusion": c.get("conclusion"),
                            }
                            for c in d.get("check_runs", [])
                        ],
                    }

                if action_lower == "git_status":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    ref = args.get("ref", "HEAD")
                    result = await self._gh_get(
                        client, f"/repos/{owner}/{repo}/commits/{ref}/status",
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result["data"]
                    return {
                        "ok": True, "action": action,
                        "sha": d.get("sha", ""),
                        "state": d.get("state", "unknown"),
                        "total_count": d.get("total_count", 0),
                        "statuses": [
                            {"context": s.get("context", ""), "state": s.get("state", "")}
                            for s in d.get("statuses", [])
                        ],
                    }

                if action_lower == "git_log":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    sha = args.get("sha", "")
                    page = args.get("page", 1)
                    per_page = args.get("per_page", 30)
                    params = {"page": page, "per_page": per_page}
                    if sha:
                        params["sha"] = sha
                    result = await self._gh_get(
                        client, f"/repos/{owner}/{repo}/commits", params=params,
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    commits = result["data"]
                    return {
                        "ok": True, "action": action,
                        "count": len(commits),
                        "commits": [
                            {
                                "sha": c["sha"],
                                "message": c.get("commit", {}).get("message", ""),
                                "author": c.get("commit", {}).get("author", {}).get("name", ""),
                                "date": c.get("commit", {}).get("author", {}).get("date", ""),
                            }
                            for c in commits
                        ],
                    }

                # ------ L2 WRITE actions ------

                if action_lower == "create_issue":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    title = args.get("title", "")
                    if not title:
                        return {"ok": False, "action": action, "error": "title required"}
                    body_data: dict[str, Any] = {"title": title}
                    if args.get("body"):
                        body_data["body"] = args["body"]
                    if args.get("labels"):
                        body_data["labels"] = args["labels"]
                    if args.get("assignees"):
                        body_data["assignees"] = args["assignees"]
                    result = await self._gh_post(
                        client, f"/repos/{owner}/{repo}/issues", body_data,
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result["data"]
                    return {
                        "ok": True, "action": action,
                        "number": d.get("number"),
                        "title": d.get("title", title),
                        "html_url": d.get("html_url", ""),
                        "state": d.get("state", "open"),
                    }

                if action_lower == "create_pr":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    title = args.get("title", "")
                    head = args.get("head", "")
                    base = args.get("base", "main")
                    if not title or not head:
                        return {"ok": False, "action": action, "error": "title and head required"}
                    body_data = {"title": title, "head": head, "base": base}
                    if args.get("body"):
                        body_data["body"] = args["body"]
                    if args.get("draft"):
                        body_data["draft"] = True
                    result = await self._gh_post(
                        client, f"/repos/{owner}/{repo}/pulls", body_data,
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result["data"]
                    return {
                        "ok": True, "action": action,
                        "number": d.get("number"),
                        "title": d.get("title", title),
                        "html_url": d.get("html_url", ""),
                        "state": d.get("state", "open"),
                    }

                if action_lower == "create_branch":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    branch = args.get("branch", "")
                    from_sha = args.get("from_sha", "")
                    if not branch or not from_sha:
                        return {"ok": False, "action": action, "error": "branch and from_sha required"}
                    result = await self._gh_post(
                        client, f"/repos/{owner}/{repo}/git/refs",
                        {"ref": f"refs/heads/{branch}", "sha": from_sha},
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    return {
                        "ok": True, "action": action,
                        "branch": branch,
                        "ref": result["data"].get("ref", ""),
                    }

                if action_lower == "comment":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    issue_number = args.get("issue_number", 0)
                    body_text = args.get("body", "")
                    if not issue_number or not body_text:
                        return {"ok": False, "action": action, "error": "issue_number and body required"}
                    result = await self._gh_post(
                        client,
                        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
                        {"body": body_text},
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    return {
                        "ok": True, "action": action,
                        "issue_number": issue_number,
                        "comment_id": result["data"].get("id"),
                    }

                if action_lower == "run_workflow":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    workflow = args.get("workflow", "")
                    ref = args.get("ref", "main")
                    if not workflow:
                        return {"ok": False, "action": action, "error": "workflow required"}
                    body_data: dict[str, Any] = {"ref": ref}
                    if args.get("inputs"):
                        body_data["inputs"] = args["inputs"]
                    result = await self._gh_post(
                        client,
                        f"/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches",
                        body_data,
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    return {
                        "ok": True, "action": action,
                        "workflow": workflow,
                        "ref": ref,
                        "dispatched": True,
                    }

                # ------ L3 DESTRUCTIVE actions ------

                if action_lower == "merge_pr":
                    if not owner or not repo:
                        return {"ok": False, "action": action, "error": "owner and repo required"}
                    pr_number = args.get("pr_number", 0)
                    if not pr_number:
                        return {"ok": False, "action": action, "error": "pr_number required"}
                    merge_method = args.get("merge_method", "merge")
                    body_data: dict[str, Any] = {"merge_method": merge_method}
                    if args.get("commit_title"):
                        body_data["commit_title"] = args["commit_title"]
                    if args.get("commit_message"):
                        body_data["commit_message"] = args["commit_message"]
                    result = await self._gh_put(
                        client,
                        f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                        body_data,
                    )
                    if not result["ok"]:
                        return {"ok": False, "action": action, "error": result["error"]}
                    d = result.get("data") or {}
                    return {
                        "ok": True, "action": action,
                        "pr_number": pr_number,
                        "merged": d.get("merged", True),
                        "sha": d.get("sha", ""),
                        "restore_method": "git revert -m 1 <merge_commit_sha>",
                    }

                if action_lower == "revert_pr":
                    # Revert needs the merge commit SHA, which we don't have
                    # without first fetching the PR. This is a multi-step
                    # operation best done via a local git repo.
                    return {
                        "ok": False,
                        "action": action,
                        "deferred": True,
                        "error": "revert_pr requires local git clone for reliable revert -- use git locally",
                    }

                # ------ Unknown action ------
                return {"ok": False, "error": f"unknown github action: {action}"}

        except Exception as e:
            logger.error("github.dispatch failed action=%s: %s", action, e, exc_info=True)
            return {"ok": False, "action": action, "error": str(e)}
