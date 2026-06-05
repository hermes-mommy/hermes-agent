#!/usr/bin/env python3
"""Hybrid Tool Safety Guards — pre_tool_call (on_failure: block).

Implements deterministic safety guards for:
  - Shell injection detection (``;``, ``|``, ``&&``, backticks, ``$()``)
  - Docker 5-layer guard (container/image/forbidden-patterns/network/sub-command)
  - Git force-push to main/master guard
  - Aizanta path isolation (``/home/aizanta``, ``/etc/aizanta``, etc.)
  - Port isolation (block standard 5432/6379, protect canonical 5433/6380)

Every guard returns ``None`` when safe (allow) or a block dict
``{"action": "block", "reason": "..."}`` when a violation is detected.

Usage as a Hermes shell hook (stdin/stdout JSON):
    $ echo '{"tool_name": "shell", "args": {"command": "ls; rm -rf /"}}' \\
        | python3 hybrid_guards.py
    {"action": "block", "reason": "SHELL_INJECTION: ..."}
"""

from __future__ import annotations

import importlib
import re
import sys
from typing import Final, Protocol, cast


class Logger(Protocol):
    """Logger protocol used by hook utilities."""

    def info(self, message: str, *args: object) -> None: ...
    def warning(self, message: str, *args: object) -> None: ...
    def error(self, message: str, *args: object) -> None: ...


class HookUtilsModule(Protocol):
    """Typed subset of ``_hook_utils`` used by this hook."""

    def read_stdin_json(self) -> dict[str, object]: ...
    def setup_logger(self, name: str) -> Logger: ...
    def write_stdout_json(self, data: dict[str, object]) -> None: ...


_hook_utils = cast(
    HookUtilsModule,
    cast(object, importlib.import_module("_hook_utils")),
)
read_stdin_json = _hook_utils.read_stdin_json
setup_logger = _hook_utils.setup_logger
write_stdout_json = _hook_utils.write_stdout_json

_log = setup_logger("hybrid_guards")

# ==============================================================================
# Constants
# ==============================================================================

# ── Shell Injection ───────────────────────────────────────────────────────────

SHELL_INJECTION_PATTERNS: Final[list[re.Pattern[str]]] = [
    # Command chaining with semicolon
    re.compile(r";"),
    # Double pipe (OR chaining)
    re.compile(r"\|\|"),
    # Double ampersand (AND chaining)
    re.compile(r"&&"),
    # Pipe (command chaining) — not preceded by $ to avoid false $|
    re.compile(r"(?<!\$)\|"),
    # Backtick command substitution
    re.compile(r"`[^`]*`"),
    # $() command substitution — not preceded by ( to avoid nested false
    re.compile(r"\$\([^)]*\)"),
    # Dangerous redirections to system files
    re.compile(r">\s*/dev/"),
    re.compile(r">\s*/proc/"),
    # Background execution at end of command
    re.compile(r"&\s*$"),
]

# ── Docker 5-Layer Guard ─────────────────────────────────────────────────────

DOCKER_READ_ONLY_COMMANDS: Final[frozenset[str]] = frozenset({
    "ps", "logs", "inspect", "images", "pull", "search",
    "info", "version", "stats", "top", "port", "history",
})

DOCKER_DESTRUCTIVE_COMMANDS: Final[frozenset[str]] = frozenset({
    "rm", "rmi", "prune", "system_prune", "stop", "restart",
    "kill", "pause", "unpause", "update", "rename",
    "commit", "push", "tag", "load", "save",
    "container_rm", "image_rm", "system_df",
    "container_stop", "container_restart", "container_kill",
    "volume_rm", "network_rm", "network_prune",
})

DOCKER_FORBIDDEN_PATTERNS: Final[list[re.Pattern[str]]] = [
    # System-level destructive patterns
    re.compile(r"\bsystem\s+prune\b"),
    re.compile(r"\bcontainer\s+prune\b"),
    re.compile(r"\bimage\s+prune\b"),
    re.compile(r"\bvolume\s+prune\b"),
    re.compile(r"\bnetwork\s+prune\b"),
    re.compile(r"\bbuildx\s+prune\b"),
    # Mass removal patterns
    re.compile(r"\brm\s+-[a-z]*f"),
    re.compile(r"\brmi\s+-[a-z]*f"),
    # Unauthorized net operations
    re.compile(r"\bnetwork\s+create\b"),
    re.compile(r"\bnetwork\s+connect\b"),
]

CONTAINER_NAME_RE: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
"""Valid container/image name pattern — no shell metacharacters."""

IMAGE_METACHARACTERS: Final[re.Pattern[str]] = re.compile(r"[;|&`$(){}<>!\\]")
"""Metacharacters forbidden in image names to prevent injection."""

# Non-guinevere container prefix patterns that are blocked for destructive ops
GUIINEVERE_NET_PREFIX: Final[str] = "guinevere-"

# ── Git Force-Push Guard ─────────────────────────────────────────────────────

PROTECTED_BRANCHES: Final[frozenset[str]] = frozenset({"main", "master"})

FORCE_PUSH_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\bpush\s+--force\b"),
    re.compile(r"\bpush\s+-f\b"),
    re.compile(r"\bpush\s+--force-with-lease\b"),
]

REVOCABLE_FORCE_PUSH_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\bpush\s+--force\b"),
    re.compile(r"\bpush\s+-f\b"),
    re.compile(r"\bpush\s+--force-with-lease\b"),
]

FORCE_PUSH_ALIAS_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\bforce_push\b"),
    re.compile(r"\bforce-push\b"),
    re.compile(r"\bpushf\b"),
]

# ── Aizanta Path Isolation ───────────────────────────────────────────────────

AIZANTA_BLOCKED_PATHS: Final[list[str]] = [
    "/home/aizanta",
    "/etc/aizanta",
    "/var/lib/aizanta",
    "/opt/aizanta",
    "/aizanta",
]

AIZANTA_BLOCKED_PATH_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"/home/aizanta"),
    re.compile(r"/etc/aizanta"),
    re.compile(r"/var/lib/aizanta"),
    re.compile(r"/opt/aizanta"),
    re.compile(r"^/aizanta"),
]

# ── Port Isolation ───────────────────────────────────────────────────────────

# Standard (forbidden for non-canonical use)
STANDARD_PORTS: Final[dict[int, str]] = {
    5432: "postgresql",
    6379: "redis",
}

# Canonical Guinevere ports (protected)
CANONICAL_PORTS: Final[dict[int, str]] = {
    5433: "postgresql_canonical",
    6380: "redis_canonical",
    20128: "ninerouter",
}

PORT_PATTERNS: Final[list[re.Pattern[str]]] = [
    # PostgreSQL standard port — host:port format
    re.compile(r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0):5432\b"),
    re.compile(r"port\s*=\s*5432\b"),
    re.compile(r"-p\s+5432\b"),
    # Redis standard port
    re.compile(r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0):6379\b"),
    re.compile(r"port\s*=\s*6379\b"),
    re.compile(r"-p\s+6379\b"),
]


# ==============================================================================
# Guard: Shell Injection
# ==============================================================================


def check_shell_injection(command: object) -> dict[str, str] | None:
    """Check *command* for shell injection patterns.

    All commands are scanned for injection patterns regardless of the base
    command name.  A safe base command (e.g. ``ls``) does **not** prevent
    injection detection because ``ls; rm -rf /`` is still dangerous.

    Args:
        command: The full command string to inspect.

    Returns:
        Block dict if injection detected, ``None`` if safe.
    """
    if not command or not isinstance(command, str):
        return None

    for pattern in SHELL_INJECTION_PATTERNS:
        match = pattern.search(command)
        if match is not None:
            return {
                "action": "block",
                "reason": (
                    f"SHELL_INJECTION: Command contains shell injection "
                    f"pattern '{match.group()[:60]}'"
                ),
            }

    return None


# ==============================================================================
# Guard: Docker 5-Layer
# ==============================================================================


def _extract_docker_subcommand(docker_args: str) -> str:
    """Extract the docker sub-command from a docker command string.

    Handles: ``docker ps``, ``docker container rm``, ``docker image prune``.

    Args:
        docker_args: The full docker command string.

    Returns:
        The extracted sub-command (e.g. ``"ps"``, ``"container rm"``).
    """
    parts = docker_args.strip().split()
    if not parts:
        return ""

    # Skip "docker" if present as first word
    start = 0
    if parts[0].lower() == "docker":
        start = 1

    if start >= len(parts):
        return ""

    # Check for docker <noun> <verb> pattern
    docker_nouns = {"container", "image", "volume", "network", "system", "buildx"}
    first = parts[start].lower()
    if first in docker_nouns and start + 1 < len(parts):
        return f"{first}_{parts[start + 1].lower()}"

    return first


def _check_container_name(name: str) -> dict[str, str] | None:
    """Layer 1: Validate container/image name contains no shell metacharacters.

    Args:
        name: Container or image name to validate.

    Returns:
        Block dict if name contains metacharacters, ``None`` if valid.
    """
    if not name:
        return None

    if IMAGE_METACHARACTERS.search(name):
        return {
            "action": "block",
            "reason": f"DOCKER_CONTAINER_NAME: Name contains shell metacharacters: '{name[:80]}'",
        }

    if not CONTAINER_NAME_RE.match(name):
        # Only warn for names that don't match - allow but flag
        pass

    return None


def _check_image_name(image: str) -> dict[str, str] | None:
    """Layer 2: Reject image names with metacharacters.

    Args:
        image: Image name to validate.

    Returns:
        Block dict if image name contains metacharacters, ``None`` if valid.
    """
    if not image:
        return None

    if IMAGE_METACHARACTERS.search(image):
        return {
            "action": "block",
            "reason": f"DOCKER_IMAGE_NAME: Image name contains shell metacharacters: '{image[:80]}'",
        }

    return None


def _check_forbidden_patterns(docker_args: str) -> dict[str, str] | None:
    """Layer 3: Check for forbidden Docker patterns.

    Args:
        docker_args: The full docker command arguments.

    Returns:
        Block dict if a forbidden pattern is found, ``None`` if safe.
    """
    if not docker_args:
        return None

    for pattern in DOCKER_FORBIDDEN_PATTERNS:
        match = pattern.search(docker_args)
        if match is not None:
            return {
                "action": "block",
                "reason": (
                    f"DOCKER_FORBIDDEN: Pattern "
                    f"'{match.group()[:60]}' is not permitted"
                ),
            }

    return None


def _check_network_isolation(
    docker_args: str,
    sub_command: str,
) -> dict[str, str] | None:
    """Layer 4: Verify destructive Docker operations use guinevere- prefix.

    Args:
        docker_args: The full docker command arguments.
        sub_command: The extracted sub-command.

    Returns:
        Block dict if a destructive operation targets a non-guinevere container,
        ``None`` if safe.
    """
    if not docker_args:
        return None

    # Only check destructive commands
    if sub_command not in DOCKER_DESTRUCTIVE_COMMANDS:
        return None

    # Split docker args and filter:
    # 1. Remove "docker" prefix
    # 2. Remove the sub-command itself (first meaningful word)
    # 3. Remove flag args (starting with -)
    # 4. Remove image references (containing : or /)
    parts = docker_args.split()
    filtered: list[str] = []
    sub_found = False
    for p in parts:
        if p.lower() == "docker":
            continue
        if not sub_found:
            sub_found = True
            continue  # Skip sub-command
        if p.startswith("-"):
            continue  # Skip flags
        if ":" in p or "/" in p:
            continue  # Skip image references
        if "=" in p:
            continue  # Skip key=value
        filtered.append(p)

    for pos_arg in filtered:
        # Container names in the guinevere project should start with guinevere-
        if not pos_arg.startswith(GUIINEVERE_NET_PREFIX):
            return {
                "action": "block",
                "reason": (
                    f"DOCKER_NET_ISOLATION: Destructive operation on "
                    f"non-guinevere container '{pos_arg[:60]}' blocked. "
                    f"Only 'guinevere-*' containers are permitted."
                ),
            }

    return None


def _check_sub_command(sub_command: str) -> dict[str, str] | None:
    """Layer 5: Block specific dangerous sub-commands at runtime.

    Args:
        sub_command: The extracted Docker sub-command.

    Returns:
        Block dict if the sub-command is blocked, ``None`` if allowed.
    """
    if not sub_command:
        return None

    # Hard-block specific sub-commands
    sub_command_lower = sub_command.lower()

    # Block system prune variants
    if "prune" in sub_command_lower:
        return {
            "action": "block",
            "reason": f"DOCKER_SUB_COMMAND: 'docker {sub_command}' is not permitted",
        }

    # Block rm/rms with -f (force removal) — caught by forbidden patterns
    if sub_command_lower in ("rm_all", "kill_all", "stop_all"):
        return {
            "action": "block",
            "reason": f"DOCKER_SUB_COMMAND: 'docker {sub_command}' is not permitted",
        }

    return None


def check_docker_5_layer(docker_args: object) -> dict[str, str] | None:
    """Docker 5-layer guard: validate a docker command string.

    Layers:
        1. Container name validation (no metacharacters)
        2. Image name validation (no metacharacters)
        3. Forbidden patterns (system prune, rm -f, etc.)
        4. Network isolation (destructive ops on guinevere-* containers only)
        5. Sub-command blocking (prune variants, mass removal)

    Args:
        docker_args: The full docker command/arguments string.

    Returns:
        Block dict on first violation, ``None`` if all layers pass.
    """
    if not docker_args or not isinstance(docker_args, str):
        return None

    sub_command = _extract_docker_subcommand(docker_args)

    # Read-only docker commands pass through (Layer 0: allow fast-path)
    if sub_command in DOCKER_READ_ONLY_COMMANDS:
        return None

    # Layer 1: Container name validation
    parts = docker_args.split()
    for part in parts:
        if not part.startswith("-") and part.lower() != "docker":
            result = _check_container_name(part)
            if result is not None:
                return result

    # Layer 2: Image name validation
    for part in parts:
        if ":" in part or "/" in part:
            result = _check_image_name(part)
            if result is not None:
                return result

    # Layer 3: Forbidden patterns
    result = _check_forbidden_patterns(docker_args)
    if result is not None:
        return result

    # Layer 4: Network isolation
    result = _check_network_isolation(docker_args, sub_command)
    if result is not None:
        return result

    # Layer 5: Sub-command blocking
    result = _check_sub_command(sub_command)
    if result is not None:
        return result

    return None


# ==============================================================================
# Guard: Git Force-Push
# ==============================================================================


def check_git_force_push(git_args: object) -> dict[str, str] | None:
    """Check *git_args* for force-push operations targeting protected branches.

    Args:
        git_args: The git command arguments/operation string.

    Returns:
        Block dict if force-push to main/master detected, ``None`` if safe.
    """
    if not git_args or not isinstance(git_args, str):
        return None

    git_args_lower = git_args.lower()

    # Check for force-push aliases (word-boundary matched)
    for alias_pattern in FORCE_PUSH_ALIAS_PATTERNS:
        if alias_pattern.search(git_args_lower):
            return {
                "action": "block",
                "reason": "GIT_FORCE_PUSH: Force push alias is blocked",
            }

    # Check for push --force patterns
    is_force_push = False
    for pattern in FORCE_PUSH_PATTERNS:
        if pattern.search(git_args_lower):
            is_force_push = True
            break

    if not is_force_push:
        return None

    # Check if targeting a protected branch
    words = git_args_lower.split()
    # Also expand refspec words (e.g. "main:main" expands to ["main", "main"])
    expanded: list[str] = []
    for w in words:
        expanded.append(w)
        if ":" in w:
            expanded.extend(w.split(":"))

    for branch in PROTECTED_BRANCHES:
        if branch in expanded:
            return {
                "action": "block",
                "reason": (
                    f"GIT_FORCE_PUSH: Force-push to protected branch "
                    f"'{branch}' is blocked"
                ),
            }

    # Force-push to a non-protected branch — still warn but allow
    return None


# ==============================================================================
# Guard: Aizanta Path Isolation
# ==============================================================================


def check_aizanta_path(path: object) -> dict[str, str] | None:
    """Check *path* for Aizanta isolation violations.

    Args:
        path: The filesystem path to check.

    Returns:
        Block dict if path is in a blocked Aizanta directory, ``None`` if safe.
    """
    if not path or not isinstance(path, str):
        return None

    for blocked_path in AIZANTA_BLOCKED_PATHS:
        if blocked_path in path:
            return {
                "action": "block",
                "reason": (
                    f"AIZANTA_ISOLATION: Path '{path[:120]}' is in blocked "
                    f"Aizanta directory '{blocked_path}'"
                ),
            }

    for pattern in AIZANTA_BLOCKED_PATH_PATTERNS:
        match = pattern.search(path)
        if match is not None:
            return {
                "action": "block",
                "reason": f"AIZANTA_ISOLATION: Path '{path[:120]}' matches blocked Aizanta pattern",
            }

    return None


# ==============================================================================
# Guard: Port Isolation
# ==============================================================================


def check_port_isolation(text: object) -> dict[str, str] | None:
    """Check *text* for references to standard (blocked) ports.

    Blocks references to PostgreSQL 5432 and Redis 6379 which are reserved for
    the Aizanta isolation boundary. The canonical Guinevere ports 5433 and 6380
    are the only permitted PostgreSQL and Redis ports.

    Args:
        text: The text to scan (command args, connection string, etc.).

    Returns:
        Block dict if a standard port reference is detected, ``None`` if safe.
    """
    if not text or not isinstance(text, str):
        return None

    for pattern in PORT_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            return {
                "action": "block",
                "reason": (
                    f"PORT_ISOLATION: Standard port '{match.group()[:60]}' "
                    f"is blocked. Use canonical Guinevere ports "
                    f"(PG=5433, Redis=6380)."
                ),
            }

    return None


# ==============================================================================
# Composite Guard: check all guards
# ==============================================================================


def check_hybrid_guards(tool_name: object, command: object = "") -> dict[str, str] | None:
    """Run all applicable guards based on the tool name.

    Routing logic:
        - ``shell``, ``terminal`` → shell injection guard
        - ``docker`` → Docker 5-layer guard
        - ``git`` → Git force-push guard (+ shell injection on args)
        - ``filesystem`` → Aizanta path isolation on path args
        - ``postgres``, ``redis`` → port isolation on connection args

    Args:
        tool_name: The name of the tool being invoked.
        command: The command/arguments string to check.

    Returns:
        Block dict on first violation, ``None`` if all guards pass.
    """
    tool_lower = tool_name.lower() if isinstance(tool_name, str) else ""

    # ── Aizanta path isolation (applies to any tool with path arguments) ──
    if command:
        result = check_aizanta_path(command)
        if result is not None:
            return result

    # ── Shell injection (applies to shell/terminal tools) ──
    if tool_lower in ("shell", "terminal", "shell_exec"):
        if command:
            result = check_shell_injection(command)
            if result is not None:
                return result

    # ── Docker 5-layer guard ──
    if tool_lower in ("docker",):
        if command:
            result = check_docker_5_layer(command)
            if result is not None:
                return result

    # ── Git force-push guard ──
    if tool_lower in ("git",):
        if command:
            result = check_git_force_push(command)
            if result is not None:
                return result
            # Also run shell injection on git args
            result = check_shell_injection(command)
            if result is not None:
                return result

    # ── Port isolation (applies to any tool referencing connection strings) ──
    if command:
        result = check_port_isolation(command)
        if result is not None:
            return result

    return None


# ==============================================================================
# Main (stdin/stdout hook entry point)
# ==============================================================================


def main() -> None:
    """Read tool call from stdin, apply hybrid guards, write result to stdout."""
    try:
        data = read_stdin_json()
    except SystemExit:
        _log.error("Failed to read stdin: invalid or empty JSON")
        write_stdout_json({"action": "block", "reason": "Invalid input JSON"})
        sys.exit(1)

    tool_name: str = str(data.get("tool_name", ""))
    args_value = data.get("args", {})
    args = cast(dict[object, object], args_value) if isinstance(args_value, dict) else {}
    command: str = ""

    # Extract command/args depending on tool type
    if args:
        # shell/terminal: command key
        cmd_val = args.get("command", args.get("cmd", ""))
        if isinstance(cmd_val, str):
            command = cmd_val
        # docker: command key
        dock_cmd = args.get("docker_args", args.get("command", ""))
        if isinstance(dock_cmd, str) and not command:
            command = dock_cmd
        # git: args list or command
        git_val = args.get("args", args.get("command", ""))
        if isinstance(git_val, list):
            command = " ".join(str(x) for x in git_val)
        elif isinstance(git_val, str) and not command:
            command = git_val
        # filesystem: path key
        path_val = args.get("path", "")
        if isinstance(path_val, str):
            command = command or path_val
        # postgres/redis: connection string
        conn_val = args.get("query", args.get("connection", args.get("command", "")))
        if isinstance(conn_val, str) and not command:
            command = conn_val

    result = check_hybrid_guards(tool_name=tool_name, command=command)

    if result is None:
        _log.info("ALLOWED | tool=%s", tool_name)
        write_stdout_json({"action": "allow"})
        sys.exit(0)

    _log.warning(
        "BLOCKED | tool=%s | reason=%s",
        tool_name,
        result.get("reason", "Unknown"),
    )
    result_payload: dict[str, object] = dict(result)
    write_stdout_json(result_payload)
    sys.exit(1)


if __name__ == "__main__":
    main()
