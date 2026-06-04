#!/usr/bin/env python3
"""DNR (Do Not Remember) Filter Hook — post_tool_call (50ms, on_failure: block).

Scans tool results for content flagged as Do Not Remember before it reaches
memory or response context. Reads DNR list from Redis DB5.

Exit codes:
  0 = ALLOW (no DNR content detected)
  1 = BLOCK (DNR content found in tool result)
"""

from __future__ import annotations

import re
import sys
import time
from typing import Final

from _hook_utils import get_redis_connection, read_stdin_json, setup_logger, write_stdout_json

_log = setup_logger("dnr_filter")

# ── Static DNR Patterns (always enforced, zero network) ───────────────────────
# These patterns do not depend on Redis — they are hardcoded as defense-in-depth.

STATIC_DNR_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    (
        "operator_phone",
        re.compile(
            r"(?:\+?62\d{8,15}|08\d{8,12})",
        ),
    ),
    (
        "operator_email",
        re.compile(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        ),
    ),
    (
        "api_key_leak",
        re.compile(
            r"(?:sk-[a-zA-Z0-9]{20,}|AIza[a-zA-Z0-9_-]{30,}|"
            r"(?:api[_-]?key|apikey|api_secret|secret_key)\s*[:=]\s*[\"'][^\n]{8,}[\"'])",
            re.IGNORECASE,
        ),
    ),
    (
        "discord_token",
        re.compile(
            r"[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27}",
        ),
    ),
    (
        "private_address",
        re.compile(
            r"(?:jalan|jl\.?|alamat)\s+[\w\s.,]+\b(?:no\.?|nomor)\s*\d+",
            re.IGNORECASE,
        ),
    ),
    (
        "surveillance_raw",
        re.compile(
            r"(?:screenshot|camera\s+feed|location\s+log)\s*[:=]\s*base64:",
            re.IGNORECASE,
        ),
    ),
    (
        "password_leak",
        re.compile(
            r"(?:password|passwd|pwd)\s*[:=]\s*[\"'][^\n]{4,}[\"']",
            re.IGNORECASE,
        ),
    ),
]

# ── Cached DNR List ───────────────────────────────────────────────────────────

_dynamic_dnr_cache: list[str] | None = None
"""In-memory cache of DNR keywords from Redis DB5."""


def _load_dnr_list() -> list[str]:
    """Load DNR keywords from Redis DB5 key ``guinevere:dnr_list``.

    Returns:
        List of DNR keyword strings. Empty list if Redis is unavailable.
    """
    global _dynamic_dnr_cache  # noqa: PLW0603

    if _dynamic_dnr_cache is not None:
        return _dynamic_dnr_cache

    r = get_redis_connection()
    if r is None:
        _log.warning("Redis unavailable — DNR filter using static patterns only")
        _dynamic_dnr_cache = []
        return _dynamic_dnr_cache

    try:
        raw = r.get("guinevere:dnr_list")
        if raw is None:
            _log.info("No DNR list found in Redis DB5")
            _dynamic_dnr_cache = []
        else:
            import json as _json

            items = _json.loads(raw.decode("utf-8", errors="replace"))
            _dynamic_dnr_cache = [str(item).strip().lower() for item in items if item]
            _log.info("Loaded %d DNR keywords from Redis", len(_dynamic_dnr_cache))
    except (ValueError, OSError, UnicodeError) as exc:
        _log.error("Failed to load DNR list from Redis: %s", exc)
        _dynamic_dnr_cache = []

    return _dynamic_dnr_cache


# ── Detection ─────────────────────────────────────────────────────────────────


def check_dnr(result_text: str) -> tuple[bool, str]:
    """Check *result_text* for DNR-flagged content.

    Args:
        result_text: The tool result as a string.

    Returns:
        ``(blocked, reason)`` tuple.
    """
    if not result_text:
        return False, ""

    text_lower = result_text.lower()

    # 1. Static patterns (always enforced)
    for label, pattern in STATIC_DNR_PATTERNS:
        if pattern.search(result_text):
            return True, f"DNR static pattern: {label}"

    # 2. Dynamic DNR keywords from Redis
    for keyword in _load_dnr_list():
        if keyword in text_lower:
            return True, f"DNR keyword: {keyword}"

    return False, ""


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Read tool result from stdin, check for DNR, write result to stdout."""
    start_ns = time.perf_counter_ns()

    try:
        data = read_stdin_json()
    except SystemExit:
        _log.error("Failed to read stdin: invalid or empty JSON")
        write_stdout_json({"action": "block", "reason": "Invalid input JSON"})
        sys.exit(1)

    tool_name: str = str(data.get("tool_name", ""))
    tool_result_raw = data.get("tool_result", "")
    user_id: str = str(data.get("user_id", ""))

    # Handle tool_result that might be a dict, list, or string
    if isinstance(tool_result_raw, (dict, list)):
        import json as _json

        result_text: str = _json.dumps(tool_result_raw, default=str)
    else:
        result_text = str(tool_result_raw)

    blocked, reason = check_dnr(result_text)

    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_ms = elapsed_ns / 1_000_000.0

    if blocked:
        _log.warning(
            "BLOCKED | tool=%s | user=%s | reason=%s | elapsed_ms=%.2f",
            tool_name,
            user_id,
            reason,
            elapsed_ms,
        )
        write_stdout_json({"action": "block", "reason": reason})
        sys.exit(1)

    _log.info(
        "ALLOWED | tool=%s | user=%s | result_len=%d | elapsed_ms=%.2f",
        tool_name,
        user_id,
        len(result_text),
        elapsed_ms,
    )
    write_stdout_json({"action": "allow"})
    sys.exit(0)


if __name__ == "__main__":
    main()