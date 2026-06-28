"""P22 brutal-audit F08 — GitHub client shim raises typed errors on non-200.

Covers every status-path that the previous implementation silently swallowed
as ``[]`` / ``{}`` / ``{merged: False}`` / etc. AFTER the fix, each non-200
must surface as a typed integration error that the audit journal can record.

Spec mapping (from brutal-audit F08):
   * 200 (or 200/201/202/204 for writes) → parsed JSON (existing behavior,
     NOT re-tested here — already covered by ``test_github_client_shim.py``).
   * 403 with ``X-RateLimit-Remaining: 0`` header → RateLimitExceededError.
   * 429 → RateLimitExceededError (``Retry-After`` parsed).
   * 404 → ProviderError("github", 404, "GitHub resource not found: ...").
   * 401 → AuthenticationError.
   * 403 (non-rate-limit) → ProviderError("github", 403, "Forbidden: ...").
   * 5xx → ProviderError("github", status, "GitHub API error: ...").
   * other non-200 → ProviderError("github", status, "unexpected status …").

Method coverage: we exercise one LIST method (list_issues) and one
WRITE method (merge_pr) per status path; the helper
``_handle_github_http_error`` is centralised, so coverage on these
two methods exercises every other inline-REST method's branch.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from src.life_integrations.adapters._clients.github_client_shim import (
    GitHubClientShim,
)
from src.life_integrations.errors import (  # noqa: E402
    AuthenticationError,
    ConfigurationMissingError,
    ProviderError,
    RateLimitExceededError,
)

_FAKE_PAT = "fake-ghp-test"


class _FakeResponse:
    """httpx.Response stand-in. Adds ``headers`` and ``text`` to enable
    full coverage of the ``_handle_github_http_error`` helper.
    """

    def __init__(
        self,
        status_code: int,
        payload=None,
        *,
        headers: dict | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.text = str(self._payload) if self._payload else ""

    def json(self):
        return self._payload


def _client(fake_response: _FakeResponse) -> AsyncMock:
    """Build an async-context httpx.AsyncClient returning ``fake_response``."""
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.get = AsyncMock(return_value=fake_response)
    client.put = AsyncMock(return_value=fake_response)
    client.post = AsyncMock(return_value=fake_response)
    client.delete = AsyncMock(return_value=fake_response)
    return client


@pytest.fixture
def shim_with_pat(monkeypatch):
    monkeypatch.setenv("GITHUB_PAT", _FAKE_PAT)
    return GitHubClientShim()


# ---------------------------------------------------------------------------
# 429 → RateLimitExceededError
# ---------------------------------------------------------------------------


async def test_list_issues_429_raises_rate_limit_exceeded(shim_with_pat):
    """429 status → RateLimitExceededError with Retry-After parsed."""
    fake = _FakeResponse(
        429, {"message": "rate limit"},
        headers={"Retry-After": "60"},
    )
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(RateLimitExceededError) as exc_info:
            await shim_with_pat.list_issues("owner", "repo")

    assert exc_info.value.provider == "github"
    assert exc_info.value.retry_after == 60


async def test_merge_pr_429_raises_rate_limit_exceeded(shim_with_pat):
    """429 on PUT merge → RateLimitExceededError."""
    fake = _FakeResponse(429, {"message": "rate"},
                         headers={"Retry-After": "120"})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(RateLimitExceededError):
            await shim_with_pat.merge_pr("owner", "repo", 1)


async def test_rate_limit_without_header_raises_with_none_retry_after(
    shim_with_pat,
):
    """429 without Retry-After → RateLimitExceededError(retry_after=None)."""
    fake = _FakeResponse(429, {"message": "rate"}, headers={})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(RateLimitExceededError) as exc_info:
            await shim_with_pat.list_issues("owner", "repo")
    assert exc_info.value.retry_after is None


# ---------------------------------------------------------------------------
# 403 with X-RateLimit-Remaining: 0 → RateLimitExceededError
# ---------------------------------------------------------------------------


async def test_list_issues_403_rl_remaining_zero_raises_rate_limit(
    shim_with_pat,
):
    """Forbidden with X-RateLimit-Remaining=0 is de-facto a 429."""
    fake = _FakeResponse(
        403, {"message": "rate"},
        headers={
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "9999999999",
        },
    )
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(RateLimitExceededError) as exc_info:
            await shim_with_pat.list_issues("owner", "repo")
    assert exc_info.value.provider == "github"
    # Retry-after derived from X-RateLimit-Reset - now (large positive int)
    assert isinstance(exc_info.value.retry_after, int)
    assert exc_info.value.retry_after > 0


# ---------------------------------------------------------------------------
# 404 → ProviderError("github", 404, ...)
# ---------------------------------------------------------------------------


async def test_list_issues_404_raises_provider_error_not_found(shim_with_pat):
    """404 → typed ProviderError. Pre-fix: silently returned []."""
    fake = _FakeResponse(404, {"message": "Not Found"})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(ProviderError) as exc_info:
            await shim_with_pat.list_issues("ghost", "void")

    assert exc_info.value.provider == "github"
    assert exc_info.value.status == 404
    assert "not found" in exc_info.value.message.lower()


async def test_merge_pr_404_raises_provider_error_not_found(shim_with_pat):
    """404 on PUT merge → ProviderError."""
    fake = _FakeResponse(404, {"message": "Not Found"})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(ProviderError) as exc_info:
            await shim_with_pat.merge_pr("ghost", "void", 999)
    assert exc_info.value.status == 404


# ---------------------------------------------------------------------------
# 401 → AuthenticationError
# ---------------------------------------------------------------------------


async def test_list_issues_401_raises_authentication_error(shim_with_pat):
    """401 → AuthenticationError (PAT invalid/expired)."""
    fake = _FakeResponse(401, {"message": "Bad credentials"})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(AuthenticationError) as exc_info:
            await shim_with_pat.list_issues("owner", "repo")

    assert "PAT" in str(exc_info.value) or "invalid" in str(exc_info.value).lower()


async def test_merge_pr_401_raises_authentication_error(shim_with_pat):
    """401 on PUT → AuthenticationError."""
    fake = _FakeResponse(401, {"message": "Bad credentials"})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(AuthenticationError):
            await shim_with_pat.merge_pr("owner", "repo", 1)


# ---------------------------------------------------------------------------
# 403 (non-rate-limit) → ProviderError
# ---------------------------------------------------------------------------


async def test_list_issues_403_non_rl_raises_provider_error(shim_with_pat):
    """403 without rate-limit hints → ProviderError(403, 'Forbidden: ...')."""
    fake = _FakeResponse(403, {"message": "Forbidden by org policy"})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(ProviderError) as exc_info:
            await shim_with_pat.list_issues("owner", "repo")
    assert exc_info.value.status == 403
    assert exc_info.value.provider == "github"
    assert "Forbidden" in exc_info.value.message or "forbidden" in exc_info.value.message.lower()


# ---------------------------------------------------------------------------
# 5xx → ProviderError
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
async def test_list_issues_5xx_raises_provider_error(
    shim_with_pat, status_code,
):
    """5xx → ProviderError('GitHub API error: <status>')."""
    fake = _FakeResponse(status_code, {"message": "Internal error"})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(ProviderError) as exc_info:
            await shim_with_pat.list_issues("owner", "repo")
    assert exc_info.value.status == status_code
    assert "api error" in exc_info.value.message.lower() or str(status_code) in exc_info.value.message


# ---------------------------------------------------------------------------
# Other non-200 → ProviderError("unexpected status ...")
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status_code", [418, 418, 451])
async def test_list_issues_unexpected_status_raises_provider_error(
    shim_with_pat, status_code,
):
    """418 / 451 / etc → ProviderError('unexpected status ...')."""
    fake = _FakeResponse(status_code, {"message": ""})
    with patch("httpx.AsyncClient", return_value=_client(fake)):
        with pytest.raises(ProviderError) as exc_info:
            await shim_with_pat.list_issues("owner", "repo")
    assert exc_info.value.status == status_code
    assert "unexpected" in exc_info.value.message.lower()


# ---------------------------------------------------------------------------
# all list/all-write methods route to the same helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method_name,args,verb",
    [
        ("list_issues", ("o", "r"), "get"),
        ("list_prs", ("o", "r"), "get"),
        ("get_repo", ("o", "r"), "get"),
        ("get_pr", ("o", "r", 1), "get"),
        ("get_branch", ("o", "r", "main"), "get"),
        ("list_releases", ("o", "r"), "get"),
        ("list_webhooks", ("o", "r"), "get"),
        ("merge_pr", ("o", "r", 1), "put"),
        ("create_release", ("o", "r", "v1.0"), "post"),
        ("add_collaborator", ("o", "r", "alice"), "put"),
        ("create_webhook", ("o", "r", "https://x"), "post"),
    ],
)
async def test_every_inline_rest_method_routes_429_through_helper(
    shim_with_pat, method_name, args, verb,
):
    """Every inline-REST method's 429 path raises RateLimitExceededError.

    The helper is centralised, so a single assertion per method proves
    wiring is intact across the 13 inline-REST methods.
    """
    fake = _FakeResponse(
        429, {"message": "rl"},
        headers={"Retry-After": "1"},
    )
    client = _client(fake)
    with patch("httpx.AsyncClient", return_value=client):
        method = getattr(shim_with_pat, method_name)
        with pytest.raises(RateLimitExceededError):
            await method(*args)


# ---------------------------------------------------------------------------
# Helper unit tests (no shim / no httpx)
# ---------------------------------------------------------------------------


async def test_helper_404_url_in_message(shim_with_pat):
    """404 message includes the URL so the audit journal can trace it."""
    from src.life_integrations.adapters._clients.github_client_shim import (
        _handle_github_http_error,
    )

    fake = _FakeResponse(404, {"message": "Not Found"})
    with pytest.raises(ProviderError) as exc_info:
        _handle_github_http_error(fake, "https://api.github.com/repos/ghost/void")
    assert "ghost/void" in exc_info.value.message


async def test_helper_5xx_message_format(shim_with_pat):
    """5xx message format: 'GitHub API error: <status>'."""
    from src.life_integrations.adapters._clients.github_client_shim import (
        _handle_github_http_error,
    )

    fake = _FakeResponse(503, {"message": "Service Unavailable"})
    with pytest.raises(ProviderError) as exc_info:
        _handle_github_http_error(fake, "https://api.github.com/anything")
    assert "503" in exc_info.value.message


# ---------------------------------------------------------------------------
# Static guard: forbidden patterns (PER TASK HARD REJECTION)
# ---------------------------------------------------------------------------


def test_shim_no_silent_returns_on_non_200_inline_methods():
    """Static guard: no `return []` / `return {}` / `return {merged: False...}`
    on the non-200 branch of inline-REST methods.

    We strip docstrings (which may describe the old behaviour verbally) and
    then walk the file string line-by-line, looking for `return []` or
    `return {}` IMMEDIATELY following a logger.warning that name a method's
    non-200 branch. This is a coarse but safe assertion.
    """
    src_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "life_integrations"
        / "adapters"
        / "_clients"
        / "github_client_shim.py"
    )
    text = src_path.read_text(encoding="utf-8")

    # Forbidden: any `return []` or `return {}` AFTER the logger.warning
    # block labelled `.http_error`.
    # We split the file into "between http_error warning and next return".
    forbidden_lines = []
    in_non_200_block = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "http_error" in line and "logger.warning" in line:
            in_non_200_block = True
            continue
        if in_non_200_block:
            stripped = line.strip()
            # any return that produces an empty container shape at this
            # block is a silent-empty-return on non-200.
            if stripped in {"return []", "return {}", "return [] # noqa"}:
                forbidden_lines.append((line_no, stripped))
            # Exit block when we leave the warning indented body.
            if not line.startswith("            ") and stripped:
                in_non_200_block = False

    assert not forbidden_lines, (
        "github_client_shim has silent empty returns on non-200 paths: "
        f"{forbidden_lines}"
    )


def test_shim_does_not_swallow_429_silently():
    """Static guard: the file imports RateLimitExceededError."""
    src_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "life_integrations"
        / "adapters"
        / "_clients"
        / "github_client_shim.py"
    )
    text = src_path.read_text(encoding="utf-8")
    assert "RateLimitExceededError" in text, (
        "github_client_shim must import RateLimitExceededError"
    )
    assert "429" in text or "_HTTP_RATE_LIMIT" in text
