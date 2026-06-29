"""AES-GCM-256 encryption/decryption with Argon2id key derivation.

Key source: MEMORY_S4_AES_KEY environment variable (base64-encoded 32 bytes).
Never hardcoded — always read from env at call time.

Argon2id parameters (per r05 research):
  - Memory: 64 MiB (65536 KiB)
  - Iterations: 3
  - Parallelism: 4
  - Output: 32 bytes (256-bit key)
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional

from argon2.low_level import Type as Argon2Type
from argon2.low_level import hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# AES-GCM-256 constants
_NONCE_LEN = 12   # 96-bit nonce per NIST SP 800-38D
_KEY_LEN = 32     # 256-bit key
_TAG_LEN = 16     # 128-bit authentication tag (appended by AESGCM)

# Argon2id parameters
_ARGON2_TIME_COST = 3
_ARGON2_MEMORY_COST = 65536   # 64 MiB
_ARGON2_PARALLELISM = 4
_ARGON2_HASH_LEN = 32
_ARGON2_SALT_LEN = 16

# Env var name for the master encryption key
_KEY_ENV_VAR = "MEMORY_S4_AES_KEY"


def get_master_key() -> bytes:
    """Load the master AES-256 key from the environment.

    Expects a base64-encoded 32-byte key in MEMORY_S4_AES_KEY.
    Raises ValueError if missing or wrong length.
    """
    raw = os.environ.get(_KEY_ENV_VAR)
    if not raw:
        raise ValueError(
            f"Environment variable {_KEY_ENV_VAR} is not set. "
            "Generate with: python -c \"import base64, os; "
            "print(base64.b64encode(os.urandom(32)).decode())\""
        )
    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise ValueError(
            f"Environment variable {_KEY_ENV_VAR} is not valid base64: {exc}"
        ) from exc
    if len(key) != _KEY_LEN:
        raise ValueError(
            f"Environment variable {_KEY_ENV_VAR} must decode to {_KEY_LEN} bytes, "
            f"got {len(key)}"
        )
    return key


def encrypt(plaintext: str, key: bytes) -> bytes:
    """Encrypt plaintext with AES-GCM-256.

    Args:
        plaintext: The string to encrypt.
        key: 32-byte AES-256 key.

    Returns:
        bytes: nonce (12) + ciphertext + tag (16).
    """
    if len(key) != _KEY_LEN:
        raise ValueError(f"AES-256 key must be {_KEY_LEN} bytes, got {len(key)}")
    nonce = os.urandom(_NONCE_LEN)
    aesgcm = AESGCM(key)
    # AESGCM.encrypt returns ciphertext + tag appended together
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce + ct


def decrypt(ciphertext: bytes, key: bytes) -> str:
    """Decrypt AES-GCM-256 ciphertext produced by encrypt().

    Args:
        ciphertext: nonce (12) + ciphertext + tag (16).
        key: 32-byte AES-256 key.

    Returns:
        str: The original plaintext.

    Raises:
        ValueError: If the key length is wrong.
        cryptography.exceptions.InvalidTag: If authentication fails.
    """
    if len(key) != _KEY_LEN:
        raise ValueError(f"AES-256 key must be {_KEY_LEN} bytes, got {len(key)}")
    if len(ciphertext) < _NONCE_LEN + _TAG_LEN:
        raise ValueError("Ciphertext too short to contain nonce and tag")
    nonce = ciphertext[:_NONCE_LEN]
    ct_body = ciphertext[_NONCE_LEN:]
    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(nonce, ct_body, None)
    return pt.decode("utf-8")


def derive_key_argon2id(
    master_key: bytes,
    salt: bytes,
    *,
    time_cost: int = _ARGON2_TIME_COST,
    memory_cost: int = _ARGON2_MEMORY_COST,
    parallelism: int = _ARGON2_PARALLELISM,
) -> bytes:
    """Derive a 256-bit key from the master key using Argon2id.

    Args:
        master_key: The secret input (e.g. from get_master_key()).
        salt: 16-byte salt (e.g. derived from agent_id).
        time_cost: Argon2 iterations (default 3).
        memory_cost: Memory in KiB (default 65536 = 64 MiB).
        parallelism: Thread count (default 4).

    Returns:
        bytes: 32-byte derived key.
    """
    if len(salt) < 8:
        raise ValueError("Argon2id salt must be at least 8 bytes")
    return hash_secret_raw(
        secret=master_key,
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory_cost,
        parallelism=parallelism,
        hash_len=_ARGON2_HASH_LEN,
        type=Argon2Type.ID,
    )
