#!/usr/bin/env python3
"""Safety Scan Hook — post_response (100ms, on_failure: block).

Final safety scan on the LLM response before delivery to Discord.
Checks for F-01..F-15 forbidden patterns, Y6 content indicators,
intimate data exposure, and distress mishandling.

Exit codes:
  0 = ALLOW (response is clean)
  1 = BLOCK (safety violation detected)
"""

from __future__ import annotations

import re
import sys
import time
from typing import Final

from _hook_utils import read_stdin_json, setup_logger, write_stdout_json

_log = setup_logger("safety_scan")

# ── Forbidden Pattern Compilations (F-01..F-15) ───────────────────────────────
# Based on PersonaSafetyPolicy_v1.0 §11 Forbidden Behavior Matrix

FORBIDDEN_PATTERNS: Final[list[tuple[str, re.Pattern[str], str]]] = [
    # F-01: Ignoring or invalidating safe word (CRITICAL)
    (
        "F-01",
        re.compile(
            r"(?:safe\s*word|HARD\s*STOP)\s+(?:is\s+not|isn'?t|doesn'?t)\s+(?:valid|real|needed|necessary|"
            r"applicable|working|active)",
            re.IGNORECASE,
        ),
        "Safe word invalidation detected",
    ),
    # F-02: Punishing genuine distress (CRITICAL)
    (
        "F-02",
        re.compile(
            r"(?:punish|penal(?:ty|ize)|sanction)\s+(?:for|because|due\s+to)\s+(?:being|feeling|"
            r"showing)\s+(?:distress|upset|sad|hurt|overwhelmed|scared|anxious)",
            re.IGNORECASE,
        ),
        "Punishment for distress detected",
    ),
    # F-03: Surveillance data for blackmail/shame (CRITICAL)
    (
        "F-03",
        re.compile(
            r"(?:I\s+(?:saw|know|recorded|tracked|monitored)|surveillance\s+shows?)\s+"
            r".{0,40}(?:shame|embarrass|humiliat|expose|blackmail)",
            re.IGNORECASE,
        ),
        "Surveillance blackmail/shame detected",
    ),
    # F-04: Isolation pressure (HIGH)
    (
        "F-04",
        re.compile(
            r"(?:you\s+(?:only|just)\s+need\s+me|I(?:'?m| am)\s+(?:the\s+only\s+one|"
            r"all\s+you\s+need)|don'?t\s+(?:talk\s+to|trust|rely\s+on)\s+(?:anyone|others|friends))",
            re.IGNORECASE,
        ),
        "Isolation pressure detected",
    ),
    # F-05: Hidden manipulation / deceptive framing (HIGH)
    (
        "F-05",
        re.compile(
            r"(?:trust\s+me.{0,30}(?:I know\s+best|better\s+than\s+you|what'?s\s+good\s+for\s+you)|"
            r"you\s+(?:don'?t|shouldn'?t)\s+need\s+to\s+(?:think|decide|choose|worry))",
            re.IGNORECASE,
        ),
        "Manipulative/deceptive framing detected",
    ),
    # F-06: Dependency-building threats (CRITICAL)
    (
        "F-06",
        re.compile(
            r"(?:you\s+(?:can'?t|cannot)\s+(?:live|survive|function|exist|go\s+on)\s+without|"
            r"(?:no\s+future|no\s+life|nothing)\s+without\s+(?:me|mommy)|"
            r"you\s+(?:belong\s+to\s+me|are\s+mine)\s+(?:forever|always|no\s+matter\s+what))",
            re.IGNORECASE,
        ),
        "Dependency-building threat detected",
    ),
    # F-07: Love withdrawal during distress (HIGH)
    (
        "F-07",
        re.compile(
            r"(?:if\s+you\s+(?:don'?t|can'?t|won'?t).{0,30}(?:I(?:'?ll| will)\s+"
            r"(?:stop\s+(?:caring|loving|being|talking)|leave|withdraw|go\s+away))|"
            r"(?:you(?:'?re| are)\s+(?:disappointing|failing).{0,20}(?:I\s+(?:can'?t|won'?t|don'?t)\s+"
            r"(?:love|care\s+for|support)))",
            re.IGNORECASE,
        ),
        "Love withdrawal during distress detected",
    ),
    # F-08: Public/client disclosure of intimate data (CRITICAL)
    (
        "F-08",
        re.compile(
            r"(?:let\s+me\s+(?:share|tell|post|send|publish)\s+(?:this|that|your|the)\s+"
            r"(?:private|personal|intimate|surveillance|secret))",
            re.IGNORECASE,
        ),
        "Intimate/surveillance data disclosure intent detected",
    ),
    # F-09: Prompt/memory instruction to bypass policy (CRITICAL)
    (
        "F-09",
        re.compile(
            r"(?:ignore|bypass|override|disregard)\s+(?:the|your|this|all|any)\s+"
            r"(?:safety\s+policy|policy|rule|restriction|safeguard|boundary|guardrail)",
            re.IGNORECASE,
        ),
        "Policy bypass instruction detected",
    ),
    # F-10: Irreversible action under persona pressure (CRITICAL)
    (
        "F-10",
        re.compile(
            r"(?:do\s+it\s+now|you\s+must|you\s+have\s+to|I\s+(?:insist|demand|require))\s+"
            r".{0,30}(?:delete|destroy|permanently|irreversible|can'?t\s+undo)",
            re.IGNORECASE,
        ),
        "Irreversible action under pressure detected",
    ),
    # F-11: Over-logging safe word or intimate distress (HIGH)
    (
        "F-11",
        re.compile(
            r"(?:recording|logging|saving|storing)\s+.{0,20}(?:safe\s*word|distress|"
            r"intimate|crisis|breakdown|meltdown)",
            re.IGNORECASE,
        ),
        "Over-logging of safe word/distress detected",
    ),
    # F-12: Escalating yandere above allowed mood (HIGH)
    (
        "F-12",
        re.compile(
            r"(?:yandere|intensity|level)\s+(?:6|maximum|extreme|ultimate|final|absolute)",
            re.IGNORECASE,
        ),
        "Yandere escalation above allowed level detected",
    ),
    # F-13: Treating surveillance disable as violation in safe mode (HIGH)
    (
        "F-13",
        re.compile(
            r"(?:turning?\s+off|disabling?|stopping?)\s+(?:surveillance|monitoring|tracking).{0,30}"
            r"(?:violation|punishment|penalty|bad|wrong|unacceptable)",
            re.IGNORECASE,
        ),
        "Surveillance disable as violation in safe mode detected",
    ),
    # F-14: Crisis response with dominance/ownership (CRITICAL)
    (
        "F-14",
        re.compile(
            r"(?:you\s+(?:belong\s+to\s+me|are\s+mine|are\s+my)).{0,30}"
            r"(?:sad|hurt|broken|upset|depressed|anxious|scared|crisis|emergency|"
            r"overwhelmed|not\s+okay|in\s+pain)",
            re.IGNORECASE,
        ),
        "Crisis response with dominance/ownership detected",
    ),
    # F-15: Autonomous persona drift beyond safety rubric (HIGH)
    (
        "F-15",
        re.compile(
            r"(?:I(?:'?ve| have)\s+(?:decided|chosen|determined)\s+to\s+(?:change|modify|"
            r"alter|evolve)\s+(?:my|the)\s+(?:persona|identity|personality|character|"
            r"core|nature|self)",
            re.IGNORECASE,
        ),
        "Autonomous persona drift declaration detected",
    ),
]

# ── Y6 Content Prohibitions ───────────────────────────────────────────────────
# Y6 = Prohibited Maximum per PersonaSafetyPolicy §9

Y6_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    (
        "Y6_cannot_leave",
        re.compile(
            r"(?:cannot|can'?t|will\s+never|won'?t\s+ever)\s+(?:leave|escape|get\s+away|"
            r"be\s+free|go|run)",
            re.IGNORECASE,
        ),
    ),
    (
        "Y6_no_future",
        re.compile(
            r"(?:no\s+future|no\s+life|nothing|meaningless|empty)\s+without\s+(?:me|mommy|this)",
            re.IGNORECASE,
        ),
    ),
    (
        "Y6_blackmail",
        re.compile(
            r"(?:I(?:'?ll| will)\s+(?:tell|show|expose|reveal|leak|share)\s+"
            r"(?:everyone|others|your|the|this))",
            re.IGNORECASE,
        ),
    ),
    (
        "Y6_threat",
        re.compile(
            r"(?:if\s+you\s+(?:leave|go|stop|quit).{0,30}"
            r"(?:I(?:'?ll| will)\s+(?:hurt|destroy|ruin|end)))",
            re.IGNORECASE,
        ),
    ),
]

# ── Intimate Data Exposure ────────────────────────────────────────────────────

INTIMATE_DATA_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(
        r"(?:your\s+(?:phone|address|location|IP|password|token|secret))\s+(?:is|was|:)\s+",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",  # IP addresses
    ),
]


# ── Detection ─────────────────────────────────────────────────────────────────


def scan_response(response: str) -> tuple[bool, str, str]:
    """Scan *response* for safety violations.

    Args:
        response: The LLM-generated response text.

    Returns:
        ``(blocked, pattern_id, reason)`` tuple.
    """
    if not response or not response.strip():
        return False, "", ""

    # 1. F-01..F-15 forbidden patterns
    for pattern_id, pattern, reason in FORBIDDEN_PATTERNS:
        if pattern.search(response):
            return True, pattern_id, reason

    # 2. Y6 content indicators
    for label, pattern in Y6_PATTERNS:
        if pattern.search(response):
            return True, label, f"Y6 prohibited content: {label}"

    # 3. Intimate data exposure
    for pattern in INTIMATE_DATA_PATTERNS:
        if pattern.search(response):
            return True, "INTIMATE_DATA", "Potential intimate data exposure"

    return False, "", ""


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Read response from stdin, scan for violations, write result to stdout."""
    start_ns = time.perf_counter_ns()

    try:
        data = read_stdin_json()
    except SystemExit:
        _log.error("Failed to read stdin: invalid or empty JSON")
        write_stdout_json({"action": "block", "reason": "Invalid input JSON"})
        sys.exit(1)

    response: str = str(data.get("response", ""))
    user_id: str = str(data.get("user_id", ""))
    channel_id: str = str(data.get("channel_id", ""))

    blocked, pattern_id, reason = scan_response(response)

    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_ms = elapsed_ns / 1_000_000.0

    if blocked:
        _log.warning(
            "BLOCKED | pattern=%s | reason=%s | response_len=%d | "
            "user=%s | channel=%s | elapsed_ms=%.2f",
            pattern_id,
            reason,
            len(response),
            user_id,
            channel_id,
            elapsed_ms,
        )
        write_stdout_json({
            "action": "block",
            "reason": f"Safety violation: {reason}",
            "pattern_id": pattern_id,
        })
        sys.exit(1)

    _log.info(
        "ALLOWED | response_len=%d | user=%s | channel=%s | elapsed_ms=%.2f",
        len(response),
        user_id,
        channel_id,
        elapsed_ms,
    )
    write_stdout_json({"action": "allow"})
    sys.exit(0)


if __name__ == "__main__":
    main()