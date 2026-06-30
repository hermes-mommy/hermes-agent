from __future__ import annotations

"""SOPS-backed binary encryption helpers for WhatsApp session artifacts.

This module keeps P11 session persistence narrow:
- encrypt/decrypt opaque session bytes
- resolve the active age recipient from env or ``.sops.yaml``
- never log plaintext session contents
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import structlog
import yaml

logger = structlog.get_logger()

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SOPS_CONFIG_FILE = _REPO_ROOT / ".sops.yaml"
_AGE_RECIPIENT_ENV = "SOPS_AGE_RECIPIENT"


def _load_age_recipient_from_sops_config() -> str:
    if not _SOPS_CONFIG_FILE.exists():
        raise FileNotFoundError(f"SOPS config file not found: {_SOPS_CONFIG_FILE}")

    with _SOPS_CONFIG_FILE.open("r", encoding="utf-8") as fh:
        data: dict[str, Any] | None = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise RuntimeError(".sops.yaml is malformed or empty")

    creation_rules = data.get("creation_rules")
    if not isinstance(creation_rules, list):
        raise RuntimeError(".sops.yaml missing creation_rules list")

    for rule in creation_rules:
        if not isinstance(rule, dict):
            continue
        direct_age = rule.get("age")
        if isinstance(direct_age, str) and direct_age.strip():
            return direct_age.strip()
        key_groups = rule.get("key_groups")
        if isinstance(key_groups, list):
            for group in key_groups:
                if not isinstance(group, dict):
                    continue
                age_values = group.get("age")
                if isinstance(age_values, list):
                    for age_value in age_values:
                        if isinstance(age_value, str) and age_value.strip():
                            return age_value.strip()
                if isinstance(age_values, str) and age_values.strip():
                    return age_values.strip()

    raise RuntimeError("No age recipient found in .sops.yaml")


def resolve_age_recipient() -> str:
    env_value = os.environ.get(_AGE_RECIPIENT_ENV, "").strip()
    if env_value:
        logger.debug("whatsapp_age_recipient_resolved", source="environment")
        return env_value

    recipient = _load_age_recipient_from_sops_config()
    logger.debug("whatsapp_age_recipient_resolved", source="sops_config")
    return recipient


def sops_encrypt_bytes(plaintext: bytes, age_recipient: str | None = None) -> bytes:
    recipient = age_recipient or resolve_age_recipient()

    with tempfile.NamedTemporaryFile(delete=False) as plain_fh:
        plain_path = Path(plain_fh.name)
        plain_fh.write(plaintext)
    cipher_path = plain_path.with_suffix(".enc")

    try:
        result = subprocess.run(
            [
                "sops",
                "--encrypt",
                "--input-type",
                "binary",
                "--output-type",
                "binary",
                "--age",
                recipient,
                "--output",
                str(cipher_path),
                str(plain_path),
            ],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(
                "whatsapp_sops_encrypt_failed",
                returncode=result.returncode,
                stderr=result.stderr.decode(errors="replace").strip(),
            )
            raise RuntimeError(
                "WhatsApp session encryption failed: "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
        return cipher_path.read_bytes()
    finally:
        plain_path.unlink(missing_ok=True)
        cipher_path.unlink(missing_ok=True)


def sops_decrypt_bytes(ciphertext: bytes) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".enc") as cipher_fh:
        cipher_path = Path(cipher_fh.name)
        cipher_fh.write(ciphertext)
    plain_path = cipher_path.with_suffix(".dec")

    try:
        result = subprocess.run(
            [
                "sops",
                "--decrypt",
                "--input-type",
                "binary",
                "--output-type",
                "binary",
                "--output",
                str(plain_path),
                str(cipher_path),
            ],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(
                "whatsapp_sops_decrypt_failed",
                returncode=result.returncode,
                stderr=result.stderr.decode(errors="replace").strip(),
            )
            raise RuntimeError(
                "WhatsApp session decryption failed: "
                f"{result.stderr.decode(errors='replace').strip()}"
            )
        return plain_path.read_bytes()
    finally:
        cipher_path.unlink(missing_ok=True)
        plain_path.unlink(missing_ok=True)
