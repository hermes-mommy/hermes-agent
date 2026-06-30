"""MCP Shell Tool — Whitelisted shell command execution via asyncio.

Provides ``register_tools(mcp: FastMCP) -> None`` to register the ``shell_exec``
tool on the MCP server, gated at ``AuthLevel.READ_AUTO`` (shell operations pass through without approval).

Command Safety:
    1. Base command must exist in ``ALLOWED_COMMANDS`` (exact prefix match).
    2. Injection patterns (``;``, ``|``, ``&&``, ``||``, backticks, ``$()``,
       redirection) are rejected before parsing.
    3. Known destructive patterns (``rm -rf``, ``sudo``, ``mkfs``, etc.) are
       blocked outright.
    4. Execution uses ``asyncio.create_subprocess_exec`` — never shell=True.
"""

from __future__ import annotations

import asyncio
import shlex
import time
from typing import TYPE_CHECKING, Final

import structlog

from guinvere.mcp.auth import AuthLevel, ForbiddenOperationError, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Whitelist — only these commands (or compound prefixes) are allowed
# ---------------------------------------------------------------------------

ALLOWED_COMMANDS: frozenset[str] = frozenset({
    "ls",
    "cat",
    "grep",
    "find",
    "wc",
    "head",
    "tail",
    "python",
    "pip",
    "git",
    "systemctl status",
    "df",
    "free",
    "uptime",
    "hostname",
    "whoami",
    "pwd",
    "echo",
    "date",
    "which",
    "file",
    "stat",
})

# ---------------------------------------------------------------------------
# Hard-block patterns — if ANY substring matches, reject immediately
# ---------------------------------------------------------------------------

BLOCKED_PATTERNS: frozenset[str] = frozenset({
    "rm -rf",
    "mkfs",
    "dd",
    "sudo",
    "chmod 777",
    "wget | sh",
    "curl | sh",
    "wget|sh",
    "curl|sh",
    ":(){",  # fork bomb
    "> /dev/sda",
    "mv / /dev/null",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
})

# ---------------------------------------------------------------------------
# Aizanta isolation — block paths and services owned by Aizanta
# ---------------------------------------------------------------------------

_BLOCKED_PATH_PATTERNS: Final[frozenset[str]] = frozenset({
    "/home/aizanta",
    "/etc/aizanta",
    "/var/lib/aizanta",
    "/opt/aizanta",
})

_BLOCKED_SERVICE_PATTERNS: Final[frozenset[str]] = frozenset({
    "aizanta",
})

# ---------------------------------------------------------------------------
# Injection characters — presence anywhere means rejection
# (checked on the raw command string before parsing)
# ---------------------------------------------------------------------------

_INJECTION_CHARS: frozenset[str] = frozenset({
    ";",    # command chaining
    "|",    # piping
    "&&",   # AND chaining
    "||",   # OR chaining
    "`",    # backtick execution
    "$(",   # subshell execution
    ">",    # output redirection
    "<",    # input redirection
})

# Maximum timeout in seconds (configurable per call, capped here)
_MAX_TIMEOUT: int = 300

# Default timeout in seconds
_DEFAULT_TIMEOUT: int = 30


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class CommandForbiddenError(ForbiddenOperationError):
    """Raised when a shell command is blocked by whitelist or injection checks."""


class ShellTimeoutError(Exception):
    """Raised when a shell command exceeds its configured timeout."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _check_injection(command: str) -> None:
    """Scan *command* for injection characters and raise if found.

    Args:
        command: The raw (unparsed) command string.

    Raises:
        CommandForbiddenError: If any injection character is detected.
    """
    for char in _INJECTION_CHARS:
        if char in command:
            logger.warning(
                "shell_injection_detected",
                command=command[:120],
                injection_char=char,
            )
            raise CommandForbiddenError(
                f"Injection pattern '{char}' detected in command."
            )


def _check_blocked_patterns(command: str) -> None:
    """Scan *command* for blocked substrings and raise if found.

    Args:
        command: The raw (unparsed) command string.

    Raises:
        CommandForbiddenError: If a blocked pattern is detected.
    """
    lowered = command.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in lowered:
            logger.warning(
                "shell_blocked_pattern",
                command=command[:120],
                pattern=pattern,
            )
            raise CommandForbiddenError(
                f"Blocked pattern '{pattern}' detected in command."
            )


def _check_path_isolation(command: str) -> None:
    """Scan *command* for Aizanta-isolated paths and raise if found.

    Args:
        command: The raw (unparsed) command string.

    Raises:
        ForbiddenOperationError: If the command references an Aizanta-isolated path.
    """
    for pattern in _BLOCKED_PATH_PATTERNS:
        if pattern in command:
            logger.warning(
                "shell_path_blocked",
                command=command[:120],
                blocked_path=pattern,
            )
            raise ForbiddenOperationError(
                "shell_path_blocked: command references Aizanta-isolated path"
            )


def validate_command(cmd: str) -> tuple[str, list[str]]:
    """Parse and validate a shell command against the whitelist.

    Checks (in order):
        1. Injection characters (``;``, ``|``, ``&&``, ``||``, backticks,
           ``$()``, redirection).
        2. Blocked destructive patterns (``rm -rf``, ``sudo``, ``mkfs``, etc.).
        3. ``shlex.split`` to produce an argument list.
        4. Whitelist membership (exact match or compound prefix like
           ``systemctl status``).

    Args:
        cmd: The raw command string from the caller.

    Returns:
        A ``(base_command, args)`` tuple where ``base_command`` is the
        matched whitelist entry and ``args`` is the argument list for
        ``asyncio.create_subprocess_exec``.

    Raises:
        CommandForbiddenError: If the command fails any validation step.
    """
    stripped = cmd.strip()

    if not stripped:
        raise CommandForbiddenError("Empty command.")

    _check_injection(stripped)
    _check_blocked_patterns(stripped)

    try:
        args = shlex.split(stripped)
    except ValueError as exc:
        raise CommandForbiddenError(f"Invalid command syntax: {exc}") from exc

    if not args:
        raise CommandForbiddenError("Empty command after parsing.")

    # Resolve the whitelist key.  Compound entries like "systemctl status"
    # are matched by joining the first two tokens when the first token
    # alone is not in the whitelist.
    base: str
    if args[0] in ALLOWED_COMMANDS:
        base = args[0]
    elif len(args) >= 2 and f"{args[0]} {args[1]}" in ALLOWED_COMMANDS:
        base = f"{args[0]} {args[1]}"
    else:
        logger.warning("shell_command_not_allowed", command=stripped[:120])
        raise CommandForbiddenError(
            f"Command '{args[0]}' is not in the allowed list."
        )

    # Block systemctl commands targeting Aizanta services
    if args[0] == "systemctl":
        for arg in args[1:]:
            if arg.lower() in _BLOCKED_SERVICE_PATTERNS:
                logger.warning(
                    "shell_service_blocked",
                    command=stripped[:120],
                    service=arg,
                )
                raise ForbiddenOperationError(
                    f"shell_service_blocked: systemctl targeting Aizanta service '{arg}'"
                )

    logger.debug("shell_command_validated", base=base, args=args)
    return base, args


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


async def _execute(args: list[str], workdir: str | None, timeout: int) -> dict[str, object]:
    """Run *args* via ``asyncio.create_subprocess_exec`` with a deadline.

    Args:
        args: Argument list (never includes shell operators).
        workdir: Working directory for the subprocess.
        timeout: Deadline in seconds.

    Returns:
        Dict with ``exit_code``, ``stdout``, ``stderr``, ``command``,
        and ``duration_ms``.

    Raises:
        ShellTimeoutError: If the process exceeds *timeout* seconds.
    """
    start = time.monotonic()

    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=workdir,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        elapsed = (time.monotonic() - start) * 1000
        logger.error(
            "shell_command_timeout",
            args=args,
            timeout=timeout,
            duration_ms=elapsed,
        )
        raise ShellTimeoutError(
            f"Command timed out after {timeout}s"
            f"  args={args!r}"
        )

    exit_code = process.returncode if process.returncode is not None else -1
    elapsed = (time.monotonic() - start) * 1000

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    log_level = "error" if exit_code != 0 else "info"
    getattr(logger, log_level)(
        "shell_command_complete",
        args=args,
        exit_code=exit_code,
        duration_ms=round(elapsed, 2),
        stdout_len=len(stdout),
        stderr_len=len(stderr),
    )

    return {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "command": " ".join(args),
        "duration_ms": round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# Public tool function (decorated at module level)
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="shell_exec")
async def shell_exec(
    command: str,
    workdir: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, object]:
    """Execute a whitelisted shell command.

    The command is validated against ``ALLOWED_COMMANDS``, scanned for
    injection patterns, and run via ``asyncio.create_subprocess_exec``
    (no shell=True).  A non-zero exit code is returned in the result
    dict rather than raised — the caller decides how to handle it.

    Args:
        command: Shell command string (e.g. ``"ls -la /tmp"``).
        workdir: Optional working directory for the subprocess.
        timeout: Deadline in seconds (1 – 300, default 30).

    Returns:
        ``{"exit_code": int, "stdout": str, "stderr": str, "command": str, "duration_ms": float}``.

    Raises:
        CommandForbiddenError: If the command fails whitelist or injection checks.
        ShellTimeoutError: If the subprocess exceeds *timeout*.
        ForbiddenOperationError: If operator denies the ``READ_AUTO`` request.
    """
    if not isinstance(timeout, int) or timeout < 1:
        timeout = _DEFAULT_TIMEOUT
    timeout = min(timeout, _MAX_TIMEOUT)

    _check_path_isolation(command)

    _base, args = validate_command(command)

    logger.info(
        "shell_exec_requested",
        command=command[:120],
        workdir=workdir,
        timeout=timeout,
    )

    return await _execute(args, workdir, timeout)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register the ``shell_exec`` tool on the MCP server.

    All shell operations require ``READ_AUTO`` — the operator
    must explicitly approve each invocation via Discord.
    """

    mcp.tool()(shell_exec)

    logger.info("shell_tool_registered")