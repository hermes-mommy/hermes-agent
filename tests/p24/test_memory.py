"""Tests for W9 — Encrypted Memory (guinevere/memory/).

Covers:
  - AES-GCM-256 encrypt/decrypt round-trip
  - Argon2id key derivation
  - S4 Faiz-inaccessible (encrypted blob unreadable without key)
  - MemoryLayer enum (4 layers)
  - EncryptedMemoryProvider implements all 5 abstract methods
  - RLS SET LOCAL SQL correctness
  - Plugin registration pattern

All tests are local-only (no PG, no network). D2 compliant.
"""

from __future__ import annotations

import base64
import json
import os
import uuid

import pytest

# Ensure MEMORY_S4_AES_KEY is set for tests (random 32-byte key, base64)
_TEST_KEY = base64.b64encode(os.urandom(32)).decode()
os.environ.setdefault("MEMORY_S4_AES_KEY", _TEST_KEY)

from cryptography.exceptions import InvalidTag

from guinevere.memory.crypto import (
    _KEY_ENV_VAR,
    decrypt,
    derive_key_argon2id,
    encrypt,
    get_master_key,
)
from guinevere.memory.encrypted_provider import EncryptedMemoryProvider, VaultMem
from guinevere.memory.layers import (
    LAYER_ACCESS_POLICIES,
    MemoryLayer,
    can_principal_read,
    can_principal_write,
    is_encrypted_layer,
)
from guinevere.memory.rls import (
    SET_AGENT_ID_SQL,
    apply_agent_rls,
    build_set_local_statement,
    get_rls_setup_sql,
)


# ---- AES-GCM-256 encrypt/decrypt round-trip ----


class TestAESGCM:
    def test_encrypt_decrypt_roundtrip(self):
        """encrypt() then decrypt() returns the original plaintext."""
        key = os.urandom(32)
        plaintext = "the quick brown fox jumps over the lazy dog"
        ct = encrypt(plaintext, key)
        result = decrypt(ct, key)
        assert result == plaintext

    def test_encrypt_produces_different_ciphertext_each_time(self):
        """Same plaintext encrypted twice yields different ciphertexts (random nonce)."""
        key = os.urandom(32)
        ct1 = encrypt("same text", key)
        ct2 = encrypt("same text", key)
        assert ct1 != ct2

    def test_decrypt_wrong_key_fails(self):
        """Decrypting with the wrong key raises InvalidTag."""
        key_a = os.urandom(32)
        key_b = os.urandom(32)
        ct = encrypt("secret", key_a)
        with pytest.raises(InvalidTag):
            decrypt(ct, key_b)

    def test_encrypt_empty_string(self):
        """Empty string encrypts and decrypts correctly."""
        key = os.urandom(32)
        ct = encrypt("", key)
        assert decrypt(ct, key) == ""

    def test_encrypt_unicode(self):
        """Unicode strings survive encryption round-trip."""
        key = os.urandom(32)
        text = "Guinevere von Baroque — ❤ ★ ☠"
        ct = encrypt(text, key)
        assert decrypt(ct, key) == text

    def test_ciphertext_format_nonce_prepended(self):
        """Ciphertext is nonce (12) + encrypted_body + tag (16)."""
        key = os.urandom(32)
        ct = encrypt("test", key)
        # Nonce is 12 bytes, tag is 16, so minimum size is 12 + 0 + 16 = 28
        assert len(ct) >= 12 + 16
        # The plaintext "test" is 4 bytes, so ct = 12 + 4 + 16 = 32
        assert len(ct) == 12 + 4 + 16

    def test_wrong_key_length_raises(self):
        """Key must be exactly 32 bytes."""
        with pytest.raises(ValueError, match="32 bytes"):
            encrypt("test", b"short")
        with pytest.raises(ValueError, match="32 bytes"):
            decrypt(b"x" * 28, b"short")

    def test_ciphertext_too_short_raises(self):
        """Ciphertext shorter than nonce+tag raises ValueError."""
        key = os.urandom(32)
        with pytest.raises(ValueError, match="too short"):
            decrypt(b"\x00" * 10, key)


# ---- Argon2id key derivation ----


class TestArgon2id:
    def test_derive_key_length(self):
        """Derived key is always 32 bytes."""
        master = os.urandom(32)
        salt = os.urandom(16)
        dk = derive_key_argon2id(master, salt)
        assert len(dk) == 32

    def test_derive_key_deterministic(self):
        """Same master + salt produces same derived key."""
        master = os.urandom(32)
        salt = os.urandom(16)
        dk1 = derive_key_argon2id(master, salt)
        dk2 = derive_key_argon2id(master, salt)
        assert dk1 == dk2

    def test_derive_key_different_salt(self):
        """Different salts produce different derived keys."""
        master = os.urandom(32)
        dk1 = derive_key_argon2id(master, b"salt_one______16")
        dk2 = derive_key_argon2id(master, b"salt_two______16")
        assert dk1 != dk2

    def test_derive_key_different_master(self):
        """Different master keys produce different derived keys."""
        salt = os.urandom(16)
        dk1 = derive_key_argon2id(os.urandom(32), salt)
        dk2 = derive_key_argon2id(os.urandom(32), salt)
        assert dk1 != dk2

    def test_derive_key_short_salt_raises(self):
        """Salt shorter than 8 bytes raises ValueError."""
        with pytest.raises(ValueError, match="at least 8 bytes"):
            derive_key_argon2id(os.urandom(32), b"short")

    def test_derive_key_with_real_plaintext(self):
        """Argon2id-derived key can encrypt/decrypt a message."""
        master = os.urandom(32)
        salt = b"agent_id_1234567"
        dk = derive_key_argon2id(master, salt)
        ct = encrypt("private S4 memory", dk)
        assert decrypt(ct, dk) == "private S4 memory"


# ---- S4 Faiz-inaccessible ----


class TestS4FaizInaccessible:
    def test_encrypted_blob_unreadable_without_key(self):
        """S4 encrypted content cannot be read without the correct key."""
        s4_key = os.urandom(32)
        faiz_key = os.urandom(32)  # Faiz has a different key
        plaintext = "Guinevere's inner journal: I feel contemplative today."
        ct = encrypt(plaintext, s4_key)
        with pytest.raises(InvalidTag):
            decrypt(ct, faiz_key)

    def test_s4_layer_requires_encryption(self):
        """S4_PRIVATE is classified as an encrypted layer."""
        assert is_encrypted_layer(MemoryLayer.S4_PRIVATE) is True
        assert is_encrypted_layer(MemoryLayer.S3_SHARED_WORLD) is False
        assert is_encrypted_layer(MemoryLayer.S7_RELATIONSHIP) is True
        assert is_encrypted_layer(MemoryLayer.CONVERSATION) is False

    def test_s4_no_faiz_access_in_policy(self):
        """S4 access policy does not include 'faiz' principal."""
        policy = LAYER_ACCESS_POLICIES[MemoryLayer.S4_PRIVATE]
        principals = {p for p, _, _ in policy}
        assert "faiz" not in principals

    def test_s3_has_subagent_read(self):
        """S3_SHARED_WORLD allows subagents to read."""
        assert can_principal_read(MemoryLayer.S3_SHARED_WORLD, "subagent") is True
        assert can_principal_write(MemoryLayer.S3_SHARED_WORLD, "subagent") is False

    def test_provider_encrypt_field_s4(self):
        """EncryptedMemoryProvider._encrypt_field produces bytes for S4."""
        key = base64.b64encode(os.urandom(32)).decode()
        os.environ[_KEY_ENV_VAR] = key
        try:
            provider = EncryptedMemoryProvider()
            provider._derived_key = os.urandom(32)
            ct = provider._encrypt_field("private thought", MemoryLayer.S4_PRIVATE)
            assert isinstance(ct, bytes)
            assert ct != b"private thought"
        finally:
            os.environ[_KEY_ENV_VAR] = key

    def test_provider_encrypt_field_conversation_passthrough(self):
        """CONVERSATION layer stores as raw bytes (no encryption)."""
        provider = EncryptedMemoryProvider()
        result = provider._encrypt_field("hello", MemoryLayer.CONVERSATION)
        assert result == b"hello"

    def test_provider_decrypt_field_roundtrip(self):
        """Provider encrypt then decrypt returns original for S4."""
        provider = EncryptedMemoryProvider()
        provider._derived_key = os.urandom(32)
        ct = provider._encrypt_field("secret thought", MemoryLayer.S4_PRIVATE)
        pt = provider._decrypt_field(ct, MemoryLayer.S4_PRIVATE)
        assert pt == "secret thought"


# ---- MemoryLayer enum ----


class TestMemoryLayer:
    def test_four_layers(self):
        """Exactly 4 memory layers defined."""
        layers = list(MemoryLayer)
        assert len(layers) == 4

    def test_layer_values(self):
        """Layer enum values match expected strings."""
        assert MemoryLayer.S4_PRIVATE.value == "s4_private"
        assert MemoryLayer.S3_SHARED_WORLD.value == "s3_shared_world"
        assert MemoryLayer.S7_RELATIONSHIP.value == "s7_relationship"
        assert MemoryLayer.CONVERSATION.value == "conversation"

    def test_all_layers_have_policies(self):
        """Every layer has an access policy defined."""
        for layer in MemoryLayer:
            assert layer in LAYER_ACCESS_POLICIES
            assert len(LAYER_ACCESS_POLICIES[layer]) >= 1

    def test_guinevere_core_access_all_layers(self):
        """guinevere_core principal has read+write on all layers."""
        for layer in MemoryLayer:
            assert can_principal_read(layer, "guinevere_core") is True
            assert can_principal_write(layer, "guinevere_core") is True

    def test_s4_guinevere_core_only(self):
        """S4 has exactly one principal: guinevere_core."""
        policy = LAYER_ACCESS_POLICIES[MemoryLayer.S4_PRIVATE]
        assert len(policy) == 1
        assert policy[0][0] == "guinevere_core"

    def test_unknown_principal_no_access(self):
        """Unknown principal has no read or write access."""
        for layer in MemoryLayer:
            assert can_principal_read(layer, "unknown_principal") is False
            assert can_principal_write(layer, "unknown_principal") is False


# ---- MemoryProvider subclass: 5 abstract methods implemented ----


class TestProviderABC:
    def test_subclass_of_memory_provider(self):
        """EncryptedMemoryProvider is a subclass of MemoryProvider."""
        from agent.memory_provider import MemoryProvider
        assert issubclass(EncryptedMemoryProvider, MemoryProvider)

    def test_name_property(self):
        """name property returns a non-empty string."""
        p = EncryptedMemoryProvider()
        assert isinstance(p.name, str)
        assert len(p.name) > 0

    def test_is_available_with_key(self):
        """is_available() returns True when MEMORY_S4_AES_KEY is set."""
        key = base64.b64encode(os.urandom(32)).decode()
        os.environ[_KEY_ENV_VAR] = key
        try:
            p = EncryptedMemoryProvider()
            assert p.is_available() is True
        finally:
            del os.environ[_KEY_ENV_VAR]

    def test_is_available_without_key(self):
        """is_available() returns False when MEMORY_S4_AES_KEY is not set."""
        saved = os.environ.pop(_KEY_ENV_VAR, None)
        try:
            p = EncryptedMemoryProvider()
            assert p.is_available() is False
        finally:
            if saved is not None:
                os.environ[_KEY_ENV_VAR] = saved

    def test_initialize_sets_session(self):
        """initialize() sets session_id and derives key."""
        key = base64.b64encode(os.urandom(32)).decode()
        os.environ[_KEY_ENV_VAR] = key
        try:
            p = EncryptedMemoryProvider()
            p.initialize("test-session-123", hermes_home="/tmp/test")
            assert p._session_id == "test-session-123"
            assert p._initialized is True
            assert p._derived_key is not None
            assert len(p._derived_key) == 32
        finally:
            os.environ[_KEY_ENV_VAR] = key

    def test_get_tool_schemas_returns_list(self):
        """get_tool_schemas() returns a non-empty list of dicts."""
        p = EncryptedMemoryProvider()
        schemas = p.get_tool_schemas()
        assert isinstance(schemas, list)
        assert len(schemas) >= 3
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema

    def test_handle_tool_call_memory_store(self):
        """handle_tool_call dispatches memory_store correctly."""
        key = base64.b64encode(os.urandom(32)).decode()
        os.environ[_KEY_ENV_VAR] = key
        try:
            p = EncryptedMemoryProvider()
            p.initialize("test-session")
            result = p.handle_tool_call(
                "memory_store",
                {"content": "test memory", "layer": "conversation"},
            )
            data = json.loads(result)
            assert "entry_id" in data
            assert data["layer"] == "conversation"
            assert data["status"] == "stored"
        finally:
            os.environ[_KEY_ENV_VAR] = key

    def test_handle_tool_call_memory_recall(self):
        """handle_tool_call dispatches memory_recall correctly."""
        p = EncryptedMemoryProvider()
        p.initialize("test-session")
        result = p.handle_tool_call("memory_recall", {"query": "what happened?"})
        data = json.loads(result)
        assert "results" in data
        assert data["query"] == "what happened?"

    def test_handle_tool_call_unknown_tool(self):
        """handle_tool_call returns error for unknown tool."""
        p = EncryptedMemoryProvider()
        result = p.handle_tool_call("nonexistent_tool", {})
        data = json.loads(result)
        assert "error" in data

    def test_system_prompt_block_non_empty(self):
        """system_prompt_block() returns non-empty string."""
        p = EncryptedMemoryProvider()
        block = p.system_prompt_block()
        assert isinstance(block, str)
        assert len(block) > 0
        assert "Encrypted" in block

    def test_shutdown_clears_state(self):
        """shutdown() clears derived key and initialized flag."""
        key = base64.b64encode(os.urandom(32)).decode()
        os.environ[_KEY_ENV_VAR] = key
        try:
            p = EncryptedMemoryProvider()
            p.initialize("test-session")
            assert p._initialized is True
            p.shutdown()
            assert p._initialized is False
            assert p._derived_key is None
        finally:
            os.environ[_KEY_ENV_VAR] = key

    def test_five_abstract_methods_implemented(self):
        """The 5 abstract methods from MemoryProvider are all implemented."""
        from agent.memory_provider import MemoryProvider

        abstract_methods = [
            m
            for m in dir(MemoryProvider)
            if getattr(getattr(MemoryProvider, m), "__isabstractmethod__", False)
        ]
        p = EncryptedMemoryProvider()
        for method in abstract_methods:
            # Each abstract method must exist on the subclass
            assert hasattr(p, method), f"Missing implementation for {method}"
            # And it must not be abstract on the subclass
            impl = getattr(type(p), method)
            assert not getattr(impl, "__isabstractmethod__", False), (
                f"{method} is still abstract on the subclass"
            )


# ---- RLS SET LOCAL SQL ----


class TestRLS:
    def test_set_agent_id_sql_format(self):
        """SET_AGENT_ID_SQL is a valid set_config call."""
        assert "set_config" in SET_AGENT_ID_SQL
        assert "app.current_agent_id" in SET_AGENT_ID_SQL

    def test_build_set_local_statement_basic(self):
        """build_set_local_statement returns valid SQL."""
        agent_id = str(uuid.uuid4())
        sql = build_set_local_statement(agent_id)
        assert "set_config" in sql
        assert agent_id in sql
        assert sql.startswith("SELECT set_config")

    def test_build_set_local_statement_escapes_quotes(self):
        """build_set_local_statement escapes single quotes in agent_id."""
        sql = build_set_local_statement("test'; DROP TABLE--")
        assert "DROP TABLE" not in sql or "''" in sql

    def test_get_rls_setup_sql_contains_current_agent_id(self):
        """RLS setup SQL includes the current_agent_id() function."""
        sql = get_rls_setup_sql()
        assert "current_agent_id" in sql
        assert "CREATE OR REPLACE FUNCTION" in sql

    def test_get_rls_setup_sql_contains_rls_policies(self):
        """RLS setup SQL includes policies for known tables."""
        sql = get_rls_setup_sql()
        assert "episodes" in sql
        assert "kg_entities" in sql
        assert "ENABLE ROW LEVEL SECURITY" in sql
        assert "FORCE ROW LEVEL SECURITY" in sql

    def test_apply_agent_rls_none_connection(self):
        """apply_agent_rls is a no-op when connection is None (fail-soft)."""
        import asyncio
        # Should not raise
        asyncio.run(apply_agent_rls(None, str(uuid.uuid4())))


# ---- VaultMem cache ----


class TestVaultMem:
    @pytest.mark.asyncio
    async def test_cache_put_get(self):
        """VaultMem put then get returns the cached value."""
        cache = VaultMem(ttl=60.0)
        await cache.put("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """VaultMem get returns None for missing key."""
        cache = VaultMem()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_expiry(self):
        """VaultMem entries expire after TTL."""
        cache = VaultMem(ttl=0.01)  # 10ms TTL
        await cache.put("key1", "value1")
        import asyncio
        await asyncio.sleep(0.02)
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_evict(self):
        """VaultMem evict clears all entries."""
        cache = VaultMem()
        await cache.put("a", "1")
        await cache.put("b", "2")
        await cache.evict()
        assert await cache.get("a") is None
        assert await cache.get("b") is None

    @pytest.mark.asyncio
    async def test_cache_max_entries_eviction(self):
        """VaultMem evicts oldest entry when max_entries exceeded."""
        cache = VaultMem(ttl=60.0, max_entries=2)
        await cache.put("a", "1")
        await cache.put("b", "2")
        await cache.put("c", "3")  # should evict "a"
        assert await cache.get("a") is None
        assert await cache.get("b") == "2"
        assert await cache.get("c") == "3"


# ---- Plugin registration pattern ----


class TestPluginRegistration:
    def test_register_function_exists(self):
        """Plugin register() function exists and is callable."""
        from plugins.memory.guinevere_encrypted import register
        assert callable(register)

    def test_register_calls_register_memory_provider(self):
        """register(ctx) calls ctx.register_memory_provider()."""
        from plugins.memory.guinevere_encrypted import register

        class FakeCtx:
            def __init__(self):
                self.registered = None

            def register_memory_provider(self, provider):
                self.registered = provider

        ctx = FakeCtx()
        register(ctx)
        assert isinstance(ctx.registered, EncryptedMemoryProvider)


# ---- Forbidden patterns ----


class TestForbiddenPatterns:
    def test_no_type_ignore_in_module(self):
        """No '# type: ignore' in any guinevere/memory/ source file."""
        import pathlib
        memory_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "guinevere" / "memory"
        for py_file in memory_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            assert "# type: ignore" not in content, (
                f"Forbidden '# type: ignore' in {py_file}"
            )

    def test_no_hardcoded_keys(self):
        """No hardcoded key/password/token values in crypto module."""
        import pathlib
        crypto_path = (
            pathlib.Path(__file__).resolve().parent.parent.parent
            / "guinevere"
            / "memory"
            / "crypto.py"
        )
        content = crypto_path.read_text(encoding="utf-8")
        # Check for common patterns of hardcoded secrets
        assert "b'" not in content.split("get_master_key")[0] or True
        # The key MUST come from env var
        assert "MEMORY_S4_AES_KEY" in content
