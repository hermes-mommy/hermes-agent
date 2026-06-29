"""Guinevere encrypted memory — 4-layer memory provider.

Public surface:
  EncryptedMemoryProvider — MemoryProvider subclass with AES-GCM-256 encryption.
  MemoryLayer — S4_PRIVATE, S3_SHARED_WORLD, S7_RELATIONSHIP, CONVERSATION.
  encrypt / decrypt — AES-GCM-256 primitives.
  derive_key_argon2id — Argon2id key derivation.
  apply_agent_rls — PG RLS SET LOCAL helper.
"""

from .crypto import decrypt, derive_key_argon2id, encrypt, get_master_key
from .encrypted_provider import EncryptedMemoryProvider
from .layers import (
    LAYER_ACCESS_POLICIES,
    MemoryLayer,
    can_principal_read,
    can_principal_write,
    is_encrypted_layer,
)
from .rls import apply_agent_rls, build_set_local_statement, get_rls_setup_sql

__all__ = [
    "EncryptedMemoryProvider",
    "MemoryLayer",
    "LAYER_ACCESS_POLICIES",
    "encrypt",
    "decrypt",
    "derive_key_argon2id",
    "get_master_key",
    "is_encrypted_layer",
    "can_principal_read",
    "can_principal_write",
    "apply_agent_rls",
    "build_set_local_statement",
    "get_rls_setup_sql",
]
