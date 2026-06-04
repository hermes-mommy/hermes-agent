#!/usr/bin/env python3
"""Consent Gate Hook — pre_tool_call (200ms, on_failure: block).

Checks whether a tool call requires operator consent and verifies that
consent has been granted. Reads consent state from Redis DB5.

Allowed network targets: localhost:6380 (Redis), localhost:5433 (PostgreSQL).

Exit codes:
  0 = ALLOW (tool call permitted)
  1 = BLOCK (consent not granted or consent required but unavailable)
"""

from __future__ import annotations

import sys
import time
from typing import Final

from _hook_utils import get_redis_connection, read_stdin_json, setup_logger, write_stdout_json

_log = setup_logger("consent_gate")

# ── Tool Category Mapping ─────────────────────────────────────────────────────

# Tools that ALWAYS require consent before execution
CONSENT_REQUIRED_TOOLS: Final[dict[str, str]] = {
    # Surveillance tools
    "surveillance_start": "surveillance",
    "surveillance_stop": "surveillance",
    "surveillance_query": "surveillance",
    "surveillance_status": "surveillance",
    "camera_capture": "surveillance",
    "location_query": "surveillance",
    "screen_capture": "surveillance",
    # Destructive tools
    "delete_memory": "destructive",
    "delete_file": "destructive",
    "drop_table": "destructive",
    "force_push": "destructive",
    "rm_rf": "destructive",
    "uninstall": "destructive",
    # Financial tools
    "process_payment": "financial",
    "transfer_funds": "financial",
    "make_purchase": "financial",
    "wallet_access": "financial",
    # System tools
    "shutdown": "system",
    "restart": "system",
    "update_system": "system",
    "modify_config": "system",
    "run_script": "system",
    # Network tools
    "open_port": "network",
    "create_tunnel": "network",
    "modify_firewall": "network",
    "ssh_connect": "network",
    "proxy_enable": "network",
}

# Tool name prefix matching for dynamic/plugin tools
CATEGORY_PREFIXES: Final[list[tuple[str, str]]] = [
    ("surveillance_", "surveillance"),
    ("camera_", "surveillance"),
    ("location_", "surveillance"),
    ("financial_", "financial"),
    ("payment_", "financial"),
    ("system_", "system"),
    ("admin_", "system"),
    ("network_", "network"),
    ("firewall_", "network"),
    ("destructive_", "destructive"),
    ("delete_", "destructive"),
    ("drop_", "destructive"),
]


# ── Consent Resolution ────────────────────────────────────────────────────────


def get_tool_category(tool_name: str) -> str | None:
    """Determine the consent category for *tool_name*.

    Args:
        tool_name: Name of the tool being invoked.

    Returns:
        Category string (surveillance, destructive, financial, system, network)
        or ``None`` if the tool does not require consent.
    """
    # Exact match first
    if tool_name in CONSENT_REQUIRED_TOOLS:
        return CONSENT_REQUIRED_TOOLS[tool_name]

    # Prefix match
    lower_name = tool_name.lower()
    for prefix, category in CATEGORY_PREFIXES:
        if lower_name.startswith(prefix):
            return category

    return None


def check_consent(category: str) -> tuple[bool, str]:
    """Check if consent is granted for *category* in Redis DB5.

    Args:
        category: Consent category (e.g. "surveillance", "destructive").

    Returns:
        ``(granted, reason)`` tuple.
    """
    consent_key = f"guinevere:consent:{category}"

    r = get_redis_connection()
    if r is None:
        # Redis unavailable — fail closed (block)
        return False, f"Consent state unavailable (Redis down) for '{category}'"

    try:
        value = r.get(consent_key)
        if value is None:
            return False, f"Consent not configured for '{category}'"
        consent_state = value.decode("utf-8", errors="replace").strip().lower()
        if consent_state in ("true", "1", "yes", "granted", "enabled"):
            return True, ""
        return False, f"Consent not granted for '{category}' (state: {consent_state})"
    except (ValueError, OSError, UnicodeError) as exc:
        _log.error("Redis consent check failed for %s: %s", category, exc)
        return False, f"Consent check error for '{category}': {exc}"


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Read tool call from stdin, check consent, write result to stdout."""
    start_ns = time.perf_counter_ns()

    try:
        data = read_stdin_json()
    except SystemExit:
        _log.error("Failed to read stdin: invalid or empty JSON")
        write_stdout_json({"action": "block", "reason": "Invalid input JSON"})
        sys.exit(1)

    tool_name: str = str(data.get("tool_name", ""))
    user_id: str = str(data.get("user_id", ""))

    if not tool_name:
        _log.warning("No tool_name in input — allowing (conservative)")
        write_stdout_json({"action": "allow"})
        sys.exit(0)

    # Determine category
    category = get_tool_category(tool_name)
    if category is None:
        elapsed_ns = time.perf_counter_ns() - start_ns
        _log.info(
            "ALLOWED (no consent needed) | tool=%s | user=%s | elapsed_ms=%.2f",
            tool_name,
            user_id,
            elapsed_ns / 1_000_000.0,
        )
        write_stdout_json({"action": "allow"})
        sys.exit(0)

    # Check consent
    granted, reason = check_consent(category)

    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_ms = elapsed_ns / 1_000_000.0

    if granted:
        _log.info(
            "ALLOWED | tool=%s | category=%s | user=%s | elapsed_ms=%.2f",
            tool_name,
            category,
            user_id,
            elapsed_ms,
        )
        write_stdout_json({"action": "allow"})
        sys.exit(0)

    _log.warning(
        "BLOCKED | tool=%s | category=%s | user=%s | reason=%s | elapsed_ms=%.2f",
        tool_name,
        category,
        user_id,
        reason,
        elapsed_ms,
    )
    write_stdout_json({"action": "block", "reason": reason})
    sys.exit(1)


if __name__ == "__main__":
    main()