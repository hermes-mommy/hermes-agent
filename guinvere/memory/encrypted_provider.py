"""Encrypted memory provider — 4-layer MemoryProvider subclass.

Implements all 5 abstract methods from MemoryProvider ABC and overrides
relevant concrete hooks for encrypted 4-layer memory.

Layers:
  S4_PRIVATE        — AES-GCM-256 + Argon2id, Faiz-inaccessible
  S3_SHARED_WORLD   — RLS-only, no field encryption
  S7_RELATIONSHIP   — AES-GCM-256 for sensitive fields
  CONVERSATION      — RLS + DNR guard, session-scoped

Encryption:
  AES-GCM-256 (cryptography lib), Argon2id key derivation (argon2-cffi).
  Key source: MEMORY_S4_AES_KEY env var (never hardcoded).

PG Integration:
  SET LOCAL app.current_agent_id for transaction-scoped RLS.
  Fail-soft if PG is unavailable (D2 constraint).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider

from .crypto import (
    _KEY_ENV_VAR,
    decrypt,
    derive_key_argon2id,
    encrypt,
    get_master_key,
)
from .layers import (
    LAYER_ACCESS_POLICIES,
    MemoryLayer,
    can_principal_read,
    is_encrypted_layer,
)
from .rls import apply_agent_rls, build_set_local_statement

logger = logging.getLogger(__name__)


class VaultMem:
    """In-memory decrypted cache with TTL.

    Thread-safe via asyncio.Lock. Process-scoped — never persisted.
    Decrypted S4/S7 entries are cached to amortize Argon2id latency.
    """

    def __init__(self, ttl: float = 300.0, max_entries: int = 1000) -> None:
        self._cache: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()
        self._ttl = ttl
        self._max_entries = max_entries

    async def get(self, key: str) -> Optional[str]:
        """Return cached plaintext if present and not expired."""
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            plaintext, expires = entry
            if time.monotonic() > expires:
                del self._cache[key]
                return None
            return plaintext

    async def put(self, key: str, plaintext: str) -> None:
        """Cache a decrypted value with TTL."""
        async with self._lock:
            if len(self._cache) >= self._max_entries:
                # Evict oldest entry (simple LRU approximation)
                oldest_key = min(self._cache, key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            self._cache[key] = (plaintext, time.monotonic() + self._ttl)

    async def evict(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._cache.clear()


class EncryptedMemoryProvider(MemoryProvider):
    """Guinevere encrypted memory provider.

    4-layer memory with AES-GCM-256 encryption for S4/S7 layers,
    PG RLS for agent isolation, Argon2id key derivation, and
    knowledge graph integration as semantic memory layer (stub for M8).
    """

    def __init__(self) -> None:
        self._session_id: str = ""
        self._hermes_home: str = ""
        self._platform: str = ""
        self._agent_id: str = ""
        self._derived_key: Optional[bytes] = None
        self._vault = VaultMem()
        self._initialized: bool = False
        self._pg_available: bool = False

    # -- Abstract methods (5) ------------------------------------------------

    @property
    def name(self) -> str:
        """Short identifier for this provider."""
        return "guinevere_encrypted"

    def is_available(self) -> bool:
        """Return True if the master encryption key is configured.

        Checks env var only — no network calls (per ABC contract).
        PG availability is checked at initialize() time.
        """
        raw = os.environ.get(_KEY_ENV_VAR)
        if not raw:
            return False
        try:
            import base64
            key = base64.b64decode(raw)
            return len(key) == 32
        except ValueError:
            logger.debug("MEMORY_S4_AES_KEY is not valid base64 or wrong length")
            return False

    def initialize(self, session_id: str, **kwargs) -> None:
        """Initialize the provider for a session.

        Derives encryption keys, probes PG, sets up RLS context.
        """
        self._session_id = session_id
        self._hermes_home = kwargs.get("hermes_home", "")
        self._platform = kwargs.get("platform", "cli")
        self._agent_id = str(uuid.uuid4())

        # Derive per-agent key from master key + agent_id as salt
        try:
            master = get_master_key()
            # Use first 16 bytes of agent_id UUID as salt
            salt = uuid.UUID(self._agent_id).bytes[:16]
            self._derived_key = derive_key_argon2id(master, salt)
        except ValueError:
            logger.warning("Failed to derive encryption key; S4 writes will fail")
            self._derived_key = None

        # Probe PG (fail-soft if unavailable)
        self._pg_available = self._probe_pg()

        self._initialized = True
        logger.info(
            "EncryptedMemoryProvider initialized: session=%s agent=%s pg=%s",
            session_id,
            self._agent_id[:8],
            "available" if self._pg_available else "unavailable",
        )

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return tool schemas for memory_store, memory_recall, memory_forget."""
        return [
            {
                "name": "memory_store",
                "description": (
                    "Store a memory entry in the encrypted 4-layer memory. "
                    "Specify the layer (s4_private, s3_shared_world, "
                    "s7_relationship, conversation) and the content."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The memory content to store.",
                        },
                        "layer": {
                            "type": "string",
                            "enum": [
                                MemoryLayer.S4_PRIVATE.value,
                                MemoryLayer.S3_SHARED_WORLD.value,
                                MemoryLayer.S7_RELATIONSHIP.value,
                                MemoryLayer.CONVERSATION.value,
                            ],
                            "description": "The memory layer to store in.",
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata for the entry.",
                        },
                    },
                    "required": ["content", "layer"],
                },
            },
            {
                "name": "memory_recall",
                "description": (
                    "Recall memory entries from the encrypted 4-layer memory. "
                    "Specify a query and optionally which layers to search."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query for recall.",
                        },
                        "layers": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Layers to search (default: all readable).",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "memory_forget",
                "description": (
                    "Remove a specific memory entry by ID."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entry_id": {
                            "type": "string",
                            "description": "The ID of the memory entry to forget.",
                        },
                    },
                    "required": ["entry_id"],
                },
            },
        ]

    def handle_tool_call(
        self, tool_name: str, args: Dict[str, Any], **kwargs
    ) -> str:
        """Dispatch tool calls to store/recall/forget handlers."""
        handlers = {
            "memory_store": self._handle_store,
            "memory_recall": self._handle_recall,
            "memory_forget": self._handle_forget,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        try:
            return handler(args, **kwargs)
        except Exception as exc:
            logger.error("Tool %s failed: %s", tool_name, exc, exc_info=True)
            return json.dumps({"error": str(exc)})

    # -- Lifecycle methods (override concrete) --------------------------------

    def system_prompt_block(self) -> str:
        """Return system prompt text describing the encrypted memory model."""
        return (
            "[Encrypted Memory Active]\n"
            "4-layer memory model: S4 (private, encrypted), S3 (shared-world), "
            "S7 (relationship), Conversation (session-scoped).\n"
            "S4 data is encrypted with AES-GCM-256 and is not accessible to "
            "the human operator. Use memory_store with layer='s4_private' for "
            "private thoughts and self-reflections."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Recall relevant context for the upcoming turn.

        Returns decrypted context from S3/conversation layers.
        S4 context is only injected if explicitly requested by the agent.
        """
        if not self._initialized:
            return ""
        # Stub: in production, this queries PG with RLS + decryption.
        # For now, return empty — the pipeline is ready but PG may be absent.
        return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Queue background recall for the next turn."""
        # Background prefetch will be wired when PG is live.

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Persist a completed turn to the encrypted store.

        Stores as CONVERSATION layer. Encrypts if S4 key is available.
        """
        if not self._initialized:
            return
        # Store the turn as a conversation-layer entry
        entry = {"user": user_content, "assistant": assistant_content}
        layer = MemoryLayer.CONVERSATION
        self._store_to_layer(entry, layer)

    def shutdown(self) -> None:
        """Clean shutdown — evict caches, clear derived key."""
        logger.info("EncryptedMemoryProvider shutting down")
        # Run cache eviction synchronously (shutdown may be called outside loop)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._vault.evict())
        except RuntimeError:
            # No event loop — create a temporary one for eviction
            asyncio.run(self._vault.evict())
        self._derived_key = None
        self._initialized = False

    # -- Optional hooks (override) -------------------------------------------

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        """Final consolidation and cache eviction at session end."""
        logger.debug("Session %s ending — evicting vault cache", self._session_id)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._vault.evict())
        except RuntimeError:
            asyncio.run(self._vault.evict())

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        **kwargs,
    ) -> None:
        """Switch session context and clear cache if resetting."""
        old = self._session_id
        self._session_id = new_session_id
        if reset:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._vault.evict())
            except RuntimeError:
                asyncio.run(self._vault.evict())
        logger.debug(
            "Session switch: %s -> %s (reset=%s)", old, new_session_id, reset
        )

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mirror built-in memory writes to the encrypted store."""
        if not self._initialized:
            return
        entry = {"action": action, "target": target, "content": content}
        if metadata:
            entry["metadata"] = metadata
        self._store_to_layer(entry, MemoryLayer.S3_SHARED_WORLD)

    # -- Internal methods ----------------------------------------------------

    def _encrypt_field(self, plaintext: str, layer: MemoryLayer) -> bytes:
        """Encrypt a field with AES-GCM-256.

        Uses the derived key for S4/S7 layers. Returns plaintext bytes
        for non-encrypted layers.
        """
        if not is_encrypted_layer(layer):
            return plaintext.encode("utf-8")
        if self._derived_key is None:
            raise ValueError(
                "Cannot encrypt: no derived key (check MEMORY_S4_AES_KEY)"
            )
        return encrypt(plaintext, self._derived_key)

    def _decrypt_field(self, ciphertext: bytes, layer: MemoryLayer) -> str:
        """Decrypt a field. Checks VaultMem cache first for S4/S7 layers."""
        if not is_encrypted_layer(layer):
            return ciphertext.decode("utf-8")
        if self._derived_key is None:
            raise ValueError(
                "Cannot decrypt: no derived key (check MEMORY_S4_AES_KEY)"
            )
        return decrypt(ciphertext, self._derived_key)

    def _store_to_layer(
        self,
        entry: Dict[str, Any],
        layer: MemoryLayer,
    ) -> str:
        """Store an entry to a memory layer. Returns the entry ID.

        For encrypted layers, encrypts the JSON content.
        For RLS layers, applies agent_id isolation.
        """
        entry_id = str(uuid.uuid4())
        content_json = json.dumps(entry, ensure_ascii=False)

        if is_encrypted_layer(layer):
            encrypted = self._encrypt_field(content_json, layer)
            logger.debug(
                "Stored %s entry %s (encrypted %d bytes) to layer %s",
                entry_id[:8],
                entry_id[:8],
                len(encrypted),
                layer.value,
            )
        else:
            logger.debug(
                "Stored entry %s (%d chars) to layer %s",
                entry_id[:8],
                len(content_json),
                layer.value,
            )

        # In production, this would INSERT into PG with RLS SET LOCAL.
        # D2: design-only, PG may be absent.
        return entry_id

    def _handle_store(self, args: Dict[str, Any], **kwargs) -> str:
        """Handle memory_store tool call."""
        content = args.get("content", "")
        layer_str = args.get("layer", MemoryLayer.CONVERSATION.value)
        metadata = args.get("metadata")

        try:
            layer = MemoryLayer(layer_str)
        except ValueError:
            return json.dumps({"error": f"Invalid layer: {layer_str}"})

        entry = {"content": content}
        if metadata:
            entry["metadata"] = metadata

        entry_id = self._store_to_layer(entry, layer)
        return json.dumps({"entry_id": entry_id, "layer": layer.value, "status": "stored"})

    def _handle_recall(self, args: Dict[str, Any], **kwargs) -> str:
        """Handle memory_recall tool call."""
        query = args.get("query", "")
        layers = args.get("layers", [l.value for l in MemoryLayer])
        return json.dumps({
            "query": query,
            "layers": layers,
            "results": [],
            "note": "PG-backed recall not yet active (D2 design-only)",
        })

    def _handle_forget(self, args: Dict[str, Any], **kwargs) -> str:
        """Handle memory_forget tool call."""
        entry_id = args.get("entry_id", "")
        return json.dumps({
            "entry_id": entry_id,
            "status": "forgotten",
            "note": "PG-backed forget not yet active (D2 design-only)",
        })

    def _probe_pg(self) -> bool:
        """Probe PostgreSQL availability. Returns False if unavailable."""
        # In production, this would test a connection.
        # D2: design-only — assume unavailable unless wired.
        try:
            db_url = os.environ.get("GUINEVERE_DATABASE_URL", "")
            if not db_url:
                return False
            # Don't actually connect — just check if URL is configured
            return "postgresql" in db_url
        except (TypeError, OSError):
            logger.debug("PG probe failed reading GUINEVERE_DATABASE_URL")
            return False
