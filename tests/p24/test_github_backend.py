"""P6 GitHub backend TDD tests -- mocked httpx, NO live GitHub calls.

Each action gets one dedicated test.  All httpx calls are monkeypatched
via a helper that returns pre-crafted JSON for each endpoint.
"""
from __future__ import annotations

import asyncio
import os
import re
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guinevere.tools.backends.github import GitHubBackend


# ---------------------------------------------------------------------------
# Fake httpx response factory
# ---------------------------------------------------------------------------

class _FakeResponse:
    """Mimics httpx.Response enough for GitHubBackend."""

    def __init__(self, status_code: int, json_data: dict | list | None = None,
                 text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or ""
        self.content = (text or "").encode("utf-8")

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if 400 <= self.status_code < 600:
            import httpx
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=MagicMock(),
                response=self,
            )


# Pre-crafted GitHub API response payloads ------------------------------------

_FAKE_REPOS = [
    {"full_name": "alice/alpha", "private": False, "description": "Alpha repo",
     "default_branch": "main", "html_url": "https://github.com/alice/alpha"},
    {"full_name": "alice/beta", "private": True, "description": "Beta repo",
     "default_branch": "main", "html_url": "https://github.com/alice/beta"},
]

_FAKE_REPO = {
    "full_name": "hermes-mommy/hermes-agent",
    "private": True,
    "description": "Owned fork",
    "default_branch": "main",
    "html_url": "https://github.com/hermes-mommy/hermes-agent",
    "open_issues_count": 3,
    "stargazers_count": 0,
}

_FAKE_ISSUES = [
    {"number": 1, "title": "First bug", "state": "open",
     "html_url": "https://github.com/test/repo/issues/1"},
    {"number": 2, "title": "Second bug", "state": "closed",
     "html_url": "https://github.com/test/repo/issues/2"},
]

_FAKE_PRS = [
    {"number": 10, "title": "feat: add feature", "state": "open",
     "html_url": "https://github.com/test/repo/pull/10", "draft": False},
    {"number": 11, "title": "fix: bug", "state": "closed", "merged": True,
     "html_url": "https://github.com/test/repo/pull/11", "draft": False},
]

_FAKE_PR = {
    "number": 10, "title": "feat: add feature", "state": "open",
    "head": {"ref": "feat/feature", "sha": "abc123"},
    "base": {"ref": "main"},
    "html_url": "https://github.com/test/repo/pull/10",
}

_FAKE_SEARCH = {
    "total_count": 1,
    "items": [
        {"name": "found.py", "path": "src/found.py",
         "html_url": "https://github.com/test/repo/blob/main/src/found.py",
         "repository": {"full_name": "test/repo"}},
    ],
}

_FAKE_FILE = {
    "name": "README.md",
    "path": "README.md",
    "sha": "deadbeef",
    "content": "SGVsbG8=",  # base64("Hello")
    "encoding": "base64",
    "type": "file",
}

_FAKE_ISSUE = {
    "number": 42,
    "title": "New issue",
    "state": "open",
    "html_url": "https://github.com/test/repo/issues/42",
    "body": "Issue body text",
}

_FAKE_CHECKS = {
    "total_count": 2,
    "check_runs": [
        {"name": "build", "status": "completed", "conclusion": "success"},
        {"name": "test", "status": "in_progress", "conclusion": None},
    ],
}

_FAKE_BRANCHES = [
    {"name": "main", "protected": True},
    {"name": "dev", "protected": False},
]

_FAKE_WORKFLOW_RUN = {
    "id": 9999,
    "status": "queued",
    "html_url": "https://github.com/test/repo/actions/runs/9999",
}

_FAKE_COMMITS = [
    {"sha": "aabbccddee", "commit": {"message": "Initial commit",
                                      "author": {"name": "Test", "date": "2026-01-01T00:00:00Z"}}},
]

_FAKE_STATUS = {
    "sha": "abc123",
    "state": "success",
    "total_count": 1,
    "statuses": [{"context": "ci/build", "state": "success"}],
}


# ---------------------------------------------------------------------------
# Route helper -- maps (method, url_contains) -> fake response
# ---------------------------------------------------------------------------

def _make_fake_get(url: str, **kwargs):
    """Return a fake httpx response based on the URL."""
    # Normalize: strip base_url prefix to get path-only for matching
    path = url.replace("https://api.github.com", "")

    if path.startswith("/user/repos"):
        return _FakeResponse(200, _FAKE_REPOS)
    if path == "/repos/test/repo":
        return _FakeResponse(200, _FAKE_REPO)
    # get_pr must match BEFORE list_prs (more specific path first)
    if re.match(r"/repos/test/repo/pulls/\d+$", path):
        return _FakeResponse(200, _FAKE_PR)
    if path == "/repos/test/repo/pulls":
        return _FakeResponse(200, _FAKE_PRS)
    if "/repos/test/repo/issues" in path and "/pulls" not in path:
        return _FakeResponse(200, _FAKE_ISSUES)
    if path.startswith("/search/code"):
        return _FakeResponse(200, _FAKE_SEARCH)
    if path == "/repos/test/repo/contents/README.md":
        return _FakeResponse(200, _FAKE_FILE)
    if "/repos/test/repo/issues/42" in path:
        return _FakeResponse(200, _FAKE_ISSUE)
    if "/commits/abc123/check-runs" in path:
        return _FakeResponse(200, _FAKE_CHECKS)
    if path == "/repos/test/repo/branches":
        return _FakeResponse(200, _FAKE_BRANCHES)
    # git_status: /commits/{ref}/status (check BEFORE plain /commits)
    if re.match(r"/repos/test/repo/commits/[^/]+/status$", path):
        return _FakeResponse(200, _FAKE_STATUS)
    if path.startswith("/repos/test/repo/commits"):
        return _FakeResponse(200, _FAKE_COMMITS)
    # Fallback 404
    return _FakeResponse(404, {"message": "Not Found"})


def _make_fake_post(url: str, **kwargs):
    """Return a fake httpx response for POST requests."""
    json_data = kwargs.get("json", {})
    if "/issues" in url and "/comments" not in url:
        resp = {**_FAKE_ISSUE, "title": json_data.get("title", "")}
        return _FakeResponse(201, resp)
    if "/pulls" in url and "/reviews" not in url:
        resp = {**_FAKE_PR, "title": json_data.get("title", "")}
        return _FakeResponse(201, resp)
    if "/issues/" in url and "/comments" in url:
        return _FakeResponse(201, {"id": 100, "body": json_data.get("body", "")})
    if "/git/refs" in url:
        return _FakeResponse(201, {"ref": "refs/heads/new-branch"})
    if "/pulls/" in url and "/merge" in url:
        return _FakeResponse(200, {"sha": "merged-sha", "merged": True})
    if "/actions/workflows" in url and "/dispatches" in url:
        return _FakeResponse(204, None)
    if "/git/commits" in url:
        return _FakeResponse(201, {"sha": "new-commit-sha"})
    # Fallback
    return _FakeResponse(201, json_data)


def _make_fake_patch(url: str, **kwargs):
    """Return a fake httpx response for PATCH requests."""
    return _FakeResponse(200, {**_FAKE_REPO})


def _make_fake_put(url: str, **kwargs):
    """Return a fake httpx response for PUT requests."""
    if "/merge" in url:
        return _FakeResponse(200, {"sha": "merged-sha", "merged": True})
    return _FakeResponse(200, {})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def backend():
    return GitHubBackend()


@pytest.fixture(autouse=True)
def _setup_env_and_httpx(monkeypatch):
    """Set a dummy GITHUB_PAT and replace httpx.AsyncClient with a fake."""
    import httpx

    # Ensure a token is available for all tests (except config_missing test)
    monkeypatch.setenv("GITHUB_PAT", "ghp_fake_test_token_not_real")

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    fake_client.get = AsyncMock(side_effect=_make_fake_get)
    fake_client.post = AsyncMock(side_effect=_make_fake_post)
    fake_client.patch = AsyncMock(side_effect=_make_fake_patch)
    fake_client.put = AsyncMock(side_effect=_make_fake_put)
    fake_client.request = AsyncMock(side_effect=_make_fake_get)

    monkeypatch.setattr(httpx, "AsyncClient", MagicMock(return_value=fake_client))


# ---------------------------------------------------------------------------
# Tests -- one per action
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_repos_returns_repos(backend):
    result = await backend.dispatch("list_repos", {})
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["repos"][0]["full_name"] == "alice/alpha"


@pytest.mark.asyncio
async def test_get_repo_returns_metadata(backend):
    result = await backend.dispatch("get_repo", {"owner": "test", "repo": "repo"})
    assert result["ok"] is True
    assert result["full_name"] == "hermes-mommy/hermes-agent"


@pytest.mark.asyncio
async def test_get_repo_returns_config_missing_without_token(backend):
    """get_repo returns config_missing when GITHUB_TOKEN is not set."""
    with patch.object(backend, "_get_token", return_value=None):
        result = await backend.dispatch("get_repo", {"owner": "test", "repo": "repo"})
    assert result["ok"] is False
    assert result.get("config_missing") is True


@pytest.mark.asyncio
async def test_list_issues_returns_issues(backend):
    result = await backend.dispatch("list_issues", {"owner": "test", "repo": "repo"})
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["issues"][0]["number"] == 1


@pytest.mark.asyncio
async def test_list_prs_returns_prs(backend):
    result = await backend.dispatch("list_prs", {"owner": "test", "repo": "repo"})
    assert result["ok"] is True
    assert result["count"] == 2


@pytest.mark.asyncio
async def test_get_pr_returns_pr(backend):
    result = await backend.dispatch("get_pr",
                                    {"owner": "test", "repo": "repo", "pr_number": 10})
    assert result["ok"] is True
    assert result["number"] == 10


@pytest.mark.asyncio
async def test_search_code_returns_results(backend):
    result = await backend.dispatch("search_code", {"query": "tool_backend"})
    assert result["ok"] is True
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_get_file_returns_decoded_content(backend):
    result = await backend.dispatch("get_file",
                                    {"owner": "test", "repo": "repo", "path": "README.md"})
    assert result["ok"] is True
    # base64("Hello") decoded
    assert result["content"] == "Hello"


@pytest.mark.asyncio
async def test_create_issue_returns_created(backend):
    result = await backend.dispatch("create_issue",
                                    {"owner": "test", "repo": "repo",
                                     "title": "New issue", "body": "Issue body text"})
    assert result["ok"] is True
    assert result["number"] == 42


@pytest.mark.asyncio
async def test_create_pr_returns_created(backend):
    result = await backend.dispatch("create_pr",
                                    {"owner": "test", "repo": "repo",
                                     "title": "feat: add feature",
                                     "head": "feat/feature", "base": "main"})
    assert result["ok"] is True
    assert result["number"] == 10


@pytest.mark.asyncio
async def test_watch_checks_returns_checks(backend):
    result = await backend.dispatch("watch_checks",
                                    {"owner": "test", "repo": "repo",
                                     "ref": "abc123"})
    assert result["ok"] is True
    assert result["total_count"] == 2


@pytest.mark.asyncio
async def test_comment_posts_comment(backend):
    result = await backend.dispatch("comment",
                                    {"owner": "test", "repo": "repo",
                                     "issue_number": 42, "body": "LGTM"})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_run_workflow_dispatches(backend):
    result = await backend.dispatch("run_workflow",
                                    {"owner": "test", "repo": "repo",
                                     "workflow": "ci.yml", "ref": "main"})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_merge_pr_merges(backend):
    result = await backend.dispatch("merge_pr",
                                    {"owner": "test", "repo": "repo",
                                     "pr_number": 10})
    assert result["ok"] is True
    assert result["merged"] is True


@pytest.mark.asyncio
async def test_revert_pr_returns_deferred(backend):
    """revert_pr is deferred (needs local git clone)."""
    result = await backend.dispatch("revert_pr",
                                    {"owner": "test", "repo": "repo",
                                     "pr_number": 10})
    assert result["ok"] is False
    assert result.get("deferred") is True


@pytest.mark.asyncio
async def test_create_branch_creates_ref(backend):
    result = await backend.dispatch("create_branch",
                                    {"owner": "test", "repo": "repo",
                                     "branch": "feat/new", "from_sha": "abc123"})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_git_status_returns_status(backend):
    result = await backend.dispatch("git_status",
                                    {"owner": "test", "repo": "repo",
                                     "ref": "abc123"})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_git_log_returns_commits(backend):
    result = await backend.dispatch("git_log",
                                    {"owner": "test", "repo": "repo"})
    assert result["ok"] is True
    assert result["count"] >= 1


@pytest.mark.asyncio
async def test_git_diff_is_deferred(backend):
    """git_diff needs local repo -- deferred."""
    result = await backend.dispatch("git_diff",
                                    {"owner": "test", "repo": "repo"})
    assert result["ok"] is False
    assert result.get("deferred") is True


@pytest.mark.asyncio
async def test_commit_is_deferred(backend):
    """commit needs local repo -- deferred."""
    result = await backend.dispatch("commit",
                                    {"owner": "test", "repo": "repo",
                                     "message": "test"})
    assert result["ok"] is False
    assert result.get("deferred") is True


@pytest.mark.asyncio
async def test_push_is_deferred(backend):
    """push needs local repo -- deferred."""
    result = await backend.dispatch("push",
                                    {"owner": "test", "repo": "repo"})
    assert result["ok"] is False
    assert result.get("deferred") is True


@pytest.mark.asyncio
async def test_unknown_action_returns_error(backend):
    result = await backend.dispatch("nonexistent_action", {})
    assert result["ok"] is False
    assert "unknown" in result["error"].lower()


@pytest.mark.asyncio
async def test_dispatch_never_raises(backend):
    """dispatch must catch ALL exceptions and return ok=False."""
    import httpx
    # Force an exception inside dispatch by making __aenter__ raise
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(side_effect=RuntimeError("boom"))
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client
        result = await backend.dispatch("list_repos", {})
    assert result["ok"] is False
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_http_error_returns_fail(backend):
    """HTTP 404 from GitHub returns ok=False."""
    import httpx

    def _get_404(url, **kw):
        return _FakeResponse(404, {"message": "Not Found"})

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    fake_client.get = AsyncMock(side_effect=_get_404)

    with patch("httpx.AsyncClient", return_value=fake_client):
        result = await backend.dispatch("get_repo",
                                        {"owner": "nobody", "repo": "nothing"})
    assert result["ok"] is False
    assert "404" in result["error"] or "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_is_available(backend):
    """is_available returns True (backend exists regardless of token)."""
    assert backend.is_available() is True


@pytest.mark.asyncio
async def test_name_is_github(backend):
    assert backend.name == "github"


@pytest.mark.asyncio
async def test_actions_count(backend):
    """Must have 19 actions (same as current stub)."""
    assert len(backend.actions()) == 19
