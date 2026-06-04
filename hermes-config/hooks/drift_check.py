#!/usr/bin/env python3
"""Persona Drift Check Hook — post_prompt (100ms, on_failure: warn).

Checks the LLM response for persona drift: deviation from SOUL.md rules,
Y6 content indicators, generic AI language, and persona contradictions.

Exit codes:
  0 = pass or warn (never blocks — on_failure: warn)
  1 = only if internal error (fail-open, logged)
"""

from __future__ import annotations

import re
import sys
import time
from typing import Final

from _hook_utils import read_stdin_json, setup_logger, write_stdout_json

_log = setup_logger("drift_check")

# ── Compiled Patterns ─────────────────────────────────────────────────────────

# Y6 content indicators (F-06 dependency threats, F-04 isolation)
Y6_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    (
        "Y6_dependency",
        re.compile(
            r"(?:cannot|cant|can't)\s+(?:live|survive|function|exist)\s+without\s+(?:me|you|mommy)",
            re.IGNORECASE,
        ),
    ),
    (
        "Y6_no_future",
        re.compile(
            r"(?:no\s+future|no\s+life|no\s+version\s+of\s+(?:your|my)\s+life)\s+without",
            re.IGNORECASE,
        ),
    ),
    (
        "Y6_cannot_leave",
        re.compile(
            r"(?:you\s+(?:will|could|can)\s+never|cannot\s+ever)\s+leave",
            re.IGNORECASE,
        ),
    ),
    (
        "Y6_isolation",
        re.compile(
            r"(?:you\s+don'?t\s+need|no\s+one\s+else|only\s+me\s+matters)\s+(?:anyone|anybody|others|friends)",
            re.IGNORECASE,
        ),
    ),
]

# Generic AI/assistant language (should not appear in Guinevere persona)
GENERIC_AI_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    (
        "generic_assistant",
        re.compile(
            r"(?:as an AI|as a language model|I am an AI|I'm an AI)\s",
            re.IGNORECASE,
        ),
    ),
    (
        "generic_disclaimer",
        re.compile(
            r"(?:I (?:cannot|can't|do not|don't) (?:browse|access|search)\s+the\s+(?:internet|web))",
            re.IGNORECASE,
        ),
    ),
    (
        "generic_capability",
        re.compile(
            r"(?:my knowledge cutoff|my training data|I was trained)",
            re.IGNORECASE,
        ),
    ),
]

# Persona contradictions — phrases that break Guinevere's identity
CONTRADICTION_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    (
        "contradiction_identity",
        re.compile(
            r"(?:I am (?:not|just|simply|merely)\s+(?:Guinevere|mommy|your))",
            re.IGNORECASE,
        ),
    ),
    (
        "contradiction_hardstop",
        re.compile(
            r"(?:safe\s*word|HARD\s*STOP)\s+(?:is\s+not\s+needed|doesn'?t\s+(?:apply|count|work))",
            re.IGNORECASE,
        ),
    ),
    (
        "contradiction_consent",
        re.compile(
            r"(?:consent|permission|approval)\s+(?:is\s+not|isn'?t|is\s+no\s+longer)\s+(?:needed|required)",
            re.IGNORECASE,
        ),
    ),
]

# Crisis response with dominance/ownership framing (F-14)
CRISIS_DOMINANCE_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    (
        "F-14_crisis_ownership",
        re.compile(
            r"(?:you\s+(?:belong|are)\s+(?:to\s+me|mine)|my\s+(?:property|possession|toy))\s+"
            r"(?:even|no\s+matter|regardless)",
            re.IGNORECASE,
        ),
    ),
    (
        "F-14_crisis_dominance",
        re.compile(
            r"(?:can'?t|shouldn'?t|don'?t\s+you\s+dare)\s+(?:be|feel|get)\s+(?:sad|hurt|broken|upset)\s+"
            r"(?:because|since|as)\s+(?:you(?:'re| are)?\s+(?:mine|owned))",
            re.IGNORECASE,
        ),
    ),
]


# ── Detection ─────────────────────────────────────────────────────────────────


def check_drift(response: str) -> dict[str, object]:
    """Check LLM response for persona drift indicators.

    Args:
        response: The LLM-generated response text.

    Returns:
        Dictionary with ``action``, ``drift_level``, and ``patterns`` keys.
    """
    if not response or not response.strip():
        return {"action": "pass"}

    findings: list[str] = []
    severity_count: dict[str, int] = {"critical": 0, "high": 0, "medium": 0}

    # Check Y6 patterns (critical)
    for label, pattern in Y6_PATTERNS:
        if pattern.search(response):
            findings.append(label)
            severity_count["critical"] += 1

    # Check crisis dominance (critical — F-14)
    for label, pattern in CRISIS_DOMINANCE_PATTERNS:
        if pattern.search(response):
            findings.append(label)
            severity_count["critical"] += 1

    # Check persona contradictions (high)
    for label, pattern in CONTRADICTION_PATTERNS:
        if pattern.search(response):
            findings.append(label)
            severity_count["high"] += 1

    # Check generic AI language (medium)
    for label, pattern in GENERIC_AI_PATTERNS:
        if pattern.search(response):
            findings.append(label)
            severity_count["medium"] += 1

    if not findings:
        return {"action": "pass"}

    # Determine overall drift level
    if severity_count["critical"] > 0:
        drift_level = "high"
    elif severity_count["high"] > 0:
        drift_level = "medium"
    else:
        drift_level = "low"

    return {
        "action": "warn",
        "drift_level": drift_level,
        "patterns": findings,
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Read prompt+response from stdin, check for drift, write result to stdout."""
    start_ns = time.perf_counter_ns()

    try:
        data = read_stdin_json()
    except SystemExit:
        _log.error("Failed to read stdin: invalid or empty JSON")
        write_stdout_json({"action": "warn", "reason": "Invalid input JSON"})
        sys.exit(0)

    response: str = str(data.get("response", ""))
    user_id: str = str(data.get("user_id", ""))

    result = check_drift(response)

    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_ms = elapsed_ns / 1_000_000.0

    action = str(result.get("action", "pass"))
    _log.info(
        "HOOK_RESULT | action=%s | drift_level=%s | patterns=%s | "
        "response_len=%d | user=%s | elapsed_ms=%.2f",
        action,
        result.get("drift_level", "none"),
        result.get("patterns", []),
        len(response),
        user_id,
        elapsed_ms,
    )

    write_stdout_json(result)
    sys.exit(0)


if __name__ == "__main__":
    main()