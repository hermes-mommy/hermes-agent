"""Clipboard secret scanner — detect and redact secrets from surveillance events.

Scans clipboard text content for known secret patterns (API keys, tokens,
passwords, private keys, connection strings) and high-entropy strings that
may represent unknown secrets. Detected secrets are replaced with
``[REDACTED]`` while preserving surrounding context.

Design decisions:
- Redact, not drop: clipboard events retain non-secret metadata after redaction.
- Log metadata only: never log actual secret values.
- Shannon entropy >= 4.5 threshold for unknown high-entropy string detection.

Regex patterns sourced from gitleaks, detect-secrets, trufflehog research.
See ``research-reports/P7/secret-scanning-patterns.md``.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Final

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REDACTION_MARKER: Final[str] = "[REDACTED]"
ENTROPY_THRESHOLD: Final[float] = 4.5
MIN_ENTROPY_STRING_LENGTH: Final[int] = 32

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SecretPattern:
    """A named regex pattern for detecting a specific secret type."""

    name: str
    pattern: re.Pattern[str]
    description: str


@dataclass(frozen=True)
class ScanResult:
    """Result of scanning text for secrets.

    Attributes:
        has_secrets: Whether any secrets were detected.
        secret_types: List of secret type names that were found.
        redacted_text: Text with all detected secrets replaced by [REDACTED].
        secrets_found: Total number of secret occurrences detected.
    """

    has_secrets: bool
    secret_types: list[str] = field(default_factory=list)
    redacted_text: str = ""
    secrets_found: int = 0


# ---------------------------------------------------------------------------
# Compiled patterns — all high-confidence detectors
# ---------------------------------------------------------------------------

PATTERNS: Final[list[SecretPattern]] = [
    SecretPattern(
        name="aws_access_key",
        pattern=re.compile(r"(?<![A-Z0-9])(AKIA[0-9A-Z]{16})(?![A-Z0-9])"),
        description="AWS Access Key ID",
    ),
    SecretPattern(
        name="aws_secret_key",
        pattern=re.compile(
            r"(?i)aws[_\-]?secret[_\-]?(?:access)?[_\-]?key\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"
        ),
        description="AWS Secret Access Key assignment",
    ),
    SecretPattern(
        name="github_pat",
        pattern=re.compile(
            r"(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59})"
        ),
        description="GitHub Personal Access Token",
    ),
    SecretPattern(
        name="github_oauth",
        pattern=re.compile(r"gho_[A-Za-z0-9]{36}"),
        description="GitHub OAuth token",
    ),
    SecretPattern(
        name="openai_api_key",
        pattern=re.compile(r"sk-[a-zA-Z0-9]{48}"),
        description="OpenAI API Key",
    ),
    SecretPattern(
        name="generic_api_key",
        pattern=re.compile(
            r"(?i)(api[_\-]?key|apikey|api[_\-]?secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,64})['\"]?"
        ),
        description="Generic API key assignment",
    ),
    SecretPattern(
        name="bearer_token",
        pattern=re.compile(r"(?i)bearer\s+([A-Za-z0-9_\-\.]{20,512})"),
        description="Bearer token in Authorization header",
    ),
    SecretPattern(
        name="jwt",
        pattern=re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
        description="JSON Web Token",
    ),
    SecretPattern(
        name="pem_key",
        pattern=re.compile(
            r"-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"
        ),
        description="PEM Private Key header",
    ),
    SecretPattern(
        name="db_connection",
        pattern=re.compile(r"(postgresql|postgres|mysql|mongodb|redis)://[^\s'\"]+"),
        description="Database connection string",
    ),
    SecretPattern(
        name="discord_token",
        pattern=re.compile(r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27,}"),
        description="Discord Bot Token",
    ),
    SecretPattern(
        name="slack_token",
        pattern=re.compile(
            r"xox[bpors]-[0-9]{10,13}-[0-9]{10,13}-[0-9]{10,13}-[a-f0-9]{32}"
        ),
        description="Slack API Token",
    ),
    SecretPattern(
        name="stripe_key",
        pattern=re.compile(r"sk_(live|test)_[A-Za-z0-9]{24,}"),
        description="Stripe API Key",
    ),
    SecretPattern(
        name="google_api_key",
        pattern=re.compile(r"AIza[0-9A-Za-z_-]{35}"),
        description="Google API Key",
    ),
    SecretPattern(
        name="age_key",
        pattern=re.compile(r"AGE-SECRET-KEY-1[A-Z0-9]{58}"),
        description="age secret key",
    ),
    SecretPattern(
        name="password_url",
        pattern=re.compile(r"://[^:]+:([^\s@]+)@"),
        description="Password embedded in URL",
    ),
    SecretPattern(
        name="password_assignment",
        pattern=re.compile(
            r"(?i)(password|passwd|pwd|pass)\s*[:=]\s*['\"]([^\s'\"]{8,})['\"]"
        ),
        description="Password assignment in code",
    ),
]

# ---------------------------------------------------------------------------
# High-entropy string pattern (medium-confidence, needs entropy check)
# ---------------------------------------------------------------------------

_HIGH_ENTROPY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z0-9_\-/+=]{32,}(?![A-Za-z0-9])"
)

# ---------------------------------------------------------------------------
# Whitelist patterns — known safe strings excluded from entropy check
# ---------------------------------------------------------------------------

_WHITELIST_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"^[a-fA-F0-9]{32,64}$"),  # MD5/SHA hashes
    re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
    ),  # UUIDs
    re.compile(r"^data:image/[a-z]+;base64,"),  # Base64 image headers
]

# ---------------------------------------------------------------------------
# Shannon entropy
# ---------------------------------------------------------------------------


def shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string.

    Returns a value >= 0.0. Values >= 4.5 typically indicate
    high-entropy data such as encoded secrets or random tokens.
    """
    if not data:
        return 0.0
    counter = Counter(data)
    length = len(data)
    return -sum(
        (count / length) * math.log2(count / length) for count in counter.values()
    )


def _is_whitelisted(text: str) -> bool:
    """Check if a string matches known safe patterns (hashes, UUIDs, etc.)."""
    for pattern in _WHITELIST_PATTERNS:
        if pattern.match(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Core scanning functions
# ---------------------------------------------------------------------------


def scan_text(text: str) -> ScanResult:
    """Scan text for secrets and return a detailed result.

    Checks all compiled regex patterns first, then falls back to
    high-entropy string detection with Shannon entropy >= 4.5.

    Args:
        text: The text to scan for secrets.

    Returns:
        ScanResult with has_secrets, secret_types, redacted_text, and
        secrets_found count.
    """
    if not text:
        logger.info("secret_scan_empty_text")
        return ScanResult(has_secrets=False, secret_types=[], redacted_text="", secrets_found=0)

    secret_types: list[str] = []
    total_secrets = 0
    redacted = text

    # Phase 1: high-confidence pattern matching
    for secret_pattern in PATTERNS:
        matches = secret_pattern.pattern.findall(redacted)
        if matches:
            count = len(matches)
            total_secrets += count
            secret_types.append(secret_pattern.name)
            redacted = secret_pattern.pattern.sub(REDACTION_MARKER, redacted)
            logger.info(
                "secret_detected",
                secret_type=secret_pattern.name,
                count=count,
                text_length=len(text),
            )

    # Phase 2: high-entropy string detection (medium-confidence)
    entropy_matches = _HIGH_ENTROPY_PATTERN.findall(redacted)
    for match_str in entropy_matches:
        if match_str == REDACTION_MARKER:
            continue
        if len(match_str) < MIN_ENTROPY_STRING_LENGTH:
            continue
        if _is_whitelisted(match_str):
            continue
        entropy = shannon_entropy(match_str)
        if entropy >= ENTROPY_THRESHOLD:
            total_secrets += 1
            if "high_entropy" not in secret_types:
                secret_types.append("high_entropy")
            redacted = redacted.replace(match_str, REDACTION_MARKER, 1)
            logger.info(
                "secret_detected",
                secret_type="high_entropy",
                entropy=round(entropy, 2),
                string_length=len(match_str),
                text_length=len(text),
            )

    has_secrets = total_secrets > 0
    if has_secrets:
        logger.info(
            "secret_scan_complete",
            secrets_found=total_secrets,
            secret_types=secret_types,
            text_length=len(text),
        )
    else:
        logger.info("secret_scan_clean", text_length=len(text))

    return ScanResult(
        has_secrets=has_secrets,
        secret_types=secret_types,
        redacted_text=redacted,
        secrets_found=total_secrets,
    )


def redact_secrets(text: str) -> str:
    """Return text with all detected secrets replaced by [REDACTED].

    Convenience wrapper around scan_text that returns only the redacted text.

    Args:
        text: The text to redact secrets from.

    Returns:
        Text with secrets replaced by [REDACTED]. Original text is returned
        unchanged if no secrets are detected.
    """
    if not text:
        return text
    result = scan_text(text)
    return result.redacted_text
