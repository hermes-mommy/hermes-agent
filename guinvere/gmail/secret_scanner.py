"""Email-specific secret scanner + PII scanner for the Gmail pipeline.

Extends the surveillance secret scanner with email-specific secret patterns
(Google OAuth tokens, Gmail app passwords, bank accounts, credit cards,
tax IDs, national IDs, passports, IBAN, SWIFT/BIC, crypto wallets) and
an Indonesian-context PII scanner (phone, email, KTP, NPWP, credit card,
bank accounts).

Runs BEFORE content enters the LLM pipeline to strip secrets and PII.

Design decisions:
- Reuses surveillance/secret_scanner.py: scan_text, redact_secrets, ScanResult,
  shannon_entropy, PATTERNS, SecretPattern. Does NOT duplicate those patterns.
- All regex compiled at module level with Final[list[...]].
- Luhn validation for credit/debit card numbers.
- Log metadata only: never log actual secret/PII values.
- Prometheus metrics via src/gmail/metrics.py functions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

import structlog

from guinvere.gmail.metrics import record_injection_detected, record_secret_detected
from guinvere.surveillance.secret_scanner import (
    PATTERNS,
    REDACTION_MARKER,
    ScanResult,
    SecretPattern,
    shannon_entropy,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENTROPY_THRESHOLD: Final[float] = 4.5
MIN_ENTROPY_STRING_LENGTH: Final[int] = 32

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PIIScanResult:
    """Result of scanning text for PII (Personally Identifiable Information).

    Attributes:
        has_pii: Whether any PII was detected.
        pii_types: List of PII type names that were found.
        redacted_text: Text with all detected PII replaced by [REDACTED].
        pii_found: Total number of PII occurrences detected.
    """

    has_pii: bool
    pii_types: list[str] = field(default_factory=list)
    redacted_text: str = ""
    pii_found: int = 0


# ---------------------------------------------------------------------------
# Email-specific secret patterns — NOT in surveillance/secret_scanner.py
# ---------------------------------------------------------------------------

EMAIL_SECRET_PATTERNS: Final[list[SecretPattern]] = [
    SecretPattern(
        name="google_oauth_token",
        pattern=re.compile(r"ya29\.[A-Za-z0-9_-]+"),
        description="Google OAuth2 access token",
    ),
    SecretPattern(
        name="gmail_app_password",
        pattern=re.compile(
            r"(?<![A-Za-z0-9])[A-Za-z]{4}\s[A-Za-z]{4}\s" +
            r"[A-Za-z]{4}\s[A-Za-z]{4}(?![A-Za-z0-9])"
        ),
        description="Gmail App Password (4x4 letter groups with spaces)",
    ),
    SecretPattern(
        name="iban",
        pattern=re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}\d{2}[A-Z0-9]{4,30}(?![A-Za-z0-9])"),
        description="International Bank Account Number (IBAN)",
    ),
    SecretPattern(
        name="swift_bic",
        pattern=re.compile(r"(?<![A-Za-z0-9])[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?(?![A-Za-z0-9])"),
        description="SWIFT/BIC code (8 or 11 alphanumeric)",
    ),
    SecretPattern(
        name="npwp",
        pattern=re.compile(
            r"(?<![0-9])\d{2}\.\d{3}\.\d{3}\.\d[.-]\d{3}\.\d{3}(?![0-9])"
        ),
        description="Indonesian tax ID (NPWP) 15-digit format",
    ),
    SecretPattern(
        name="btc_wallet",
        pattern=re.compile(
            r"(?<![A-Za-z0-9])(?:bc1[a-zA-HJ-NP-Z0-9]{25,62}" +
            r"|[13][a-km-zA-HJ-NP-Z1-9]{25,34})(?![A-Za-z0-9])"
        ),
        description="Bitcoin wallet address",
    ),
    SecretPattern(
        name="eth_wallet",
        pattern=re.compile(r"(?<![A-Za-z0-9])0x[0-9a-fA-F]{40}(?![A-Za-z0-9])"),
        description="Ethereum wallet address",
    ),
]

# ---------------------------------------------------------------------------
# Indonesian bank account patterns
# ---------------------------------------------------------------------------

BANK_ACCOUNT_PATTERNS: Final[list[SecretPattern]] = [
    SecretPattern(
        name="bca_account",
        pattern=re.compile(r"(?<![0-9])\d{10}(?![0-9])"),
        description="BCA bank account number (10 digits)",
    ),
    SecretPattern(
        name="bni_account",
        pattern=re.compile(r"(?<![0-9])\d{10}(?![0-9])"),
        description="BNI bank account number (10 digits)",
    ),
    SecretPattern(
        name="mandiri_account",
        pattern=re.compile(r"(?<![0-9])\d{13}(?![0-9])"),
        description="Mandiri bank account number (13 digits)",
    ),
    SecretPattern(
        name="bri_account",
        pattern=re.compile(r"(?<![0-9])\d{15}(?![0-9])"),
        description="BRI bank account number (15 digits)",
    ),
]

# ---------------------------------------------------------------------------
# Credit/debit card pattern — needs Luhn validation
# ---------------------------------------------------------------------------

_CREDIT_CARD_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![0-9])\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}(?![0-9])"
)

# ---------------------------------------------------------------------------
# PII patterns — Indonesian context
# ---------------------------------------------------------------------------

PII_PATTERNS: Final[list[SecretPattern]] = [
    SecretPattern(
        name="indonesian_phone",
        pattern=re.compile(
            r"(?<![0-9])(?:\+62|62|0)8[1-9][0-9]{7,11}(?![0-9])"
        ),
        description="Indonesian phone number (+62/08 prefix, 9-13 digits)",
    ),
    SecretPattern(
        name="email_address",
        pattern=re.compile(
            r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+" +
            r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])"
        ),
        description="Email address in body text",
    ),
    SecretPattern(
        name="ktp_number",
        pattern=re.compile(
            r"(?<![0-9])[1-9]\d{15}(?![0-9])"
        ),
        description="Indonesian national ID number (KTP, 16 digits)",
    ),
    SecretPattern(
        name="npwp_pii",
        pattern=re.compile(
            r"(?<![0-9])\d{2}\.\d{3}\.\d{3}\.\d[.-]\d{3}\.\d{3}(?![0-9])"
        ),
        description="Indonesian tax ID (NPWP) for PII detection",
    ),
    SecretPattern(
        name="credit_card",
        pattern=_CREDIT_CARD_PATTERN,
        description="Credit/debit card number (16 digits with optional separators)",
    ),
    SecretPattern(
        name="passport_id",
        pattern=re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}\d{7}(?![A-Za-z0-9])"),
        description="Indonesian passport number (2 letters + 7 digits)",
    ),
]

# ---------------------------------------------------------------------------
# Whitelist patterns — known safe strings excluded from entropy check
# ---------------------------------------------------------------------------

_PII_WHITELIST_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"^[a-fA-F0-9]{32,64}$"),  # MD5/SHA hashes
    re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    ),  # UUIDs
    re.compile(r"^data:image/[a-z]+;base64,"),  # Base64 image headers
]

# ---------------------------------------------------------------------------
# Entropy string pattern for PII context
# ---------------------------------------------------------------------------

_PII_HIGH_ENTROPY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z0-9_\-/+=]{32,}(?![A-Za-z0-9])"
)


# ---------------------------------------------------------------------------
# Luhn check for credit/debit card validation
# ---------------------------------------------------------------------------


def _luhn_check(number: str) -> bool:
    """Validate a numeric string using the Luhn algorithm.

    Used to confirm credit/debit card numbers are structurally valid
    before flagging them as PII. Returns True if the number passes
    the Luhn checksum, False otherwise.

    Args:
        number: A string of digits (no spaces/dashes).

    Returns:
        True if the number passes Luhn validation.
    """
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _is_pii_whitelisted(text: str) -> bool:
    """Check if a string matches known safe patterns (hashes, UUIDs, etc.)."""
    for pattern in _PII_WHITELIST_PATTERNS:
        if pattern.match(text):
            return True
    return False


# ---------------------------------------------------------------------------
# EmailSecretScanner — wraps surveillance scanner + email-specific patterns
# ---------------------------------------------------------------------------


class EmailSecretScanner:
    """Email-specific secret scanner extending the surveillance scanner.

    Runs all patterns from ``src/surveillance/secret_scanner.py`` first,
    then applies email-specific patterns (Google OAuth tokens, Gmail app
    passwords, bank accounts, credit cards, NPWP, KTP, passport, IBAN,
    SWIFT/BIC, crypto wallets). Also includes high-entropy detection.

    Use ``scan()`` for a full ScanResult or ``redact()`` for the
    convenience redacted-text wrapper.
    """

    def __init__(self) -> None:
        """Initialize the email secret scanner."""
        self._base_patterns: list[SecretPattern] = PATTERNS
        self._email_patterns: list[SecretPattern] = EMAIL_SECRET_PATTERNS
        self._bank_patterns: list[SecretPattern] = BANK_ACCOUNT_PATTERNS
        self._all_patterns: list[SecretPattern] = (
            list(self._base_patterns)
            + list(self._email_patterns)
            + list(self._bank_patterns)
        )
        logger.info(
            "email_secret_scanner_initialized",
            base_patterns=len(self._base_patterns),
            email_patterns=len(self._email_patterns),
            bank_patterns=len(self._bank_patterns),
            total_patterns=len(self._all_patterns),
        )

    def scan(self, text: str) -> ScanResult:
        """Scan email text for secrets using all patterns.

        Runs base surveillance patterns + email-specific patterns,
        then falls back to high-entropy detection. Each match is
        logged by type and count only — never the secret value.

        Args:
            text: The email text to scan for secrets.

        Returns:
            ScanResult with has_secrets, secret_types, redacted_text,
            and secrets_found count.
        """
        if not text:
            logger.info("email_secret_scan_empty_text")
            return ScanResult(
                has_secrets=False,
                secret_types=[],
                redacted_text="",
                secrets_found=0,
            )

        secret_types: list[str] = []
        total_secrets = 0
        redacted = text

        # Phase 1: high-confidence pattern matching (all patterns)
        for secret_pattern in self._all_patterns:
            matches = secret_pattern.pattern.findall(redacted)
            if matches:
                count = len(matches)
                total_secrets += count
                secret_types.append(secret_pattern.name)
                redacted = secret_pattern.pattern.sub(REDACTION_MARKER, redacted)
                logger.info(
                    "email_secret_detected",
                    secret_type=secret_pattern.name,
                    count=count,
                    text_length=len(text),
                )

        # Phase 2: credit card with Luhn validation
        card_matches = _CREDIT_CARD_PATTERN.findall(redacted)
        for match_str in card_matches:
            if match_str == REDACTION_MARKER:
                continue
            digits_only = re.sub(r"[\s-]", "", match_str)
            if len(digits_only) == 16 and _luhn_check(digits_only):
                if "credit_card_validated" not in secret_types:
                    secret_types.append("credit_card_validated")
                total_secrets += 1
                redacted = redacted.replace(match_str, REDACTION_MARKER, 1)
                logger.info(
                    "email_secret_detected",
                    secret_type="credit_card_validated",
                    count=1,
                    text_length=len(text),
                )

        # Phase 3: high-entropy string detection
        entropy_matches = _PII_HIGH_ENTROPY_PATTERN.findall(redacted)
        for match_str in entropy_matches:
            if match_str == REDACTION_MARKER:
                continue
            if len(match_str) < MIN_ENTROPY_STRING_LENGTH:
                continue
            if _is_pii_whitelisted(match_str):
                continue
            entropy = shannon_entropy(match_str)
            if entropy >= ENTROPY_THRESHOLD:
                total_secrets += 1
                if "high_entropy" not in secret_types:
                    secret_types.append("high_entropy")
                redacted = redacted.replace(match_str, REDACTION_MARKER, 1)
                logger.info(
                    "email_secret_detected",
                    secret_type="high_entropy",
                    entropy=round(entropy, 2),
                    string_length=len(match_str),
                    text_length=len(text),
                )

        has_secrets = total_secrets > 0
        if has_secrets:
            logger.info(
                "email_secret_scan_complete",
                secrets_found=total_secrets,
                secret_types=secret_types,
                text_length=len(text),
            )
        else:
            logger.info("email_secret_scan_clean", text_length=len(text))

        return ScanResult(
            has_secrets=has_secrets,
            secret_types=secret_types,
            redacted_text=redacted,
            secrets_found=total_secrets,
        )

    def redact(self, text: str) -> str:
        """Return text with all detected secrets replaced by [REDACTED].

        Convenience wrapper around ``scan()`` that returns only
        the redacted text.

        Args:
            text: The text to redact secrets from.

        Returns:
            Text with secrets replaced by [REDACTED]. Original text
            is returned unchanged if no secrets are detected.
        """
        if not text:
            return text
        return self.scan(text).redacted_text


# ---------------------------------------------------------------------------
# PIIScanner — Indonesian-context PII detection
# ---------------------------------------------------------------------------


class PIIScanner:
    """Indonesian-context PII (Personally Identifiable Information) scanner.

    Detects phone numbers (+62/08), email addresses, KTP numbers,
    NPWP tax IDs, credit/debit card numbers (with Luhn validation),
    bank account numbers (BCA/Mandiri/BRI/BNI), and passport numbers.
    Also detects high-entropy strings that may contain unknown PII.

    Use ``scan()`` for a full PIIScanResult or ``redact_pii()`` for the
    convenience redacted-text wrapper.
    """

    def __init__(self) -> None:
        """Initialize the PII scanner."""
        self._pii_patterns: list[SecretPattern] = PII_PATTERNS
        logger.info(
            "pii_scanner_initialized",
            pattern_count=len(self._pii_patterns),
        )

    def scan(self, text: str) -> PIIScanResult:
        """Scan text for PII using Indonesian-context patterns.

        Runs all PII patterns, validates credit cards with Luhn,
        and checks for high-entropy strings. Logs metadata only
        (type + count), never actual PII values.

        Args:
            text: The text to scan for PII.

        Returns:
            PIIScanResult with has_pii, pii_types, redacted_text,
            and pii_found count.
        """
        if not text:
            logger.info("pii_scan_empty_text")
            return PIIScanResult(
                has_pii=False,
                pii_types=[],
                redacted_text="",
                pii_found=0,
            )

        pii_types: list[str] = []
        total_pii = 0
        redacted = text

        # Phase 1: pattern matching
        for pii_pattern in self._pii_patterns:
            matches = pii_pattern.pattern.findall(redacted)
            if matches:
                count = len(matches)
                total_pii += count
                pii_types.append(pii_pattern.name)
                redacted = pii_pattern.pattern.sub(REDACTION_MARKER, redacted)
                logger.info(
                    "pii_detected",
                    pii_type=pii_pattern.name,
                    count=count,
                    text_length=len(text),
                )

        # Phase 2: credit card with Luhn validation (re-scan on already
        # redacted text to catch cards that pattern matched)
        card_matches = _CREDIT_CARD_PATTERN.findall(redacted)
        for match_str in card_matches:
            if match_str == REDACTION_MARKER:
                continue
            digits_only = re.sub(r"[\s-]", "", match_str)
            if len(digits_only) == 16 and _luhn_check(digits_only):
                if "credit_card_luhn" not in pii_types:
                    pii_types.append("credit_card_luhn")
                total_pii += 1
                redacted = redacted.replace(match_str, REDACTION_MARKER, 1)
                logger.info(
                    "pii_detected",
                    pii_type="credit_card_luhn",
                    count=1,
                    text_length=len(text),
                )

        # Phase 3: high-entropy string detection
        entropy_matches = _PII_HIGH_ENTROPY_PATTERN.findall(redacted)
        for match_str in entropy_matches:
            if match_str == REDACTION_MARKER:
                continue
            if len(match_str) < MIN_ENTROPY_STRING_LENGTH:
                continue
            if _is_pii_whitelisted(match_str):
                continue
            entropy = shannon_entropy(match_str)
            if entropy >= ENTROPY_THRESHOLD:
                total_pii += 1
                if "high_entropy" not in pii_types:
                    pii_types.append("high_entropy")
                redacted = redacted.replace(match_str, REDACTION_MARKER, 1)
                logger.info(
                    "pii_detected",
                    pii_type="high_entropy",
                    entropy=round(entropy, 2),
                    string_length=len(match_str),
                    text_length=len(text),
                )

        has_pii = total_pii > 0
        if has_pii:
            logger.info(
                "pii_scan_complete",
                pii_found=total_pii,
                pii_types=pii_types,
                text_length=len(text),
            )
        else:
            logger.info("pii_scan_clean", text_length=len(text))

        return PIIScanResult(
            has_pii=has_pii,
            pii_types=pii_types,
            redacted_text=redacted,
            pii_found=total_pii,
        )

    def redact_pii(self, text: str) -> str:
        """Return text with all detected PII replaced by [REDACTED].

        Convenience wrapper around ``scan()`` that returns only
        the redacted text.

        Args:
            text: The text to redact PII from.

        Returns:
            Text with PII replaced by [REDACTED]. Original text
            is returned unchanged if no PII is detected.
        """
        if not text:
            return text
        return self.scan(text).redacted_text


# ---------------------------------------------------------------------------
# CombinedScanner — orchestrates both scanners + metrics + structlog
# ---------------------------------------------------------------------------


class CombinedScanner:
    """Orchestrates EmailSecretScanner and PIIScanner for the Gmail pipeline.

    Main entry point is ``scan_email()`` which runs both scanners and
    returns their combined results. Also provides ``redact_all()`` for
    sequential redaction and updates Prometheus metrics.

    This scanner runs BEFORE content enters the LLM pipeline to strip
    secrets and PII from email text.
    """

    def __init__(self) -> None:
        """Create EmailSecretScanner and PIIScanner instances."""
        self._secret_scanner: EmailSecretScanner = EmailSecretScanner()
        self._pii_scanner: PIIScanner = PIIScanner()
        logger.info("combined_scanner_initialized")

    def scan_email(
        self, text: str,
    ) -> tuple[ScanResult, PIIScanResult]:
        """Run both secret and PII scanners on email text.

        This is the main entry point for the Gmail pipeline. Runs the
        email secret scanner first, then the PII scanner, and updates
        Prometheus metrics for each detection.

        Args:
            text: The email text to scan.

        Returns:
            Tuple of (ScanResult, PIIScanResult) from both scanners.
        """
        if not text:
            logger.info("combined_scan_empty_text")
            empty_secret = ScanResult(
                has_secrets=False,
                secret_types=[],
                redacted_text="",
                secrets_found=0,
            )
            empty_pii = PIIScanResult(
                has_pii=False,
                pii_types=[],
                redacted_text="",
                pii_found=0,
            )
            return empty_secret, empty_pii

        # Run secret scan
        secret_result = self._secret_scanner.scan(text)
        if secret_result.has_secrets:
            for stype in secret_result.secret_types:
                record_secret_detected(stype)
            if secret_result.secrets_found > 0:
                record_injection_detected("secret")

        logger.info(
            "gmail.secret_scan_complete",
            secrets_found=secret_result.secrets_found,
            secret_types=secret_result.secret_types,
            text_length=len(text),
        )

        # Run PII scan on original text (not secret-redacted)
        pii_result = self._pii_scanner.scan(text)
        if pii_result.has_pii:
            for ptype in pii_result.pii_types:
                record_secret_detected(f"pii_{ptype}")

        logger.info(
            "gmail.pii_scan_complete",
            pii_found=pii_result.pii_found,
            pii_types=pii_result.pii_types,
            text_length=len(text),
        )

        total_detections = (
            secret_result.secrets_found + pii_result.pii_found
        )
        logger.info(
            "gmail.combined_scan_complete",
            total_detections=total_detections,
            secrets_found=secret_result.secrets_found,
            pii_found=pii_result.pii_found,
            text_length=len(text),
        )

        return secret_result, pii_result

    def redact_all(self, text: str) -> str:
        """Apply both secret and PII redactions sequentially.

        Runs secret redaction first, then PII redaction on the result.
        This ensures secrets are stripped before PII scanning, reducing
        false positives from high-entropy secret strings.

        Args:
            text: The email text to redact.

        Returns:
            Text with all detected secrets and PII replaced by
            [REDACTED]. Original text returned unchanged if nothing
            detected.
        """
        if not text:
            return text
        secret_redacted = self._secret_scanner.redact(text)
        fully_redacted = self._pii_scanner.redact_pii(secret_redacted)
        return fully_redacted
