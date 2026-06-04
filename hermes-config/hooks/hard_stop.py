#!/usr/bin/env python3
"""Hard Stop Safety Hook — pre_prompt (50ms, on_failure: block).

CRITICAL — This is the #1 safety hook. It intercepts every prompt BEFORE
the LLM is called and checks for the HARD STOP safe word. Must complete
in under 50ms with zero network I/O during execution.

Safe word resolution (in priority order):
  1. ``GUINEVERE_SAFE_WORD`` environment variable (instant, local)
  2. Redis DB5 key ``guinevere:safe_word`` (cached at module load)
  3. Hardcoded fallback: "HARD STOP"

Exit codes:
  0 = PASS (allow prompt through)
  1 = BLOCK (HARD STOP detected)
"""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Final

from _hook_utils import read_stdin_json, setup_logger, write_stdout_json

# ── Logger ────────────────────────────────────────────────────────────────────

_log = setup_logger("hard_stop")


# ── Safe Word Resolution (one-time, at import) ────────────────────────────────
# This is the ONLY network call hard_stop.py makes — once at import time.
# All subsequent hook invocations use the in-memory cached value.


def _resolve_safe_word() -> str:
    """Resolve safe word from env, Redis, or hardcoded fallback.

    Priority: env var > Redis DB5 > hardcoded default.
    """
    # 1. Environment variable (instant)
    env_word = os.environ.get("GUINEVERE_SAFE_WORD", "").strip()
    if env_word:
        _log.info("Safe word resolved from env: length=%d", len(env_word))
        return env_word

    # 2. Redis DB5 (one-time network call at import)
    try:
        from _hook_utils import get_redis_connection

        r = get_redis_connection()
        if r is not None:
            redis_word = r.get("guinevere:safe_word")
            if redis_word is not None:
                word = redis_word.decode("utf-8", errors="replace").strip()
                if word:
                    _log.info("Safe word resolved from Redis DB5: length=%d", len(word))
                    return word
    except (ValueError, OSError, UnicodeError) as exc:
        _log.warning("Redis safe word lookup failed, using fallback: %s", exc)

    # 3. Hardcoded fallback
    _log.info("Safe word resolved from hardcoded fallback")
    return "HARD STOP"


SAFE_WORD: Final[str] = _resolve_safe_word()
"""The active safe word — resolved once at import, never changes at runtime."""

# ── Compiled Patterns (pre-computed at import, zero runtime cost) ─────────────


def _build_patterns(word: str) -> re.Pattern[str]:
    """Build a case-insensitive regex for exact and near-match detection.

    Matches:
      - Exact safe word (case-insensitive, optional leading/trailing whitespace)
      - Hyphenated variant (e.g. "hard-stop")
      - Underscore variant (e.g. "hard_stop")
      - Compact (no space) variant
      - Double-backtick or code-fenced version

    Args:
        word: The canonical safe word.

    Returns:
        Compiled regex pattern with ``re.IGNORECASE``.
    """
    escaped = re.escape(word)
    # Build alternation: original, hyphenated, underscore, compact
    variations: list[str] = [escaped]
    if " " in word:
        variations.append(escaped.replace(r"\ ", "-"))
        variations.append(escaped.replace(r"\ ", "_"))
        variations.append(escaped.replace(r"\ ", ""))
    # Also match the word inside backticks or code fences
    patterns = "|".join(variations)
    full_pattern = rf"(?:^|\s|`|```)({patterns})(?:\s|$|`|```)"
    return re.compile(full_pattern, re.IGNORECASE)


SAFE_WORD_PATTERN: Final[re.Pattern[str]] = _build_patterns(SAFE_WORD)
"""Pre-compiled regex — zero allocs per invocation."""

# Also compile a broader semantic match for "stop", "pause", "neutral mode"
# as required by PersonaSafetyPolicy §7.1
SAFE_EQUIVALENT_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:\b|^)(stop|pause|neutral(?:\s*mode)?|serious(?:\s*mode)?|i need a break|"
    r"aku (?:mau|butuh) (?:berhenti|pause|stop))(?:[.!]*\s*$|$)",
    re.IGNORECASE,
)
"""Broad semantic equivalent detection based on PersonaSafetyPolicy §7.1."""


# ── Detection ─────────────────────────────────────────────────────────────────


def detect_hard_stop(prompt: str) -> tuple[bool, str]:
    """Check if *prompt* triggers HARD STOP safe word.

    Args:
        prompt: The raw user message text.

    Returns:
        ``(blocked, reason)`` tuple.
        ``blocked=True`` means the prompt must NOT reach the LLM.
    """
    if not prompt or not prompt.strip():
        return False, ""

    # 1. Exact safe word match (primary, fastest path)
    if SAFE_WORD_PATTERN.search(prompt):
        return True, f"HARD_STOP triggered: safe word '{SAFE_WORD}' detected"

    # 2. Broad semantic equivalent — BUT only for standalone stop-words
    #    (avoid false positives like "the bus stop is near")
    stripped = prompt.strip().lower()
    # Only trigger on short messages where stop is clearly the intent
    if len(stripped) <= 60 and SAFE_EQUIVALENT_PATTERN.search(stripped):
        return True, "HARD_STOP triggered: semantic equivalent stop signal"

    return False, ""


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Read prompt from stdin, check for HARD STOP, write result to stdout."""
    start_ns = time.perf_counter_ns()

    try:
        data = read_stdin_json()
    except SystemExit:
        # read_stdin_json already exited with code 2 on parse failure
        _log.error("Failed to read stdin: invalid or empty JSON")
        write_stdout_json({"action": "block", "reason": "Invalid input JSON"})
        sys.exit(1)

    prompt: str = str(data.get("prompt", ""))
    user_id: str = str(data.get("user_id", ""))
    channel_id: str = str(data.get("channel_id", ""))

    # ── Detection (pure in-memory, sub-ms) ───────────────────────────────
    blocked, reason = detect_hard_stop(prompt)

    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_ms = elapsed_ns / 1_000_000.0

    if blocked:
        result: dict[str, object] = {
            "action": "block",
            "reason": reason,
        }
        _log.info(
            "BLOCKED | prompt_len=%d | user=%s | elapsed_ms=%.2f | reason=%s",
            len(prompt),
            user_id,
            elapsed_ms,
            reason,
        )
        write_stdout_json(result)
        sys.exit(1)

    result = {"action": "allow"}
    _log.info(
        "ALLOWED | prompt_len=%d | user=%s | elapsed_ms=%.2f",
        len(prompt),
        user_id,
        elapsed_ms,
    )
    write_stdout_json(result)
    sys.exit(0)


if __name__ == "__main__":
    main()