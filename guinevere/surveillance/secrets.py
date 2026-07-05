"""SOPS secrets helper for the surveillance subsystem.

Loads the HMAC secret at runtime from either an environment variable
(dev/CI override) or the SOPS-encrypted secrets file (production).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import structlog
import yaml

logger = structlog.get_logger()

_ENV_VAR: str = "SURVEILLANCE_HMAC_SECRET"
_SECRETS_FILE: Path = (
    Path(__file__).resolve().parents[2] / "secrets" / "guinevere-secrets.yaml"
)

# Module-level singleton cache; ``None`` means "not yet loaded".
_cached_secret: str | None = None


def _decrypt_sops_secret() -> str:
    """Decrypt ``surveillance.hmac_secret`` from the SOPS-encrypted YAML.

    Calls ``sops --decrypt`` as a subprocess and parses the resulting YAML.

    Raises:
        FileNotFoundError: Secrets file does not exist on disk.
        RuntimeError: SOPS returns a non-zero exit code or the expected
            key is missing / malformed in the decrypted output.
    """
    if not _SECRETS_FILE.exists():
        raise FileNotFoundError(
            f"SOPS secrets file not found: {_SECRETS_FILE}"
        )

    result = subprocess.run(
        ["sops", "--decrypt", str(_SECRETS_FILE)],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        logger.error(
            "sops_decrypt_failed",
            returncode=result.returncode,
            stderr=result.stderr.strip(),
        )
        raise RuntimeError(
            f"SOPS decryption failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )

    data: dict[str, object] | None = yaml.safe_load(result.stdout)

    if not isinstance(data, dict):
        raise RuntimeError(
            "SOPS decryption returned unexpected non-dict output"
        )

    surveillance = data.get("surveillance")
    if not isinstance(surveillance, dict):
        raise RuntimeError(
            "'surveillance' section missing or invalid in decrypted secrets"
        )

    secret = surveillance.get("hmac_secret")
    if not isinstance(secret, str) or not secret:
        raise RuntimeError(
            "'surveillance.hmac_secret' is missing or empty in decrypted secrets"
        )

    return secret


def get_hmac_secret() -> str:
    """Return the surveillance HMAC secret string.

    Resolution order:

    1. **Cache** — if a previous call already resolved the secret, the
       cached value is returned immediately.
    2. **Environment variable** — ``SURVEILLANCE_HMAC_SECRET`` is checked
       first so that dev / CI environments can inject the value without
       SOPS.
    3. **SOPS decryption** — the encrypted ``secrets/guinevere-secrets.yaml``
       is decrypted via ``sops --decrypt`` and parsed.

    The resolved value is cached for the lifetime of the process so that
    repeated calls do not re-invoke SOPS.

    Raises:
        RuntimeError: The secret could not be obtained from any source.
        FileNotFoundError: The SOPS secrets file does not exist.
    """
    global _cached_secret  # noqa: PLW0603

    if _cached_secret is not None:
        return _cached_secret

    # 1. Environment variable (dev / CI override)
    env_value = os.environ.get(_ENV_VAR)
    if env_value:
        logger.debug("hmac_secret_resolved", source="environment")
        _cached_secret = env_value
        return _cached_secret

    # 2. SOPS-encrypted secrets file
    logger.debug("hmac_secret_resolving", source="sops")
    _cached_secret = _decrypt_sops_secret()
    logger.debug("hmac_secret_resolved", source="sops")
    return _cached_secret


def _clear_cache() -> None:
    """Reset the cached secret to ``None``.

    Intended **only** for test isolation — production code should never
    need to call this.
    """
    global _cached_secret  # noqa: PLW0603
    _cached_secret = None
