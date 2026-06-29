"""Memory layer definitions and access policies for the encrypted provider.

4-layer memory model:
  S4_PRIVATE        — AES-GCM-256 + Argon2id, Faiz-inaccessible
  S3_SHARED_WORLD   — RLS-only, authorized agents can read
  S7_RELATIONSHIP   — AES-GCM-256 for sensitive fields, per-consent-token
  CONVERSATION      — RLS + DNR guard, session-scoped
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Tuple


class MemoryLayer(str, Enum):
    """Classification layers for memory entries.

    Each layer has an associated encryption policy and principal access set.
    S4 is the only layer where the human operator (Faiz) is excluded.
    """

    S4_PRIVATE = "s4_private"
    S3_SHARED_WORLD = "s3_shared_world"
    S7_RELATIONSHIP = "s7_relationship"
    CONVERSATION = "conversation"


# Type alias for access policy entries: (principal, can_read, can_write)
AccessRule = Tuple[str, bool, bool]

# Layer access policies: who can read/write each layer.
# Principal names match the app role conventions in the existing codebase.
LAYER_ACCESS_POLICIES: dict[MemoryLayer, Tuple[AccessRule, ...]] = {
    MemoryLayer.S4_PRIVATE: (
        ("guinevere_core", True, True),      # agent principal — full access
        # Faiz (human operator) has NO access — the whole point of S4.
        # Subagents have NO access — S4 is agent-private.
    ),
    MemoryLayer.S3_SHARED_WORLD: (
        ("guinevere_core", True, True),       # agent principal — full access
        ("subagent", True, False),            # subagents can read, not write
    ),
    MemoryLayer.S7_RELATIONSHIP: (
        ("guinevere_core", True, True),       # agent principal — full access
        ("relationship_peer", True, False),   # relationship peer can read
    ),
    MemoryLayer.CONVERSATION: (
        ("guinevere_core", True, True),       # agent principal — full access
        ("subagent", True, False),            # subagents can read context
    ),
}


def is_encrypted_layer(layer: MemoryLayer) -> bool:
    """Return True if the layer requires field-level AES-GCM-256 encryption."""
    return layer in (MemoryLayer.S4_PRIVATE, MemoryLayer.S7_RELATIONSHIP)


def can_principal_read(layer: MemoryLayer, principal: str) -> bool:
    """Check if a principal has read access to a given layer."""
    for p, can_read, _ in LAYER_ACCESS_POLICIES.get(layer, ()):
        if p == principal:
            return can_read
    return False


def can_principal_write(layer: MemoryLayer, principal: str) -> bool:
    """Check if a principal has write access to a given layer."""
    for p, _, can_write in LAYER_ACCESS_POLICIES.get(layer, ()):
        if p == principal:
            return can_write
    return False
