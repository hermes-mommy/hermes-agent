"""Application-level encryption for sensitive wearable health data fields.

Uses Fernet symmetric encryption (cryptography library) to encrypt sensitive
fields (notes, raw_json, device_id) before TimescaleDB insertion, and decrypt
them for display in health reports.

Key management:
  - Primary: WEARABLE_ENCRYPTION_KEY environment variable.
  - Fallback: SOPS-encrypted .env.wearable (loaded via python-dotenv).
  - If missing: generates an ephemeral key with a WARNING (not for production).

Imported by: writer.py (encrypt before insert), cmd_health_report.py (decrypt for display).

Safety: Health data encryption is consent-bound per wearable-health.* scopes.
        Encrypted fields must never appear in logs, Sentry events, or artifacts.
        Decryption failures are logged and reported; strict mode raises.
"""

from __future__ import annotations

import functools
import os
from typing import Literal

from cryptography.fernet import Fernet, InvalidToken
from structlog.stdlib import BoundLogger, get_logger

logger: BoundLogger = get_logger(__name__)

# Sensitive fields that should be encrypted at rest.
SENSITIVE_FIELDS: tuple[str, ...] = ("notes", "raw_json", "device_id")

# Prefix marker for encrypted values to distinguish from plaintext on decrypt.
_ENCRYPTED_PREFIX = "ENC:"

# Env var controlling decrypt behavior on invalid ciphertext.
# "true" -> raise InvalidToken; "false" (default) -> log and return original.
_STRICT_ENV = "WEARABLE_ENCRYPTION_STRICT"

# Sentry log levels accepted by capture_message.
_SentryLevel = Literal["fatal", "critical", "error", "warning", "info", "debug"]


def _try_load_env_wearable() -> None:
    """Attempt to load .env.wearable via python-dotenv if the file exists.

    This is a fallback for when WEARABLE_ENCRYPTION_KEY is not already in the
    environment. The .env.wearable file is expected to be SOPS-decrypted at
    deployment time before the application starts.
    """
    env_path = os.getenv("WEARABLE_ENV_FILE", ".env.wearable")
    if not os.path.isfile(env_path):
        return
    try:
        from dotenv import load_dotenv

        _ = load_dotenv(env_path, override=False)
        logger.debug("env_wearable_loaded", path=env_path)
    except ImportError:
        logger.warning("dotenv_not_available_env_wearable_fallback_skipped")


def _report_to_sentry(message: str, level: _SentryLevel = "warning") -> None:
    """Send a message to Sentry if the SDK is available and initialized.

    Silently skips if sentry_sdk is not installed. This is an optional
    integration path -- structlog remains the primary logging mechanism.
    """
    try:
        import sentry_sdk

        _ = sentry_sdk.capture_message(message, level=level)
    except ImportError:
        logger.debug("sentry_sdk_not_available_skip_report")


def _is_strict_mode() -> bool:
    """Check whether strict decryption mode is enabled via env var."""
    return os.getenv(_STRICT_ENV, "false").lower() in ("true", "1", "yes")


@functools.lru_cache(maxsize=1)
def get_encryption_key() -> bytes:
    """Load the Fernet encryption key from env or .env.wearable.

    Resolution order:
      1. WEARABLE_ENCRYPTION_KEY environment variable.
      2. SOPS-decrypted .env.wearable (loaded via python-dotenv).
      3. Ephemeral generated key (WARNING -- not production-safe).

    The result is cached for the lifetime of the process. If the key changes
    in the environment, the process must be restarted.

    Returns:
        Fernet-compatible key as bytes (URL-safe base64-encoded 32-byte key).
    """
    key = os.getenv("WEARABLE_ENCRYPTION_KEY", "")
    if not key:
        _try_load_env_wearable()
        key = os.getenv("WEARABLE_ENCRYPTION_KEY", "")

    if key:
        logger.info("wearable_encryption_key_loaded", source="env")
        return key.encode("utf-8")

    # No key found -- fail-closed in production unless ALLOW_EPHEMERAL is set.
    allow_ephemeral = os.getenv("WEARABLE_ENV_ALLOW_EPHEMERAL", "").lower() in ("true", "1", "yes")
    if allow_ephemeral:
        ephemeral_key = Fernet.generate_key()
        warning_msg = (
            "WEARABLE_ENCRYPTION_KEY not set; generated ephemeral key. "
            "Previously encrypted data will be unreadable. "
            "Set the key in SOPS-encrypted .env.wearable."
        )
        logger.warning("wearable_encryption_key_missing_generated_ephemeral")
        _report_to_sentry(warning_msg, level="warning")
        return ephemeral_key

    msg = (
        "WEARABLE_ENCRYPTION_KEY is not set and WEARABLE_ENV_ALLOW_EPHEMERAL "
        "is not enabled. Set WEARABLE_ENCRYPTION_KEY in SOPS-encrypted "
        ".env.wearable, or set WEARABLE_ENV_ALLOW_EPHEMERAL=true for "
        "test/dev (not production)."
    )
    raise RuntimeError(msg)


@functools.lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Return a cached Fernet instance using the loaded encryption key."""
    return Fernet(get_encryption_key())


def encrypt_value(value: str) -> str:
    """Encrypt a string value and return a prefixed base64-encoded ciphertext.

    The returned string is prefixed with 'ENC:' so that decrypt_value can
    distinguish encrypted values from plaintext.

    Args:
        value: Plaintext string to encrypt.

    Returns:
        Encrypted string prefixed with 'ENC:' marker.
        Returns empty string if input is empty.
    """
    if not value:
        return ""

    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode("utf-8"))
    return _ENCRYPTED_PREFIX + encrypted.decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a prefixed base64-encoded ciphertext and return plaintext.

    If the value does not have the 'ENC:' prefix, it is returned as-is
    (treated as already-plaintext). If decryption fails (invalid token),
    behavior depends on WEARABLE_ENCRYPTION_STRICT:
      - 'true': raises InvalidToken.
      - 'false' (default): logs error, reports to Sentry, returns original value.

    Args:
        ciphertext: Encrypted string with 'ENC:' prefix, or plaintext.

    Returns:
        Decrypted plaintext string, or original value on failure (non-strict).

    Raises:
        InvalidToken: If strict mode is enabled and decryption fails.
    """
    if not ciphertext:
        return ""

    if not ciphertext.startswith(_ENCRYPTED_PREFIX):
        # Not encrypted -- return as-is.
        return ciphertext

    token = ciphertext[len(_ENCRYPTED_PREFIX):]
    fernet = _get_fernet()

    try:
        decrypted = fernet.decrypt(token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken as exc:
        strict = _is_strict_mode()
        logger.error(
            "wearable_decryption_failed",
            error=str(exc),
            strict_mode=strict,
        )
        _report_to_sentry(
            "Wearable health data decryption failed -- invalid token.",
            level="error",
        )
        if strict:
            raise
        return ciphertext


def encrypt_health_record(
    record: dict[str, object],
    fields: tuple[str, ...] = SENSITIVE_FIELDS,
) -> dict[str, object]:
    """Encrypt sensitive fields in a health record dictionary.

    Only string values are encrypted; non-string values (None, numbers, etc.)
    are left unchanged. Empty strings are skipped. The original dict is not
    modified -- a shallow copy is returned.

    Args:
        record: Health record dictionary.
        fields: Tuple of field names to encrypt. Defaults to SENSITIVE_FIELDS.

    Returns:
        New dict with sensitive string fields encrypted.
    """
    result: dict[str, object] = dict(record)
    for field_name in fields:
        value = result.get(field_name)
        if isinstance(value, str) and value:
            result[field_name] = encrypt_value(value)
    return result


def decrypt_health_record(
    record: dict[str, object],
    fields: tuple[str, ...] = SENSITIVE_FIELDS,
) -> dict[str, object]:
    """Decrypt sensitive fields in a health record dictionary.

    Only values with the 'ENC:' prefix are decrypted; plaintext values are
    left unchanged. The original dict is not modified -- a shallow copy is
    returned.

    Args:
        record: Health record dictionary with potentially encrypted fields.
        fields: Tuple of field names to decrypt. Defaults to SENSITIVE_FIELDS.

    Returns:
        New dict with sensitive fields decrypted where applicable.
    """
    result: dict[str, object] = dict(record)
    for field_name in fields:
        value = result.get(field_name)
        if isinstance(value, str) and value.startswith(_ENCRYPTED_PREFIX):
            result[field_name] = decrypt_value(value)
    return result
