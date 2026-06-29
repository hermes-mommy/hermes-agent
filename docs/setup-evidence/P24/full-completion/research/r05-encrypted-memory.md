# Domain 5 Research: Encrypted Memory Architecture

> **Generated**: 2026-06-29
> **Method**: Read `agent/memory_provider.py` (Hermes v0.15.2 ABC, 292 lines), all 12 files in `src/memory/`, 47 files in `src/knowledge_graph/`, infrastructure-patterns-research.md (PG RLS, TimescaleDB RLS bugs #7830/#6827, pgcrypto), existing encryption patterns (`src/wearable/encryption.py`, `src/projects/secrets_vault.py`), and Hindsight plugin registration pattern (`plugins/memory/hindsight/__init__.py`).
> **Scope**: Design `guinevere/memory/encrypted_provider.py` subclassing MemoryProvider; 4-layer memory (S4/S3/S7/conversation); AES-GCM-256 + Argon2id; PG RLS with SET LOCAL; knowledge graph as semantic memory layer.

---

## 1. Findings: MemoryProvider ABC (Hermes v0.15.2)

**File**: `.venv/Lib/site-packages/agent/memory_provider.py`

### 1.1 Abstract Methods (must implement)

| # | Method | Signature | Line |
|---|--------|-----------|------|
| 1 | `name` | `@property -> str` | :46 |
| 2 | `is_available()` | `-> bool` | :53 |
| 3 | `initialize(session_id, **kwargs)` | `-> None` | :60 |
| 4 | `get_tool_schemas()` | `-> List[Dict]` | :133 |
| 5 | `handle_tool_call(tool_name, args, **kwargs)` | `-> str` | :143 |

### 1.2 Lifecycle Methods (with defaults)

| # | Method | Default | Line |
|---|--------|---------|------|
| 6 | `system_prompt_block()` | `""` | :84 |
| 7 | `prefetch(query, *, session_id)` | `""` | :93 |
| 8 | `queue_prefetch(query, *, session_id)` | no-op | :107 |
| 9 | `sync_turn(user, asst, *, session_id, messages)` | no-op | :115 |
| 10 | `shutdown()` | no-op | :152 |

### 1.3 Optional Hooks (override to opt in)

| # | Method | Line |
|---|--------|------|
| 11 | `on_turn_start(turn, message, **kwargs)` | :156 |
| 12 | `on_session_end(messages)` | :165 |
| 13 | `on_session_switch(new_session_id, *, parent_session_id, reset, **kwargs)` | :175 |
| 14 | `on_pre_compress(messages) -> str` | :214 |
| 15 | `on_memory_write(action, target, content, metadata)` | :274 |
| 16 | `on_delegation(task, result, *, child_session_id, **kwargs)` | :226 |
| 17 | `get_config_schema() -> List[Dict]` | :239 |
| 18 | `save_config(values, hermes_home)` | :257 |

**Total**: 18 methods (5 abstract, 5 lifecycle with defaults, 8 optional hooks). The ABC is well-designed for pluggable backends.

### 1.4 Plugin Registration Pattern

**File**: `.venv/Lib/site-packages/plugins/memory/hindsight/__init__.py:1774`

```python
def register(ctx) -> None:
    ctx.register_memory_provider(HindsightMemoryProvider())
```

The encrypted provider must follow this exact pattern. The `ctx` object has a `register_memory_provider()` method. Plugins ship in `plugins/memory/<name>/`.

---

## 2. Findings: Existing Memory Pipeline (src/memory/)

### 2.1 Architecture Summary

12 files implementing a complete episodic-to-semantic memory pipeline:

| File | Purpose | Key Details |
|------|---------|-------------|
| `models.py` | 47 tables across 12 schemas | Lines 1-1225. `ClassificationMetaMixin` with `encryption_profile='envelope-AES-256-GCM'` (line 71), `key_id` (line 76), `key_version` (line 77). `FaizProfile.value` is `LargeBinary` (line 220). `PgcryptoConfig` defaults to `aes-256-gcm` (line 1222). |
| `db.py` | Async SQLAlchemy session factory | Lines 1-193. Lazy singleton engine, `get_async_session()` context manager. Default URL: `postgresql+asyncpg://guinevere_core@localhost:5433/guinevere` (line 36). |
| `__init__.py` | Public surface exports | Lines 1-210. Exports all classification constants, errors, pipeline functions. |
| `embeddings.py` | 9Router-native embedding service | Lines 1-775. 1536-dim vectors, 5 classification levels (Public/Internal/Restricted/Confidential/Critical), privacy guards, redaction patterns for Restricted/Confidential. Critical requires sanitized_summary. |
| `write_pipeline.py` | Episodic memory store | Lines 1-357. `store_episode()` and `store_episode_batch()`. Classification-default `Restricted`. Critical fail-closed guard. |
| `read_pipeline.py` | Hybrid ranking recall | Lines 1-958. RRF fusion (vector + FTS + recency), classification ceiling per principal, safe-mode content substitution, DNR exclusion, token budget (4000 tokens). |
| `consolidation.py` | Episodic-to-semantic consolidation | Lines 1-758. APScheduler daily at 03:00 ICT. DNR-safe, safe-word-aware, classification-preserving, content-key deduplication. |
| `dnr.py` | Do-not-recall hardening | Lines 1-419. Authorized principals only (`guinevere_core`), metadata-only audit events, post-recall/pre-injection gate. |
| `tiers.py` | Memory tier management | Lines 1-42. Working/Episodic/Semantic with decay rates (30%/5%/1% per day). |
| `spaced_repetition.py` | FSRS-6 scheduler | Lines 1-603. Lazy-imported optional `fsrs` library, retrievability formula R(t) = (1 + t / (9*S))^(-D). |
| `compaction.py` | Context compaction | (exists -- not directly relevant to encryption) |
| `embedding_backfill.py` | Backfill embeddings | (exists -- not directly relevant to encryption) |

### 2.2 Key Observations for Encrypted Provider

1. **FaizProfile already uses LargeBinary for encrypted values** (models.py:220) -- the `value` column stores AES-GCM-256 ciphertext as bytes.
2. **ClassificationMetaMixin already declares `encryption_profile='envelope-AES-256-GCM'`** (models.py:71) and `key_id`/`key_version` columns (models.py:76-77).
3. **PgcryptoConfig defaults to `aes-256-gcm`** (models.py:1222) with `key_derivation_function='pbkdf2'` (models.py:1224). The encrypted provider must upgrade this to Argon2id.
4. **The db.py session factory uses SQLAlchemy async** with asyncpg -- the encrypted provider must integrate at this layer for RLS SET LOCAL.

---

## 3. Findings: Knowledge Graph (src/knowledge_graph/ -- 47 files)

### 3.1 Architecture

The KG module (P16) provides semantic memory via graph traversal on top of PostgreSQL.

| Component | Files | Key Details |
|-----------|-------|-------------|
| `types.py` | 1 | `KGEntity`, `KGEdge`, `KGTriple`, `RecallContext`, `EntityCategory` (15 types), `RelationType` (15 types), `EdgeStatus` (4 states). |
| `repository.py` | 1 | `KGRepository` with session lifecycle. Reuses caller-supplied `session_factory`. Health check probes `memory.kg_entities`. |
| `query/engine.py` | 1 | `KGQueryEngine` with RCTE traversal, BFS path-finding, neighborhood fetch, entity search. All SQL uses `memory.kg_*` schema. |
| `query/rrf_fusion.py` | 1 | RRF fusion with `KG_RRF_WEIGHT = 0.20` (constants.py:19). |
| `query/token_budget.py` | 1 | `KG_TOKEN_BUDGET_MAX = 1000` (constants.py:28). |
| `query/context.py` | 1 | Context assembly for prompt injection. |
| `query/ppr.py` | 1 | Personalized PageRank. |
| `extraction/` | 3 | `EntityExtractor`, `RelationExtractor` -- rule-based L1+L2 NER/RE. |
| `resolution/` | 3 | `canonical.py`, `resolver.py`, `fuzzy.py` -- entity dedup. |
| `ingestion/` | 4 | `pipeline.py`, `batch_processor.py`, `backfill.py`, `backfill_validator.py`, `cron.py`. |
| `consent/` | 3 | `manager.py`, `rls.py`, `audit.py` -- RLS policy manager. |
| `observability/` | 3 | `metrics.py`, `tracer.py`, `logger.py`. |
| `eval/` | 4 | `metrics.py`, `golden_set.py`, `report.py`, `runner.py`. |
| `tests/` | 7 | Smoke, adversarial, consent boundary, query, ingestion, entity resolution, VPS eval. |
| `config.py` | 1 | `KGConfig` Pydantic model. |
| `constants.py` | 1 | `RRF_K=60`, `KG_RRF_WEIGHT=0.20`, `KG_TOKEN_BUDGET_MAX=1000`, `MAX_TRAVERSAL_HOPS=3`. |
| `errors.py` | 1 | Domain-specific error hierarchy. |
| `__init__.py` | 1 | PEP 562 lazy imports for heavy modules. |

### 3.2 How KG Integrates as Semantic Memory Layer

**Data flow**: Episodes -> Consolidation -> SemanticFacts -> KG Extraction -> KG Entities/Edges -> Query Engine -> RecallContext -> RRF Fusion (weight 0.20) -> Prompt Injection

The KG feeds into the memory read pipeline's RRF fusion at `KG_RRF_WEIGHT = 0.20` (constants.py:19). The `RecallContext` dataclass (types.py:256-278) bundles entities, edges, triples, and token count for prompt injection.

**RLS Status**: The `RLSPolicyManager` (consent/rls.py:161) applies **placeholder** soft-delete-only policies on 6 `kg_*` tables. Full consent-aware RLS is **deferred to P16-008** (consent/rls.py:222-237). The current placeholder policies enforce `deletion_state != 'deleted' AND is_tombstoned = FALSE` but do NOT validate consent_token, classification ceiling, or safe-mode filtering at the DB level.

### 3.3 KG Tables for Encrypted Provider

The KG uses 6 tables in `memory` schema (consent/rls.py:60-67):
- `kg_entities` -- nodes with `canonical_key`, `display_name`, `entity_type`, `aliases`, `embedding`
- `kg_edges` -- directed edges with `src_entity_id`, `dst_entity_id`, `relationship_type`, `confidence`, `consent_token`
- `kg_episodes` -- provenance rows
- `kg_same_as_edges` -- entity resolution edges
- `kg_episode_participants` -- episode-entity links
- `kg_consent_audit` -- consent audit trail

---

## 4. Findings: Infrastructure Patterns (PG RLS, pgcrypto, TimescaleDB)

**File**: `docs/setup-evidence/P24/research/research-wave-2/infrastructure-patterns-research.md`

### 4.1 PG RLS Pattern

- **SET LOCAL** (not SET) for transaction-scoped agent_id (infrastructure-patterns-research.md:113)
- Non-superuser app role `p24_app_user` (line 39)
- `current_agent_id()` SQL function reads `app.current_agent_id` session variable (line 68)
- USING + WITH CHECK on ALL operations (lines 73-98)
- Index `agent_id` first for RLS filter optimization (line 363)

### 4.2 pgcrypto + RLS

- `pgp_sym_encrypt`/`pgp_sym_decrypt` for field-level encryption (lines 275-299)
- RLS controls which rows are visible; pgcrypto controls what data is readable
- Encrypted content stored as `BYTEA` with non-sensitive metadata in plaintext for querying

### 4.3 TimescaleDB RLS Caveats

- **Bug #7830**: Chunks do not inherit RLS policies -- users can bypass RLS by querying chunks directly. **Mitigation**: Revoke chunk access from app role (lines 337-348).
- **Bug #6827**: RLS + Compression is NOT supported on hypertables (line 313).
- **Bug #5787**: RLS on continuous aggregates is not supported (line 315).

### 4.4 Existing Encryption in Guinevere

**Fernet pattern** (`src/wearable/encryption.py`):
- Symmetric encryption via `cryptography.fernet.Fernet`
- `ENC:` prefix marker for encrypted values
- Key from `WEARABLE_ENCRYPTION_KEY` env var or SOPS-decrypted .env file
- `encrypt_value()`/`decrypt_value()` for string fields
- `encrypt_health_record()`/`decrypt_health_record()` for dict-level batch operations

**ProjectSecretsVault** (`src/projects/secrets_vault.py`):
- In-memory isolation by `project_id`
- Thread-safe via `threading.RLock`
- No persistence -- pure in-memory

---

## 5. Design: `guinevere/memory/encrypted_provider.py`

### 5.1 4-Layer Memory Model

| Layer | Name | Encryption | Access | Tables |
|-------|------|------------|--------|--------|
| S4 | Private (Guinevere-only) | AES-GCM-256 + Argon2id key derivation | Only `guinevere_core` principal | `FaizProfile`, `InnerJournal`, `FaizPredictions`, episodes with classification=Confidential/Critical |
| S3 | Shared-world | RLS-only (no field encryption) | `guinevere_core` + authorized subagents | `Episodes` (Public/Internal), `SemanticFacts`, `SocialMap` |
| S7 | Relationship | AES-GCM-256 for sensitive fields | Per-relationship consent tokens | `CommunicationLog`, `ClientContacts`, relationship-scoped episodes |
| Conv | Conversation | RLS + DNR guard | Session-scoped | `Episodes` (working tier), ephemeral context |

### 5.2 Encryption Architecture

**Key Derivation**: Argon2id (not PBKDF2 as currently in `PgcryptoConfig` at models.py:1224)
- Memory: 64 MiB, Iterations: 3, Parallelism: 4
- Derives a 256-bit key from the master secret
- Per-agent key derivation using `agent_id` as salt component
- Key rotation via `key_version` column (models.py:77)

**Encryption**: AES-256-GCM (matches `encryption_profile='envelope-AES-256-GCM'` at models.py:71)
- 96-bit nonce (12 bytes), randomly generated per encryption
- 128-bit authentication tag (16 bytes)
- Ciphertext stored as `LargeBinary` (matching FaizProfile.value pattern at models.py:220)
- Nonce prepended to ciphertext: `[12-byte nonce][ciphertext][16-byte tag]`

**VaultMem Pattern**: In-memory decrypted cache with TTL
- Decrypted values cached in a `dict[uuid.UUID, DecryptedEntry]` with TTL (default 300s)
- Cache cleared on `shutdown()` and `on_session_switch()`
- Never persisted to disk -- pure process-scoped cache
- Thread-safe via `asyncio.Lock` (not `threading.Lock` -- the provider runs on the async event loop)

### 5.3 PG RLS Integration

**Transaction-scoped agent_id via SET LOCAL** (per infrastructure-patterns-research.md:113):

```sql
-- Context function
CREATE OR REPLACE FUNCTION current_agent_id()
RETURNS UUID AS $$
    SELECT NULLIF(current_setting('app.current_agent_id', true), '')::UUID;
$$ LANGUAGE SQL STABLE;

-- RLS policies on agent-scoped tables
ALTER TABLE memory.episodes ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_isolation ON memory.episodes
    FOR ALL
    USING (agent_id = current_agent_id())
    WITH CHECK (agent_id = current_agent_id());
```

**Python integration**: The provider wraps every DB operation in a transaction that sets `app.current_agent_id` via `SET LOCAL`:

```python
async with conn.transaction():
    await conn.execute(
        "SELECT set_config('app.current_agent_id', $1, false)",
        str(agent_id)
    )
    # All queries in this transaction are RLS-filtered
```

**App role**: Non-superuser `guinevere_core` (already exists -- see db.py:36 and consent/rls.py:76). Must NOT be superuser or table owner -- both bypass RLS.

### 5.4 S4 Private Layer (Faiz-inaccessible)

The S4 layer stores data that Faiz (the human operator) cannot access directly:

1. **FaizProfile encrypted values**: Already stored as `LargeBinary` (models.py:220). The encrypted provider wraps read/write with Argon2id-derived keys.
2. **InnerJournal entries**: `revealed_to_faiz` boolean (models.py:282) controls selective disclosure. S4 entries have `revealed_to_faiz = FALSE`.
3. **Critical-classified episodes**: Raw content encrypted at rest, embedding derived from sanitized summary only (write_pipeline.py:277-281).
4. **Access control**: RLS filters S4 rows to `agent_id = current_agent_id()`. Even if Faiz has DB access, the app role's RLS policy prevents cross-agent reads. For Faiz-inaccessible specifically, S4 rows use a `guinevere_private` agent_id that has no human-facing principal.

### 5.5 TimescaleDB RLS Mitigations

For time-series tables (if hypertables are used for episodes/events):

1. **Revoke chunk access** from `guinevere_core` role to prevent RLS bypass via #7830 (infrastructure-patterns-research.md:337-348).
2. **No TimescaleDB compression** on RLS-enabled hypertables (#6827 -- they are incompatible).
3. **Hash partition on agent_id** for multi-tenant performance: `add_dimension('table', by_hash('agent_id', 4))`.
4. **Periodic chunk audit**: Run the chunk revocation DO block on a cron schedule or as a trigger on chunk creation.

### 5.6 Knowledge Graph Integration as Semantic Memory Layer

The KG serves as the **semantic memory layer** in the 4-layer model:

1. **Extraction pipeline**: Episodes -> Consolidation -> SemanticFacts -> EntityExtractor/RelationExtractor -> KG Entities/Edges
2. **Query integration**: `KGQueryEngine.traverse()` returns `GraphTraversalResult` (query/engine.py:123), fused into recall via RRF at weight 0.20 (constants.py:19)
3. **Encrypted KG entities**: S4-classified entities get their `display_name` and `description` encrypted at rest. The `embedding` column (pgvector) is computed from the sanitized form only. Entity resolution uses the plaintext canonical_key for dedup.
4. **Consent-aware KG access**: The `consent_token` field on `kg_edges` (types.py:228) controls edge visibility per principal. The encrypted provider sets `consent_token` to a token derived from the agent_id + relationship scope.
5. **RLS on KG tables**: The existing `RLSPolicyManager` (consent/rls.py:161) applies placeholder policies. The encrypted provider upgrades these to full agent_id-based RLS using `SET LOCAL` (deferred work: P16-008).

### 5.7 Subclass Design

```
guinevere/memory/
    __init__.py          # Public surface
    encrypted_provider.py # MemoryProvider subclass
    crypto.py            # AES-GCM-256 + Argon2id primitives
    vault_mem.py         # In-memory decrypted cache with TTL
    rls_middleware.py     # SET LOCAL integration for SQLAlchemy
    key_manager.py       # Key derivation, rotation, versioning
```

**encrypted_provider.py** class structure:

```python
class EncryptedMemoryProvider(MemoryProvider):
    """Guinevere encrypted memory provider.
    
    4-layer memory with AES-GCM-256 encryption for S4/S7 layers,
    PG RLS for agent isolation, Argon2id key derivation, and
    knowledge graph integration as semantic memory layer.
    """
    
    name: str = "guinevere_encrypted"
    
    # Core lifecycle
    is_available() -> bool          # Check PG connection, pgcrypto extension
    initialize(session_id, **kwargs) # Derive keys, set up RLS context, warm cache
    get_tool_schemas() -> list      # expose memory_store, memory_recall, memory_forget
    handle_tool_call(...) -> str    # dispatch to store/recall/forget APIs
    
    # Context and recall
    system_prompt_block() -> str    # "Encrypted memory active. 4-layer model."
    prefetch(query, *, session_id)  # Decrypt + inject relevant S3/S4 context
    queue_prefetch(query, ...)      # Background recall on dedicated thread
    sync_turn(user, asst, ...)      # Encrypt + store episode, update KG
    
    # Session lifecycle
    on_session_switch(...)          # Clear VaultMem cache, rotate RLS context
    on_session_end(messages)        # Final consolidation, cache eviction
    on_memory_write(...)            # Mirror built-in writes to encrypted store
    shutdown()                      # Evict all caches, close connections
    
    # S4 private methods
    _encrypt_field(plaintext, layer) -> bytes   # AES-GCM-256 with Argon2id key
    _decrypt_field(ciphertext, layer) -> str    # Decrypt with VaultMem cache check
    _set_rls_context(agent_id)                  # SET LOCAL app.current_agent_id
    _derive_key(agent_id, key_version) -> bytes # Argon2id key derivation
```

### 5.8 NO SQLite

Confirmed: the existing codebase uses PostgreSQL exclusively:
- `db.py:36` -- `postgresql+asyncpg://guinevere_core@localhost:5433/guinevere`
- `models.py` -- all tables use PostgreSQL-specific types (JSONB, TSVECTOR, ARRAY, pgvector)
- `read_pipeline.py` -- uses `plainto_tsquery`, `ts_rank`, pgvector `<=>` operator
- 2 concurrent instances require PG connection pooling + Redis, not SQLite

---

## 6. Disposition for P24

| Component | Disposition | Rationale |
|-----------|-------------|-----------|
| `MemoryProvider` ABC | **PORT** (copy to repo root) | Already at `.venv/Lib/site-packages/agent/memory_provider.py`. Copy to `agent/memory_provider.py` in repo root per D1 in-repo root layout. |
| `src/memory/` (12 files) | **MODIFY-CREATE** | Existing pipeline is complete. Encrypted provider wraps it -- does not replace it. Add `guinevere/memory/` as the new namespace alongside. |
| `src/knowledge_graph/` (47 files) | **PORT** | Existing KG is production-ready. Wrap with encrypted-aware queries for S4 entities. Add RLS upgrade (P16-008). |
| `guinevere/memory/encrypted_provider.py` | **MODIFY-CREATE** | New file. Subclasses `MemoryProvider`. Integrates with existing `src/memory/` pipeline, `src/knowledge_graph/` semantic layer, and PG RLS. |
| `guinevere/memory/crypto.py` | **MODIFY-CREATE** | New file. AES-GCM-256 + Argon2id primitives. Replaces PBKDF2 in `PgcryptoConfig`. |
| `guinevere/memory/vault_mem.py` | **MODIFY-CREATE** | New file. In-memory decrypted cache with TTL and async lock. |
| `guinevere/memory/rls_middleware.py` | **MODIFY-CREATE** | New file. SET LOCAL integration for SQLAlchemy async sessions. |
| `guinevere/memory/key_manager.py` | **MODIFY-CREATE** | New file. Key derivation, rotation, versioning. Uses `key_id`/`key_version` from `ClassificationMetaMixin`. |
| `PgcryptoConfig.key_derivation_function` | **MODIFY-CREATE** | Change from `pbkdf2` (models.py:1224) to `argon2id`. Schema migration required. |

---

## 7. Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| R1 | Argon2id key derivation latency (~100ms per derivation) | Slow first-access for S4 data | VaultMem cache with 300s TTL amortizes cost. Pre-warm cache in `initialize()`. |
| R2 | TimescaleDB RLS chunk bypass (#7830) | Agent data leak via direct chunk query | Revoke chunk access from `guinevere_core` role. Run periodic audit. |
| R3 | TimescaleDB RLS + compression incompatibility (#6827) | Cannot compress hypertables with RLS | Use application-level compression or skip TimescaleDB compression for agent-scoped tables. |
| R4 | VaultMem cache memory pressure | OOM if many S4 records decrypted simultaneously | LRU eviction at configurable cap (default 1000 entries). TTL-based expiry. |
| R5 | Key rotation during active sessions | Stale ciphertexts with old key version | Read path must support multiple key versions. `key_version` column tracks which key encrypted each row. |
| R6 | RLS bypass via superuser connection | All RLS policies ignored | Connection string must use non-superuser `guinevere_core`. CI/CD must verify. `FORCE ROW LEVEL SECURITY` on all tables. |
| R7 | KG entity resolution with encrypted display_name | Resolution breaks if name is ciphertext | Resolution uses `canonical_key` (plaintext, deterministic). Encryption applies to `display_name` and `description` only. |
| R8 | Faiz-profile sensitivity | S4 data accidentally surfaced to human operator | RLS + classification ceiling + safe-mode triple guard. S4 uses distinct `agent_id` with no human-facing principal. |

---

## 8. Verdict

**PASS** -- Domain 5 is well-scoped and the existing codebase provides strong foundations.

Key evidence:
- `MemoryProvider` ABC (agent/memory_provider.py) is clean, 18 methods, well-documented lifecycle.
- `ClassificationMetaMixin` (models.py:54-83) already declares `encryption_profile='envelope-AES-256-GCM'`, `key_id`, `key_version` -- the schema is encryption-ready.
- `FaizProfile.value` (models.py:220) already uses `LargeBinary` for encrypted values.
- `PgcryptoConfig` (models.py:1211-1224) already configures AES-256-GCM.
- The write pipeline (write_pipeline.py:277) already enforces Critical fail-closed guard.
- The read pipeline (read_pipeline.py:135-145) already has classification ceiling per principal.
- The KG module (47 files) is production-ready with RCTE traversal, consent tokens, and placeholder RLS ready for upgrade.
- Existing Fernet encryption pattern (wearable/encryption.py) proves the codebase handles application-level encryption correctly.
- The Hindsight plugin (1774 lines) demonstrates the complete MemoryProvider subclass pattern with registration, background threads, prefetch, and session lifecycle.
- Infrastructure research confirms SET LOCAL + RLS is the correct pattern for multi-agent isolation.
- No SQLite anywhere -- PostgreSQL + asyncpg + pgvector + TimescaleDB exclusively.
