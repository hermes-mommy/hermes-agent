"""MCP Git Tool — Local git operations via asyncio.create_subprocess_exec.

Provides ``register_tools(mcp: FastMCP) -> None`` to register git operations
on the MCP server, each gated with the appropriate ``AuthLevel``.

Operations and auth levels:
    - Read: ``git_status``, ``git_log``, ``git_diff`` → ``READ_AUTO``
    - Write: ``git_commit`` → ``WRITE_NOTIFY``
    - Destructive: ``git_push --force`` → ``DESTRUCTIVE_APPROVAL``
    - Forbidden: ``git push --force`` to main/master → ``FORBIDDEN``

All subprocess calls use ``asyncio.create_subprocess_exec`` (no shell=True).
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

import structlog

from src.mcp.auth import AuthLevel, ForbiddenOperationError, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Git path — searched once at registration time
# ---------------------------------------------------------------------------

_git_binary: str = os.environ.get("GIT_BINARY", "git")


def _find_git() -> str:
    """Return the git binary path — logs the configured binary for diagnostics."""
    logger.info("git_binary_configured", binary=_git_binary)
    return _git_binary


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class GitToolError(Exception):
    """Base exception for git tool errors."""


class ConfigurationError(GitToolError):
    """Raised when required configuration is missing (e.g. git not found)."""


class GitCommandError(GitToolError):
    """Raised when a git command exits with a non-zero return code."""


# ---------------------------------------------------------------------------
# Forbidden operation detection
# ---------------------------------------------------------------------------

_FORCE_FLAGS = frozenset({"--force", "-f", "--force-with-lease"})
_PROTECTED_BRANCHES = frozenset({"main", "master"})


def _extract_refspec_destination(arg: str) -> str | None:
    """Extract the destination branch from a refspec like ``src:dst``.

    Returns ``None`` if *arg* is not a refspec.  For ``HEAD:refs/heads/main``
    the destination is ``refs/heads/main``; for ``feature:main`` it is
    ``main``.
    """
    if ":" not in arg:
        return None
    _, _, dst = arg.partition(":")
    return dst or None


def _normalise_branch(branch: str) -> str:
    """Strip ``refs/heads/`` prefix and lower-case the branch name."""
    b = branch.lower()
    for prefix in ("refs/heads/", "refs/remotes/origin/"):
        if b.startswith(prefix):
            b = b[len(prefix) :]
            break
    return b


def _is_forbidden(args: list[str], branch: str | None) -> bool:
    """Check whether a git operation is forbidden.

    Returns ``True`` when the command is a force-push (``--force``,
    ``-f``, or ``--force-with-lease``) to ``main`` or ``master``,
    regardless of how the branch is passed (positional arg, ``branch``
    parameter, or refspec destination).

    Branch comparison is case-insensitive and strips common ref
    prefixes so that ``MAIN``, ``refs/heads/main``, and
    ``HEAD:refs/heads/main`` are all detected.
    """
    if len(args) < 3:
        return False

    is_push = args[0] == "push"
    has_force = bool(_FORCE_FLAGS & set(args))

    if not (is_push and has_force):
        return False

    # Collect candidate branch names from positional args and the
    # explicit *branch* parameter.
    candidate_branches: list[str] = []

    for i in range(1, len(args)):
        arg = args[i]
        if arg.startswith("-"):
            continue
        # Check for refspec syntax (e.g. HEAD:refs/heads/main)
        refspec_dst = _extract_refspec_destination(arg)
        if refspec_dst is not None:
            candidate_branches.append(refspec_dst)
        else:
            candidate_branches.append(arg)

    if branch is not None:
        candidate_branches.append(branch)

    for cb in candidate_branches:
        if _normalise_branch(cb) in _PROTECTED_BRANCHES:
            return True

    return False


# ---------------------------------------------------------------------------
# Subprocess execution
# ---------------------------------------------------------------------------


async def _run_git(
    *args: str,
    cwd: str = ".",
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Execute a git command via ``asyncio.create_subprocess_exec``.

    Args:
        *args: Git arguments (e.g. ``"status"``, ``"--porcelain"``).
        cwd: Working directory for the command.
        env: Optional environment override.

    Returns:
        Tuple of ``(returncode, stdout, stderr)``.
    """
    cmd = [_git_binary, *args]
    logger.debug("git_executing", cmd=cmd, cwd=cwd)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
    )

    stdout_bytes, stderr_bytes = await process.communicate()
    returncode = process.returncode if process.returncode is not None else -1

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    if returncode != 0:
        logger.error(
            "git_command_failed",
            cmd=cmd,
            returncode=returncode,
            stderr=stderr,
        )
    else:
        logger.debug(
            "git_command_ok",
            cmd=cmd,
            returncode=returncode,
        )

    return returncode, stdout, stderr


def _assert_zero(code: int, stderr: str, operation: str) -> None:
    """Raise ``GitCommandError`` if *code* is non-zero."""
    if code != 0:
        raise GitCommandError(
            f"git {operation} failed (exit {code}): {stderr}"
        )


# ---------------------------------------------------------------------------
# Environment helper
# ---------------------------------------------------------------------------


def _build_env() -> dict[str, str] | None:
    """Return environment with GITHUB_PAT if needed for push operations.

    Returns ``None`` if GITHUB_PAT is not set, signalling to use the
    current process environment.
    """
    env = os.environ.copy()
    pat = env.get("GITHUB_PAT", "")
    if not pat:
        logger.warning("github_pat_not_set")
    return env


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="git_status")
async def git_status(repo_path: str = ".") -> str:
    """Get git status. Auth: READ_AUTO."""
    code, stdout, stderr = await _run_git("status", "--porcelain", cwd=repo_path)
    _assert_zero(code, stderr, "status")
    logger.info("git_status_complete", repo_path=repo_path, changes=bool(stdout))
    return stdout if stdout else "No changes."


@require_approval(AuthLevel.READ_AUTO, tool_name="git_log")
async def git_log(repo_path: str = ".", count: int = 10) -> str:
    """Get git log. Auth: READ_AUTO."""
    code, stdout, stderr = await _run_git(
        "log",
        f"-{count}",
        "--oneline",
        "--decorate",
        cwd=repo_path,
    )
    _assert_zero(code, stderr, "log")
    logger.info("git_log_complete", repo_path=repo_path, count=count)
    return stdout if stdout else "No commits."


@require_approval(AuthLevel.READ_AUTO, tool_name="git_diff")
async def git_diff(repo_path: str = ".", staged: bool = False) -> str:
    """Get git diff. Auth: READ_AUTO."""
    args: list[str] = ["diff"]
    if staged:
        args.append("--staged")
    code, stdout, stderr = await _run_git(*args, cwd=repo_path)
    _assert_zero(code, stderr, "diff")
    logger.info("git_diff_complete", repo_path=repo_path, staged=staged)
    return stdout if stdout else "No changes."


@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="git_commit")
async def git_commit(
    repo_path: str,
    message: str,
    files: list[str] | None = None,
) -> str:
    """Commit changes. Auth: WRITE_NOTIFY.

    If *files* is provided they are staged before committing.  Otherwise
    only previously-staged changes are committed.
    """
    if files:
        for f in files:
            code_add, _stdout_add, stderr_add = await _run_git(
                "add", f, cwd=repo_path
            )
            _assert_zero(code_add, stderr_add, f"add {f}")
            logger.debug("git_staged", file=f)

    code, stdout, stderr = await _run_git(
        "commit", "-m", message, cwd=repo_path
    )
    _assert_zero(code, stderr, "commit")
    logger.info("git_commit_complete", repo_path=repo_path, message=message[:60])
    return stdout if stdout else "Commit successful."


@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="git_push")
async def git_push(
    repo_path: str = ".",
    branch: str | None = None,
) -> str:
    """Push to remote.

    Auth: WRITE_NOTIFY (normal push).  Force push is gated separately
    via ``git_push_force`` with DESTRUCTIVE_APPROVAL.
    """
    return await _git_push_impl(repo_path, force=False, branch=branch)


@require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="git_push_force")
async def git_push_force(
    repo_path: str = ".",
    branch: str | None = None,
) -> str:
    """Force push to remote.

    Auth: DESTRUCTIVE_APPROVAL.  Additionally, force push to main/master
    is blocked at run-time with a FORBIDDEN check inside ``_git_push_impl``.
    """
    return await _git_push_impl(repo_path, force=True, branch=branch)


async def _git_push_impl(
    repo_path: str = ".",
    force: bool = False,
    branch: str | None = None,
) -> str:
    """Internal push implementation shared by ``git_push`` and ``git_push_force``.

    Auth levels:
        - Normal push: ``WRITE_NOTIFY`` (applied by ``git_push`` decorator)
        - Force push: ``DESTRUCTIVE_APPROVAL`` (applied by ``git_push_force`` decorator)
        - Force push to main/master: run-time ``FORBIDDEN`` (checked here)
    """
    args: list[str] = ["push"]
    if force:
        args.append("--force")

    # Build positional arguments
    remote = "origin"
    if branch is not None:
        args.append(remote)
        args.append(branch)
    else:
        args.append(remote)

    # Check forbidden BEFORE execution (force push to main/master).
    if _is_forbidden(args, branch):
        forbidden_branch = branch or "main"
        logger.warning(
            "git_push_forbidden",
            repo_path=repo_path,
            branch=forbidden_branch,
        )
        raise ForbiddenOperationError(
            f"Force push to '{forbidden_branch}' branch is forbidden."
        )

    env = _build_env()
    code, stdout, stderr = await _run_git(*args, cwd=repo_path, env=env)
    _assert_zero(code, stderr, "push")
    logger.info(
        "git_push_complete",
        repo_path=repo_path,
        force=force,
        branch=branch,
    )
    return stdout if stdout else "Push successful."


# Backward-compatible aliases (tests import with underscore prefix)
_git_status = git_status
_git_log = git_log
_git_diff = git_diff
_git_commit = git_commit
_git_push = _git_push_impl


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register git tools on the MCP server.

    Adds six tools: ``git_status``, ``git_log``, ``git_diff``,
    ``git_commit``, ``git_push``, and ``git_push_force``, each
    decorated with the appropriate ``AuthLevel`` gate.

    For push, two variants are registered:
        - ``git_push`` (normal) → ``WRITE_NOTIFY``
        - ``git_push_force`` (force) → ``DESTRUCTIVE_APPROVAL``
          with additional run-time ``FORBIDDEN`` check for main/master.
    """
    # Log the configured git binary at registration time for diagnostics.
    _find_git()

    mcp.tool(name="git_status")(git_status)
    mcp.tool(name="git_log")(git_log)
    mcp.tool(name="git_diff")(git_diff)
    mcp.tool(name="git_commit")(git_commit)
    mcp.tool(name="git_push")(git_push)
    mcp.tool(name="git_push_force")(git_push_force)

    logger.info("git_tools_registered", binary=_git_binary)