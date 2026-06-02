"""P7-009: Clipboard secret scanner — comprehensive unit tests.

Tests cover:
- AWS Access Key detection (synthetic pattern)
- GitHub Personal Access Token detection (synthetic pattern)
- OpenAI API Key detection (synthetic pattern)
- JWT token detection
- PEM Private Key header detection
- Database connection string detection
- Discord Bot Token detection
- age secret key detection
- Clean text returns no secrets
- Redaction preserves surrounding text
- Empty text handling
- Multiple secrets in one text
- Shannon entropy calculation
- High-entropy string detection
- Whitelist exclusion (UUIDs, hashes)
- ScanResult dataclass immutability

All fixtures use synthetic/fake patterns — no real secrets.
"""

from __future__ import annotations

import re

import pytest

from src.surveillance.secret_scanner import (
    ENTROPY_THRESHOLD,
    MIN_ENTROPY_STRING_LENGTH,
    PATTERNS,
    REDACTION_MARKER,
    ScanResult,
    SecretPattern,
    redact_secrets,
    scan_text,
    shannon_entropy,
)

# ---------------------------------------------------------------------------
# Synthetic / fake secret fixtures — NEVER use real secrets
# ---------------------------------------------------------------------------

# AWS Access Key ID: AKIA + 16 uppercase alphanumeric
FAKE_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"

# GitHub Personal Access Token: ghp_ + 36 alphanum
FAKE_GITHUB_PAT = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"

# GitHub fine-grained PAT: github_pat_ + 22 alphanum + _ + 59 alphanum
FAKE_GITHUB_FINE_PAT = (
    "github_pat_ABCDEFGHIJKLMNOPQRSTUV"
    "_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456"
)

# OpenAI API Key: sk- + 48 alphanum
FAKE_OPENAI_KEY = "sk-" + "aBcDeFgHiJkLmNoPqRsTuVwXyZaBcDeFgHiJkLmNoPqRsTuV"  # 48 chars after sk-

# JWT: header.payload.signature (base64url segments starting with eyJ)
FAKE_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)

# PEM Private Key header
FAKE_PEM_HEADER = "-----BEGIN RSA PRIVATE KEY-----"

# Database connection strings
FAKE_DB_POSTGRES = "postgresql://testuser:testpass@localhost:5432/testdb"
FAKE_DB_MYSQL = "mysql://admin:secretword@db.example.com:3306/production"
FAKE_DB_MONGO = "mongodb://mongouser:mongopass@mongo.cluster.local:27017/appdb"

# Discord Bot Token: [MN][A-Za-z\d]{23,}.[\w-]{6}.[\w-]{27,}
FAKE_DISCORD_TOKEN = "NTEyMzQ1Njc4OTAxMjM0NTY3ODkw.ABCDEF.GhIjKlMnOpQrStUvWxYzAbCdEfGh"

# age secret key: AGE-SECRET-KEY-1 + 58 uppercase/digits
FAKE_AGE_KEY = "AGE-SECRET-KEY-1QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7LQPZRY9X8GF2TVDW0S3JN54KHCE"

# Password assignment
FAKE_PASSWORD_ASSIGN = 'password = "SuperS3cretPass!"'

# Bearer token
FAKE_BEARER = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.longtokenvalue12345"

# Clean text with no secrets
CLEAN_TEXT = "Hello, this is a normal clipboard copy. Nothing sensitive here."

# High-entropy synthetic string (>= 32 chars, high entropy, not a hash/UUID)
HIGH_ENTROPY_STRING = "kR7mNx2QpW9sL4vT8yB3cF6hJ0dA5eG1iK"

# ---------------------------------------------------------------------------
# Shannon entropy tests
# ---------------------------------------------------------------------------


class TestShannonEntropy:
    """Tests for the shannon_entropy() function."""

    def test_empty_string_returns_zero(self) -> None:
        assert shannon_entropy("") == 0.0

    def test_single_char_returns_zero(self) -> None:
        assert shannon_entropy("a") == 0.0

    def test_uniform_two_chars_is_one(self) -> None:
        """Two equally distributed chars have entropy of exactly 1.0."""
        assert shannon_entropy("ab") == pytest.approx(1.0)

    def test_high_entropy_random_looking_string(self) -> None:
        """A diverse alphanumeric string should have entropy >= 4.5."""
        entropy = shannon_entropy(HIGH_ENTROPY_STRING)
        assert entropy >= ENTROPY_THRESHOLD

    def test_low_entropy_repeated_string(self) -> None:
        """Repeated single character has entropy 0."""
        assert shannon_entropy("a" * 100) == 0.0

    def test_known_entropy_calculation(self) -> None:
        """Verify entropy for 'aabb' = 1.0 (two symbols, equal frequency)."""
        assert shannon_entropy("aabb") == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Pattern compilation tests
# ---------------------------------------------------------------------------


class TestPatterns:
    """Tests for the PATTERNS list and SecretPattern dataclass."""

    def test_patterns_is_non_empty_list(self) -> None:
        assert isinstance(PATTERNS, list)
        assert len(PATTERNS) > 0

    def test_all_patterns_are_secret_pattern_instances(self) -> None:
        for p in PATTERNS:
            assert isinstance(p, SecretPattern)
            assert isinstance(p.name, str) and len(p.name) > 0
            assert isinstance(p.pattern, re.Pattern)
            assert isinstance(p.description, str) and len(p.description) > 0

    def test_secret_pattern_is_frozen(self) -> None:
        p = PATTERNS[0]
        # frozen=True prohibits attribute assignment via __setattr__
        with pytest.raises(AttributeError):
            setattr(p, "name", "changed")


class TestScanResult:
    """Tests for the ScanResult dataclass."""

    def test_scan_result_is_frozen(self) -> None:
        result = ScanResult(has_secrets=False)
        # frozen=True prohibits attribute assignment via __setattr__
        with pytest.raises(AttributeError):
            setattr(result, "has_secrets", True)

    def test_scan_result_defaults(self) -> None:
        result = ScanResult(has_secrets=False)
        assert result.has_secrets is False
        assert result.secret_types == []
        assert result.redacted_text == ""
        assert result.secrets_found == 0

    def test_scan_result_with_values(self) -> None:
        result = ScanResult(
            has_secrets=True,
            secret_types=["aws_access_key"],
            redacted_text="key is [REDACTED]",
            secrets_found=1,
        )
        assert result.has_secrets is True
        assert result.secret_types == ["aws_access_key"]
        assert result.redacted_text == "key is [REDACTED]"
        assert result.secrets_found == 1


# ---------------------------------------------------------------------------
# scan_text — individual secret type detection
# ---------------------------------------------------------------------------


class TestScanTextAWSDetection:
    """AWS Access Key detection tests."""

    def test_detects_aws_access_key(self) -> None:
        text = f"My AWS key is {FAKE_AWS_KEY} for production."
        result = scan_text(text)
        assert result.has_secrets is True
        assert "aws_access_key" in result.secret_types
        assert result.secrets_found >= 1
        assert REDACTION_MARKER in result.redacted_text
        assert FAKE_AWS_KEY not in result.redacted_text

    def test_aws_key_redaction_preserves_surrounding(self) -> None:
        text = f"config: {FAKE_AWS_KEY} end"
        result = scan_text(text)
        assert result.redacted_text.startswith("config: ")
        assert result.redacted_text.endswith(" end")


class TestScanTextGitHubDetection:
    """GitHub Personal Access Token detection tests."""

    def test_detects_github_pat(self) -> None:
        text = f"token: {FAKE_GITHUB_PAT}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "github_pat" in result.secret_types
        assert FAKE_GITHUB_PAT not in result.redacted_text

    def test_detects_github_fine_grained_pat(self) -> None:
        text = f"new token: {FAKE_GITHUB_FINE_PAT}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "github_pat" in result.secret_types


class TestScanTextOpenAIDetection:
    """OpenAI API Key detection tests."""

    def test_detects_openai_key(self) -> None:
        text = f"OPENAI_API_KEY={FAKE_OPENAI_KEY}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "openai_api_key" in result.secret_types
        assert FAKE_OPENAI_KEY not in result.redacted_text

    def test_openai_key_redaction_preserves_prefix(self) -> None:
        text = f"key is {FAKE_OPENAI_KEY} ok"
        result = scan_text(text)
        assert "key is " in result.redacted_text
        assert " ok" in result.redacted_text


class TestScanTextJWTDetection:
    """JWT token detection tests."""

    def test_detects_jwt(self) -> None:
        text = f"Authorization: Bearer {FAKE_JWT}"
        result = scan_text(text)
        assert result.has_secrets is True
        # JWT may be caught by jwt, bearer_token, or both
        assert any(t in result.secret_types for t in ("jwt", "bearer_token"))
        assert FAKE_JWT not in result.redacted_text

    def test_jwt_redaction_replaces_full_token(self) -> None:
        text = f"token={FAKE_JWT}"
        result = scan_text(text)
        assert REDACTION_MARKER in result.redacted_text
        assert "eyJ" not in result.redacted_text


class TestScanTextPEMDetection:
    """PEM Private Key detection tests."""

    def test_detects_pem_rsa_key(self) -> None:
        text = f"{FAKE_PEM_HEADER}\nMIIBogIBAAJBALRiMLAH...\n-----END RSA PRIVATE KEY-----"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "pem_key" in result.secret_types
        assert FAKE_PEM_HEADER not in result.redacted_text

    def test_detects_pem_ec_key(self) -> None:
        text = "-----BEGIN EC PRIVATE KEY-----"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "pem_key" in result.secret_types

    def test_detects_pem_openssh_key(self) -> None:
        text = "-----BEGIN OPENSSH PRIVATE KEY-----"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "pem_key" in result.secret_types

    def test_detects_pem_plain_private_key(self) -> None:
        text = "-----BEGIN PRIVATE KEY-----"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "pem_key" in result.secret_types


class TestScanTextDBConnectionDetection:
    """Database connection string detection tests."""

    def test_detects_postgresql_connection(self) -> None:
        text = f"DATABASE_URL={FAKE_DB_POSTGRES}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "db_connection" in result.secret_types
        assert "postgresql://testuser" not in result.redacted_text

    def test_detects_mysql_connection(self) -> None:
        text = f"conn = {FAKE_DB_MYSQL}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "db_connection" in result.secret_types

    def test_detects_mongodb_connection(self) -> None:
        text = f"MONGO_URI = {FAKE_DB_MONGO}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "db_connection" in result.secret_types


class TestScanTextDiscordDetection:
    """Discord Bot Token detection tests."""

    def test_detects_discord_token(self) -> None:
        text = f"DISCORD_TOKEN={FAKE_DISCORD_TOKEN}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "discord_token" in result.secret_types
        assert FAKE_DISCORD_TOKEN not in result.redacted_text


class TestScanTextAgeDetection:
    """age secret key detection tests."""

    def test_detects_age_key(self) -> None:
        # Construct a valid 58-char key from the bech32 alphabet
        age_key = "AGE-SECRET-KEY-1QPZRY9X8GF2TVDW0S3JN54KHCE6MUA7LQPZRY9X8GF2TVDW0S3JN54KHCE"
        assert len(age_key.replace("AGE-SECRET-KEY-1", "")) == 58
        text = f"my age key: {age_key}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "age_key" in result.secret_types
        assert age_key not in result.redacted_text


class TestScanTextPasswordDetection:
    """Password pattern detection tests."""

    def test_detects_password_assignment(self) -> None:
        text = FAKE_PASSWORD_ASSIGN
        result = scan_text(text)
        assert result.has_secrets is True
        assert "password_assignment" in result.secret_types

    def test_detects_password_in_url(self) -> None:
        text = "connecting to postgresql://admin:hunter2secret@db.local/mydb"
        result = scan_text(text)
        assert result.has_secrets is True
        # db_connection and/or password_url should fire
        assert any(
            t in result.secret_types for t in ("db_connection", "password_url")
        )


class TestScanTextBearerTokenDetection:
    """Bearer token detection tests."""

    def test_detects_bearer_token(self) -> None:
        text = f"Authorization: {FAKE_BEARER}"
        result = scan_text(text)
        assert result.has_secrets is True
        # May match bearer_token and/or jwt
        assert any(t in result.secret_types for t in ("bearer_token", "jwt"))


# ---------------------------------------------------------------------------
# scan_text — clean / empty / edge cases
# ---------------------------------------------------------------------------


class TestScanTextCleanText:
    """Tests for text that should NOT be flagged as containing secrets."""

    def test_clean_text_no_secrets(self) -> None:
        result = scan_text(CLEAN_TEXT)
        assert result.has_secrets is False
        assert result.secret_types == []
        assert result.secrets_found == 0
        assert result.redacted_text == CLEAN_TEXT

    def test_plain_url_no_secrets(self) -> None:
        result = scan_text("Visit https://example.com for more info.")
        assert result.has_secrets is False

    def test_normal_code_no_secrets(self) -> None:
        code = 'def hello():\n    print("Hello, world!")\n    return True'
        result = scan_text(code)
        assert result.has_secrets is False

    def test_uuid_not_flagged(self) -> None:
        text = "ID: 550e8400-e29b-41d4-a716-446655440000"
        result = scan_text(text)
        assert result.has_secrets is False


class TestScanTextEmptyInput:
    """Tests for empty / None-like text handling."""

    def test_empty_string(self) -> None:
        result = scan_text("")
        assert result.has_secrets is False
        assert result.secret_types == []
        assert result.redacted_text == ""
        assert result.secrets_found == 0

    def test_whitespace_only(self) -> None:
        result = scan_text("   \n\t  ")
        assert result.has_secrets is False


# ---------------------------------------------------------------------------
# scan_text — multiple secrets
# ---------------------------------------------------------------------------


class TestScanTextMultipleSecrets:
    """Tests for text containing multiple different secret types."""

    def test_multiple_different_secrets(self) -> None:
        text = (
            f"AWS key: {FAKE_AWS_KEY}\n"
            f"GitHub token: {FAKE_GITHUB_PAT}\n"
            f"DB: {FAKE_DB_POSTGRES}"
        )
        result = scan_text(text)
        assert result.has_secrets is True
        assert result.secrets_found >= 3
        assert "aws_access_key" in result.secret_types
        assert "github_pat" in result.secret_types
        assert "db_connection" in result.secret_types
        # All secrets should be redacted
        assert FAKE_AWS_KEY not in result.redacted_text
        assert FAKE_GITHUB_PAT not in result.redacted_text
        assert "postgresql://testuser" not in result.redacted_text
        # Non-secret content preserved
        assert "AWS key: " in result.redacted_text
        assert "GitHub token: " in result.redacted_text
        assert "DB: " in result.redacted_text

    def test_two_same_type_secrets(self) -> None:
        text = f"key1={FAKE_AWS_KEY} key2=AKIAZ3456789ABCDEFGH"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "aws_access_key" in result.secret_types
        assert result.secrets_found >= 2


# ---------------------------------------------------------------------------
# redact_secrets convenience function
# ---------------------------------------------------------------------------


class TestRedactSecrets:
    """Tests for the redact_secrets() convenience function."""

    def test_redacts_aws_key(self) -> None:
        text = f"key={FAKE_AWS_KEY}"
        result = redact_secrets(text)
        assert FAKE_AWS_KEY not in result
        assert REDACTION_MARKER in result
        assert result.startswith("key=")

    def test_returns_original_when_clean(self) -> None:
        result = redact_secrets(CLEAN_TEXT)
        assert result == CLEAN_TEXT

    def test_empty_string_passthrough(self) -> None:
        result = redact_secrets("")
        assert result == ""

    def test_preserves_surrounding_text(self) -> None:
        text = f"before {FAKE_AWS_KEY} after"
        result = redact_secrets(text)
        assert result == f"before {REDACTION_MARKER} after"

    def test_multiple_redactions_in_one_text(self) -> None:
        text = f"{FAKE_AWS_KEY} and {FAKE_GITHUB_PAT}"
        result = redact_secrets(text)
        assert FAKE_AWS_KEY not in result
        assert FAKE_GITHUB_PAT not in result
        assert result.count(REDACTION_MARKER) >= 2


# ---------------------------------------------------------------------------
# High-entropy string detection
# ---------------------------------------------------------------------------


class TestHighEntropyDetection:
    """Tests for Shannon entropy-based unknown secret detection."""

    def test_high_entropy_string_detected(self) -> None:
        """A high-entropy 36-char string should be detected."""
        # Ensure the string has sufficient entropy
        test_str = "aB3kLm9pQr5tUv2wXy7zC4eF6gH8iJ1kN3o"
        assert len(test_str) >= MIN_ENTROPY_STRING_LENGTH
        entropy = shannon_entropy(test_str)
        assert entropy >= ENTROPY_THRESHOLD
        text = f"token: {test_str}"
        result = scan_text(text)
        assert result.has_secrets is True
        assert "high_entropy" in result.secret_types

    def test_low_entropy_long_string_not_flagged(self) -> None:
        """A long but low-entropy string should NOT be flagged."""
        test_str = "a" * 50  # 50 chars but entropy = 0
        assert shannon_entropy(test_str) < ENTROPY_THRESHOLD
        text = f"value: {test_str}"
        result = scan_text(text)
        # Should not detect high_entropy (may still match other patterns if applicable)
        assert "high_entropy" not in result.secret_types

    def test_short_high_entropy_not_flagged(self) -> None:
        """A high-entropy string shorter than MIN_ENTROPY_STRING_LENGTH is skipped."""
        test_str = "aB3kLm9pQr5"  # Only 12 chars
        assert len(test_str) < MIN_ENTROPY_STRING_LENGTH
        text = f"x {test_str} y"
        result = scan_text(text)
        assert "high_entropy" not in result.secret_types


# ---------------------------------------------------------------------------
# Redaction marker consistency
# ---------------------------------------------------------------------------


class TestRedactionMarker:
    """Tests ensuring the redaction marker is used consistently."""

    def test_redaction_marker_is_redacted(self) -> None:
        assert REDACTION_MARKER == "[REDACTED]"

    def test_no_raw_secrets_in_redacted_output(self) -> None:
        """All known secret types must be replaced in redacted output."""
        secrets_and_texts = [
            (FAKE_AWS_KEY, f"key={FAKE_AWS_KEY}"),
            (FAKE_GITHUB_PAT, f"gh={FAKE_GITHUB_PAT}"),
            (FAKE_OPENAI_KEY, f"openai={FAKE_OPENAI_KEY}"),
            (FAKE_PEM_HEADER, FAKE_PEM_HEADER),
            (FAKE_DB_POSTGRES, f"url={FAKE_DB_POSTGRES}"),
        ]
        for secret, text in secrets_and_texts:
            result = scan_text(text)
            assert secret not in result.redacted_text, (
                f"Secret '{secret[:10]}...' still present in redacted output"
            )
