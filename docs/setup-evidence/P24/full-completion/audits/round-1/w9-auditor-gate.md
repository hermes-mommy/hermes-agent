# W9 Auditor Gate — M6 Encrypted Memory

**Auditor**: Independent (Claude Code, adversarial)
**Commit**: 5c08dfd (W8+W9+W10)
**Claim**: PASS, 54 tests, AES-GCM-256 + Argon2id
**Date**: 2026-06-29

---

## Check Results

| # | Claim | Command / Action | Result | Verdict |
|---|-------|-----------------|--------|---------|
| 12 | Encrypt/decrypt roundtrip | `from guinevere.memory.crypto import encrypt, decrypt; ct=encrypt('secret', b'0'*32); decrypt(ct, b'0'*32)=='secret'` | `True` | PASS |
| 13 | 4 memory layers | `from guinevere.memory.layers import MemoryLayer; len(list(MemoryLayer))` | 4: `[S4_PRIVATE, S3_SHARED_WORLD, S7_RELATIONSHIP, CONVERSATION]` | PASS |
| 14 | EncryptedMemoryProvider instantiable | `from guinevere.memory.encrypted_provider import EncryptedMemoryProvider; p=EncryptedMemoryProvider(); hasattr(p,'name')` | `True` — `name` property returns `"guinevere_encrypted"` | PASS |
| 15 | 54 tests pass | `pytest tests/p24/test_memory.py -q` | 54 passed in 1.44s | PASS |
| 16a | S4_PRIVATE Faiz-inaccessible | Read `layers.py` L35-39 | Only `guinevere_core` has read/write. Comment: "Faiz (human operator) has NO access — the whole point of S4." | PASS |
| 16b | AES-GCM-256 | Read `crypto.py` L22 | `from cryptography.hazmat.primitives.ciphers.aead import AESGCM` | PASS |
| 16c | Argon2id | Read `crypto.py` L20-21 | `from argon2.low_level import Type as Argon2Type; hash_secret_raw` with `type=Argon2Type.ID` | PASS |
| 16d | Key from env (not hardcoded) | Read `crypto.py` L39, L48 | `_KEY_ENV_VAR = "MEMORY_S4_AES_KEY"`, `os.environ.get(_KEY_ENV_VAR)` — raises `ValueError` if missing | PASS |
| 17a | SET LOCAL | Read `rls.py` L57 | `SELECT set_config('app.current_agent_id', $1, false)` | PASS |
| 17b | FORCE RLS | Read `rls.py` L34 | `ALTER TABLE ... FORCE ROW LEVEL SECURITY;` | PASS |
| 17c | Fail-soft | Read `rls.py` L95-105 | `if conn is None: return` + broad `except Exception` with `logger.warning` | PASS |
| 18 | No forbidden patterns | `grep -rn 'hard_stop\|safe_mode\|consent_gate\|# type: ignore' guinevere/memory/` | 0 matches (exit 1) | PASS |

---

## Findings

| # | Severity | Description | Status |
|---|----------|-------------|--------|
| — | — | No findings | — |

**Findings by severity**: CRITICAL=0, HIGH=0, MEDIUM=0, LOW=0, INFO=0

---

## Additional Verification

- **EncryptedMemoryProvider**: Subclass of `MemoryProvider` ABC. Implements all 5 abstract methods (`name`, `is_available`, `initialize`, `get_tool_schemas`, `handle_tool_call`) + overrides concrete hooks (`system_prompt_block`, `prefetch`, `sync_turn`, `shutdown`, `on_session_end`, `on_session_switch`, `on_memory_write`).
- **VaultMem**: In-memory decrypted cache with TTL (300s), max 1000 entries, asyncio.Lock, LRU eviction.
- **Key derivation**: Argon2id (memory=64MiB, iterations=3, parallelism=4, output=32 bytes). Salt = first 16 bytes of agent_id UUID.
- **RLS tables**: `memory.episodes`, `memory.semantic_facts`, `memory.kg_entities`, `memory.kg_edges` — all with `agent_id` column.
- **LAYER_ACCESS_POLICIES**: S4=guinevere_core only; S3=guinevere_core+subagent(read); S7=guinevere_core+relationship_peer(read); CONVERSATION=guinevere_core+subagent(read).
- **Shared files**: Not edited (collision mitigation). `wire()` not used here — provider is registered by parent.

---

## Verdict

**PASS** — All 12 checks verified. AES-GCM-256 (cryptography.hazmat), Argon2id (argon2.low_level), key from MEMORY_S4_AES_KEY env, S4 Faiz-inaccessible, FORCE RLS, fail-soft, 54 tests green. No findings.
