"""Guinevere Encrypted Memory — Hermes MemoryProvider plugin.

4-layer encrypted memory with AES-GCM-256 + Argon2id key derivation.
S4 layer is Faiz-inaccessible (encrypted with key the operator doesn't have).
PG RLS with SET LOCAL for agent-scoped data isolation.

Registration entry point::

    from plugins.memory.guinevere_encrypted import register
    register(ctx)
"""

from __future__ import annotations

from guinevere.memory.encrypted_provider import EncryptedMemoryProvider


def register(ctx) -> None:
    """Register the encrypted memory provider with the Hermes plugin system.

    Called by the plugin loader. ctx.register_memory_provider() is the
    standard registration API per Hermes v0.15.2.
    """
    ctx.register_memory_provider(EncryptedMemoryProvider())
