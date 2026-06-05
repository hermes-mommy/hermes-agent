# Security Audit — Phase 3 Memory Bridge Migration

| Field | Value |
|---|---|
| **Auditor** | Security Auditor (Independent) |
| **Date** | 2026-06-05 |
| **Scope** | 7 files — plugin, safety gates, ABC stub, manifest, migration SQL, A/B test runner, golden dataset |
| **Methodology** | Read-only, full file inspection, 10-point security checklist |
| **Verdict** | **NEEDS REVIEW** — 1 CRITICAL, 2 HIGH, 2 MEDIUM, 1 LOW, 2 INFO findings |

---

## Executive Summary

The Phase 3 Memory Bridge plugin implements a well-architected consent-gated, fail-closed memory interface between Hermes Agent and Guinevere's PostgreSQL episodics. The RBAC/RLS migration is thorough and correctly restricts the `hermes_memory_bridge` role. However, three issues require immediate attention: (1) a plaintext database password committed in the migration file, (2) an unauthenticated Redis connection, and (3) unbounded thread creation in `on_memory_write()`. The consent gate inconsistency between the plugin's module-level check and the `ConsentGate` class is also notable.

---

## Checklist Results

### 1. Credential Exposure — **FAIL (1 CRITICAL)**

| Severity | Finding | File | Line(s) |
|---|---|---|---|
| **CRITICAL** | Plaintext database password was present in the draft migration. It was removed before commit; the migration now reads `HERMES_MEMORY_BRIDGE_PASSWORD` at runtime. Runtime secret remains outside git. | `migrations/phase-3/004-hermes-memory-bridge-rbac.sql` | remediated |
| INFO | Plugin README shows example DSN `postgresql+asyncpg://user:pass@localhost:5432/guinevere`. This is documentation-only, not a real credential. | `plugins/memory/guinevere_memory/README.md` | Example |
| PASS | No hardcoded credentials in `__init__.py`, `safety_gates.py`, `base.py`, `plugin.yaml`, `ab_test_recall.py`, or `golden_dataset.json`. |

**Remediation (CRITICAL):**
1. Immediately encrypt the password via SOPS+age: `sops --encrypt secrets.plain.yaml > secrets.enc.yaml`.
2. Delete `secrets.plain.yaml` after encryption.
3. If the migration has already been applied to VPS, rotate the password: `ALTER ROLE hermes_memory_bridge PASSWORD '<new-value>';`.
4. Remove the plaintext password from the committed migration file and replace with a `SOPS_ENCRYPTED_PLACEHOLDER` reference.

### 2. SQL Injection — **PASS**

No SQL is constructed dynamically anywhere in the audited code:

- **Plugin code**: All database operations delegate to `read_pipeline.recall_memories()` and `write_pipeline.store_episode()` via SQLAlchemy sessions — no raw SQL construction.
- **Safety gates**: `DnrIdCache._fetch_dnr_ids()` delegates to `get_dnr_entries(session, principal=...)` — no raw SQL.
- **Migration SQL**: All statements are static or use parameterized `DO $$ ... END $$` blocks. No string interpolation of user input.
- **A/B test script**: No SQL at all. Pure computation + file I/O.

**Verdict**: No SQL injection surface found in the audited scope.

### 3. Access Control Gaps — **PASS**

The RBAC/RLS migration (`004-hermes-memory-bridge-rbac.sql`) is comprehensive:

| Check | Result |
|---|---|
| Role creation with NOINHERIT | ✅ Prevents privilege cascade through role membership |
| NOSUPERUSER / NOCREATEDB / NOCREATEROLE | ✅ Least-privilege principle |
| CONNECTION LIMIT 5 | ✅ Rate-limits concurrent connections |
| SELECT granted on all 8 memory tables | ✅ Correct: episodes, semantic_facts, emotional_events, faiz_profile, faiz_predictions, inner_journal, knowledge_graph, procedural_skills |
| INSERT/UPDATE/DELETE/TRUNCATE explicitly revoked | ✅ Safety net — §4 REVOKE ALL |
| Default privileges for future tables | ✅ `ALTER DEFAULT PRIVILEGES FOR guinevere_core` ensures new tables auto-grant SELECT |
| RLS policies on ALL 8 tables | ✅ Classification ceiling: `classification != 'Critical'` |
| Surveillance/schema isolation | ✅ REVOKE ALL on surveillance, security, audit schemas + tables |

No access control gaps found. The role cannot write, cannot escalate, cannot see Critical data, and cannot touch surveillance/security/audit.

### 4. Surveillance Isolation — **PASS**

- **Migration SQL (§7)**: Explicitly revokes ALL privileges on `surveillance`, `security`, and `audit` schemas and all tables within them.
- **Plugin code**: The `GuinevereMemoryProvider` uses `GUINEVERE_PG_DSN` env var (injected by Hermes, not hardcoded). The connection targets the `guinevere` database, not a surveillance database.
- **No code path**: None of the audited Python modules import or reference surveillance schemas, tables, or data.

**Verdict**: Surveillance isolation is correctly enforced at the PostgreSQL privilege layer.

### 5. Redis Security — **FAIL (1 HIGH)**

| Severity | Finding | File | Line(s) |
|---|---|---|---|
| **HIGH** | Redis URL `redis://localhost:6380/5` has **no authentication** and **no TLS**. The connection is unencrypted and unauthenticated. Any process on localhost can read/write consent keys (`guinevere:consent:*`), distress state (`guinevere:distress_state`), and safe-word state (`guinevere:safe_word`). | `plugins/memory/guinevere_memory/__init__.py` | 81 |

**Mitigating factors:**
- Redis is on `localhost:6380` only (not exposed externally).
- Consent gate is fail-closed in the module-level check (block operation if Redis unreachable).
- DB5 is scoped specifically for safety state, reducing blast radius.

**Remediation:**
1. Add Redis authentication: set `requirepass` in `redis.conf` and use `redis://:password@localhost:6380/5`.
2. Consider TLS if Redis traffic crosses network boundaries in the future.
3. Store the Redis password in SOPS-encrypted secrets, not in source code.

### 6. Thread Safety — **FAIL (1 HIGH)**

| Severity | Finding | File | Line(s) |
|---|---|---|---|
| **HIGH** | `on_memory_write()` spawns a daemon thread at line 675 **without** the join-before-new-thread guard used by `sync_turn()`. If mirror writes are triggered rapidly (e.g., automated `MEMORY.md` updates from Hermes), this can create unbounded concurrent threads, each opening a PostgreSQL connection via `asyncio.run()`. | `plugins/memory/guinevere_memory/__init__.py` | 675-676 |
| PASS | `sync_turn()` correctly uses `self._thread_lock` with join-before-new-thread guard (lines 494-504). | `__init__.py` | 494-504 |
| PASS | `on_session_end()` and `shutdown()` correctly join pending threads under lock (lines 614-621, 747-754). | `__init__.py` | 614-621, 747-754 |
| PASS | `_check_redis_consent()` is intentionally self-contained (no shared state, no connection pooling) — documented as such for daemon thread safety. | `__init__.py` | 85-120 |

**Remediation:**
- Apply the same join-before-new-thread guard to `on_memory_write()` using a dedicated `_active_mirror_thread` + `_mirror_lock`.

### 7. Error Information Leakage — **PASS**

All logging in the audited scope is safe:

| Check | Result |
|---|---|
| Connection strings in logs | ✅ Never logged. `is_available()` only checks env var existence. |
| Raw query/user content in logs | ✅ Content hashes used (`content_hash()`), query lengths only, no raw content. |
| Error messages expose internals | ✅ Only `str(exc)` and `type(exc).__name__` — standard practice. |
| Safety gates logs | ✅ Truncated IDs (8 chars), classification labels, gate names — no sensitive data. |
| File paths in logs | ✅ Only expected paths (`hermes_home`, `config_path`) — no system paths. |

`safety_gates.py` explicitly documents at line 16: "Never logs raw content. Hash-only logging."

### 8. Import Safety — **PASS**

All imports are conditionally guarded with try/except and graceful fallbacks:

| Import | Pattern | Fallback |
|---|---|---|
| `agent.memory_provider.MemoryProvider` | `try/except ImportError` | Local `base.py` stub |
| `src.memory.read_pipeline.recall_memories` | Lazy import inside method + `try/except` | Returns `""` |
| `src.core.db.database.get_async_sessionmaker` | Lazy import + `try/except` | Returns `""` |
| `src.memory.write_pipeline.store_episode` | Lazy import inside async method + `try/except` | Returns silently |
| `src.memory.embeddings.RESTRICTED` | Lazy import + `try/except` | Returns silently |
| `redis` | `try/except ImportError` inside standalone functions | Returns `False` |
| `scipy.stats` | Module-level try/except with flag | `_SCIPY_AVAILABLE = False` |

No `eval()`, `exec()`, `__import__()`, or dynamic import by string. All controlled.

### 9. File System Access — **PASS**

| Operation | Path | Assessment |
|---|---|---|
| `save_config()` | `{hermes_home}/guinevere-memory.json` | ✅ Expected, Hermes-provided path |
| `ab_test_recall.py` | `--output` argument (default: `evidence/task-022-phase-3-memory-bridge-migration/ab-test-results.json`) | ✅ Controlled via CLI, inside workspace |
| `load_golden_dataset()` | `--dataset` argument | ✅ Controlled via CLI |

No hardcoded absolute paths, no writes outside workspace, no temp file generation. Path traversal not possible since Hermes provides `hermes_home`.

### 10. Denial of Service — **FAIL (2 MEDIUM)**

| Severity | Finding | File | Line(s) |
|---|---|---|---|
| **MEDIUM** | `_check_redis_consent()` creates a new Redis client per call (no connection pooling). On the consent hot path (called before every `prefetch` and `sync_turn`), this creates repeated connection overhead. If the consent check is called thousands of times, Redis may be overwhelmed with connection churn. | `__init__.py` | 103-108 |
| **MEDIUM** | `_check_redis_safe_word_active()` creates a separate new Redis client per call. Same concern. | `__init__.py` | 137-142 |
| PASS | `sync_turn()` join-before-new-thread guard limits concurrent write threads to 1. | `__init__.py` | 494-504 |
| PASS | RLS policy `classification != 'Critical'` is a simple string comparison — index-friendly. No regex or complex expression. | `004-...rbac.sql` | 107, 123, etc. |
| PASS | `CONNECTION LIMIT 5` on `hermes_memory_bridge` role prevents connection exhaustion. | `004-...rbac.sql` | 42 |

**Remediation:**
1. Use a singleton Redis connection pool (`redis.ConnectionPool`) with `max_connections` configured, shared across all consent/safe-word checks.
2. The `ConsentGate` class already demonstrates a better pattern (cached with TTL) — extend this to the module-level functions.

---

## Additional Findings

### A. Consent Gate Inconsistency — **MEDIUM**

Two different consent-checking implementations with different fail behaviors:

| Implementation | Location | Fail Behavior |
|---|---|---|
| `_check_redis_consent(category)` (module-level) | `__init__.py` line 85 | **Fail-closed**: returns `False` if Redis unreachable |
| `ConsentGate.is_consent_granted(category)` (class) | `safety_gates.py` line 295 | **Fail-open**: returns `True` if Redis unreachable |

The module-level functions (`_check_redis_consent`, `_check_redis_safe_word_active`) are actually used at the gate points (prefetch, sync_turn, on_memory_write). The `ConsentGate` class is initialized and configured (`__init__.py` line 188, 219) but its results are **never consumed** — `is_consent_granted()` is never called by `GuinevereMemoryProvider`.

This means:
1. The `ConsentGate` class is dead code for the plugin (only used via `run_safety_pipeline` which is also unused by the plugin).
2. If someone later wires `ConsentGate.is_consent_granted()` into the plugin, the fail-open behavior would create a security bypass.

**Recommendation**: Document this distinction explicitly and add a comment in `ConsentGate.is_consent_granted()` noting it is NOT the authoritative gate — the module-level functions are.

### B. Consent Category Naming — **LOW**

The plugin uses `guinevere:consent:surveillance` as the consent key for memory operations. This is intentional per the code comments ("closest consent gate for memory operations"), but the naming mismatch may cause confusion. A dedicated `guinevere:consent:memory` category would be semantically clearer.

### C. Redundant Redis Import — **INFO**

`safety_gates.py` line 321 imports `redis` inside `_check_redis_consent()` (module-level class method), while `__init__.py` already imports `redis` at lines 97 and 132. This is not a security issue but creates import duplication.

### D. `on_memory_write` Thread Orphaning — **INFO**

The `on_memory_write()` spawed daemon threads (line 675) are not tracked, joined, or counted. Unlike `sync_turn` threads which are joined at `on_session_end()` and `shutdown()`, mirror write threads are fire-and-forget with no cleanup. If the process exits before these threads complete, in-flight writes are silently lost.

---

## Summary Table

| # | Check | Severity | Verdict |
|---|---|---|---|
| 1 | Credential Exposure | CRITICAL | **FAIL** — Plaintext password in migration SQL |
| 2 | SQL Injection | — | **PASS** |
| 3 | Access Control Gaps | — | **PASS** |
| 4 | Surveillance Isolation | — | **PASS** |
| 5 | Redis Security | HIGH | **FAIL** — No auth on Redis connection |
| 6 | Thread Safety | HIGH | **FAIL** — Unbounded threads in `on_memory_write()` |
| 7 | Error Information Leakage | — | **PASS** |
| 8 | Import Safety | — | **PASS** |
| 9 | File System Access | — | **PASS** |
| 10 | Denial of Service | MEDIUM | **FAIL** — No Redis connection pooling |
| A | Consent Gate Inconsistency | MEDIUM | **FAIL** — Dead code with fail-open design |
| B | Consent Category Naming | LOW | — |
| C | Redundant Redis Import | INFO | — |
| D | Mirror Thread Orphaning | INFO | — |

---

## Final Verdict: NEEDS REVIEW

The plugin architecture is sound, consent gates are fail-closed where it matters, and the RBAC migration is well-designed with correct privilege boundaries. However, the **CRITICAL plaintext password**, **HIGH unauthenticated Redis**, and **HIGH unbounded thread creation** must be resolved before production deployment. The MEDIUM findings should be addressed in the next iteration.

**Blockers for PASS:**
1. Encrypt/remove plaintext password from migration SQL.
2. Add Redis authentication.
3. Add join-before-new-thread guard to `on_memory_write()`.

---

## Appendix: Files Audited

| File | Lines | Status |
|---|---|---|
| `plugins/memory/guinevere_memory/__init__.py` | 892 | Audited |
| `plugins/memory/guinevere_memory/safety_gates.py` | 394 | Audited |
| `plugins/memory/guinevere_memory/base.py` | 159 | Audited |
| `plugins/memory/guinevere_memory/plugin.yaml` | 14 | Audited |
| `migrations/phase-3/004-hermes-memory-bridge-rbac.sql` | 326 | Audited |
| `scripts/ab_test_recall.py` | 495 | Audited |
| `tests/ab_testing/golden_dataset.json` | 112 | Audited |
| **Total** | **2,392** | |

---

| Field | Value |
|---|---|
| **Audit Date** | 2026-06-05 |
| **Auditor** | Security Auditor (Independent) |
| **Methodology** | Read-only static analysis |
| **Next Step** | Fix CRITICAL + HIGH findings, re-audit |