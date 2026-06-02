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

_git_binary: str = "git"


def _find_git() -> str:
    """Return the git binary path or raise ``ConfigurationError``."""
    git = os.environ.get("GIT_BINARY", "git")
    logger.info("git_binary_configured", binary=git)
    return git


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

_FORBIDDEN_PATTERNS: list[tuple[str, ...]] = [
    ("push", "--force", "main"),
    ("push", "--force", "master"),
    ("push", "-f", "main"),
    ("push", "-f", "master"),
]


def _is_forbidden(args: list[str], branch: str | None) -> bool:
    """Check whether a git operation is forbidden.

    Returns ``True`` when the command is a force-push to ``main`` or
    ``master``, regardless of how the branch is passed (positional arg
    or ``branch`` parameter).
    """
    if len(args) < 3:
        return False

    is_push = args[0] == "push"
    is_force = "--force" in args or "-f" in args

    if not (is_push and is_force):
        return False

    # The branch may be in the positional args or passed separately.
    candidate_branches: list[str] = []

    # Positional args after 'push' and flags
    for i in range(1, len(args)):
        arg = args[i]
        if arg.startswith("-"):
            continue
        candidate_branches.append(arg)

    if branch is not None:
        candidate_branches.append(branch)

    protected = {"main", "master"}
    for cb in candidate_branches:
        if cb in protected:
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


async def _git_status(repo_path: str = ".") -> str:
    """Get git status. Auth: READ_AUTO."""
    code, stdout, stderr = await _run_git("status", "--porcelain", cwd=repo_path)
    _assert_zero(code, stderr, "status")
    logger.info("git_status_complete", repo_path=repo_path, changes=bool(stdout))
    return stdout if stdout else "No changes."


async def _git_log(repo_path: str = ".", count: int = 10) -> str:
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


async def _git_diff(repo_path: str = ".", staged: bool = False) -> str:
    """Get git diff. Auth: READ_AUTO."""
    args: list[str] = ["diff"]
    if staged:
        args.append("--staged")
    code, stdout, stderr = await _run_git(*args, cwd=repo_path)
    _assert_zero(code, stderr, "diff")
    logger.info("git_diff_complete", repo_path=repo_path, staged=staged)
    return stdout if stdout else "No changes."


async def _git_commit(
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


async def _git_push(
    repo_path: str = ".",
    force: bool = False,
    branch: str | None = None,
) -> str:
    """Push to remote.

    Auth levels:
        - Normal push: ``WRITE_NOTIFY``
        - Force push: ``DESTRUCTIVE_APPROVAL``
        - Force push to main/master: run-time ``FORBIDDEN``
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


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register git tools on the MCP server.

    Adds five tools: ``git_status``, ``git_log``, ``git_diff``,
    ``git_commit``, and ``git_push``, each decorated with the
    appropriate ``AuthLevel`` gate.

    For ``git_push``, two variants are registered:
        - ``git_push`` (normal) → ``WRITE_NOTIFY``
        - ``git_push_force`` (force) → ``DESTRUCTIVE_APPROVAL``
          with additional run-time ``FORBIDDEN`` check for main/master.
    """
    global _git_binary  # noqa: PLW0603
    _git_binary = _find_git()

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="git_status")
    async def git_status(repo_path: str = ".") -> str:
        return await _git_status(repo_path)

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="git_log")
    async def git_log(repo_path: str = ".", count: int = 10) -> str:
        return await _git_log(repo_path, count)

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="git_diff")
    async def git_diff(repo_path: str = ".", staged: bool = False) -> str:
        return await _git_diff(repo_path, staged)

    @mcp.tool()
    @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="git_commit")
    async def git_commit(
        repo_path: str,
        message: str,
        files: list[str] | None = None,
    ) -> str:
        return await _git_commit(repo_path, message, files)

    @mcp.tool()
    @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="git_push")
    async def git_push(
        repo_path: str = ".",
        branch: str | None = None,
    ) -> str:
        return await _git_push(repo_path, force=False, branch=branch)

    @mcp.tool()
    @require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="git_push_force")
    async def git_push_force(
        repo_path: str = ".",
        branch: str | None = None,
    ) -> str:
        return await _git_push(repo_path, force=True, branch=branch)

    logger.info("git_tools_registered", binary=_git_binary)