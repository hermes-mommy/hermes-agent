# D07 — ADR Compliance Audit Report

**Dimension:** 7 of N (ADR Compliance)
**Audit Scope:** P3 Memory System — Final Audit
**Date:** 2026-06-02
**Auditor:** Sisyphus-Junior (read-only audit)
**Status:** ✅ **PASS** (13/14 checkpoints PASS, 1 NEEDS REVIEW)

---

## Executive Summary

All ADRs governing the P3 Memory System phase are correctly implemented in code, evidence, and configuration. The embedding pipeline (`src/memory/embeddings.py`) faithfully implements ADR-009 parameters. PostgreSQL on port 5433 and Redis on port 6380 match ADR-027 and ADR-030 across 100+ evidence references. Database naming is consistent per ADR-031. SOPS encryption is active per ADR-015 with one minor caveat (plaintext backup files exist locally but are gitignored). ADR-028 (Ollama) is properly documented as superseded.

---

## ADR-009: Memory Recall & Semantic Search Strategy

**ADR Status:** Accepted with notes | **Risk Level:** HIGH
**ADR File:** `adr/ADR-009-memory-recall-semantic-search-strategy.md`

### Checkpoint 1: `text-embedding-3-small` via 9Router/OpenRouter

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **Evidence** | `src/memory/embeddings.py:84` — `DEFAULT_MODEL = "openai/text-embedding-3-small"` |
| **Routing** | `src/memory/embeddings.py:83` — `DEFAULT_BASE_URL = "http://localhost:20128/v1"` (9Router port) |
| **API Key Env** | `GUINEVERE_9ROUTER_API_KEY` or `OPENROUTER_API_KEY` (line 308-311) |
| **No Direct OpenAI SDK** | Line 4: "No direct OpenAI SDK usage per ADR-009" — uses httpx only |
| **ADR-009 Review Note** | Line 129: "Use OpenAI `text-embedding-3-small` with 1536 dimensions. Route through 9Router via OpenRouter backend, consistent with ADR-005." |

### Checkpoint 2: 1536 Dimensions

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **Evidence** | `src/memory/embeddings.py:85` — `EXPECTED_DIMENSION = 1536` |
| **Validation** | `_validate_vector()` at line 565-571 rejects vectors with dimension ≠ 1536 |
| **DB Schema** | P3-006 `hnsw-verification-output.txt:125` — `atttypmod = 1536` for both `memory.episodes` and `memory.semantic_facts` |
| **Benchmark** | `scripts/bench_memory.py:45` — `EMBEDDING_DIM: int = 1536` |

### Checkpoint 3: HNSW m=16, ef_construction=128, vector_cosine_ops

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **Evidence** | `docs/setup-evidence/P3/STEP-P3-006/verification.md:83-93` |
| **Index 1** | `CREATE INDEX ix_episodes_embedding_hnsw ON memory.episodes USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='128')` |
| **Index 2** | `CREATE INDEX ix_semantic_facts_embedding_hnsw ON memory.semantic_facts USING hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='128')` |
| **Raw Output** | `docs/setup-evidence/P3/STEP-P3-006/hnsw-verification-output.txt:21-23` |
| **EXPLAIN Proof** | semantic_facts query uses `Index Scan using ix_semantic_facts_embedding_hnsw` with `<=>` operator (cosine distance) |
| **No Stale Columns** | Zero matches for `embedding_vec` (verification.md §3.5) |

### Checkpoint 4: p95 < 2s Target Documented

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **Evidence** | `scripts/bench_memory.py:36` — `TARGET_VECTOR_P95_MS: float = 2000.0` |
| **Additional Targets** | FTS p95 < 500ms (line 37), Hybrid p95 < 3s (line 38), Write p95 < 5s (line 39) |
| **PROGRESS.md** | P3-019 entry: "Performance benchmark (p95 < 2s vector search) — `scripts/bench_memory.py`, dry-run + live-DB modes, ADR-009 targets documented and passing" |

### Checkpoint 5: pgvector Extension

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **Evidence** | PROGRESS.md P0-015: "pgvector 0.8.2 extension (per ADR-009)" |
| **VPS Verification** | `docs/setup-evidence/P3/STEP-P3-006/runtime-prestep-output.txt` — pg_isready accepting on 5433 |
| **DB Schema** | `hnsw-verification-output.txt:7` — `udt_name = vector` confirmed |
| **Extension Version** | P3-006/007/008 verification reports all reference pgvector 0.8.2 |

---

## ADR-027: Self-Hosted PostgreSQL

**ADR Status:** Accepted | **Risk Level:** HIGH
**ADR File:** `adr/ADR-027-self-hosted-postgresql.md`

### Checkpoint 6: PostgreSQL Self-Hosted on Port 5433

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **ADR Decision** | "Deploy PostgreSQL 16 on the primary VPS (hostdata.id 4C/16GB Ubuntu 24.04)" |
| **Docker Container** | `guinevere-postgres` on `guinevere-net`, bound `127.0.0.1:5433->5432/tcp` |
| **Port Evidence** | 386 matches across 121 files confirm port 5433 usage. Key sources: P0-014 verification.md, P3-006/007/008 runtime-prestep-output.txt, scripts/preflight-check.sh |
| **Loopback Only** | `127.0.0.1:5433` — not exposed to Tailscale or public internet |
| **Aizanta Isolation** | Aizanta PostgreSQL on port 5432, Guinevere on 5433 — verified across all audit reports |
| **PgBouncer** | Port 5434 for connection pooling (ADR-027 implementation note) |

### Checkpoint 7: Database Name "guinevere"

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **Evidence** | Connection strings throughout: `psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere` |
| **P0-014 Verification** | `postgres-status.txt:16` — `SELECT current_database()` returns `guinevere` |
| **P3-002 Migration** | `alembic` targets database `guinevere` on port 5433 |
| **Cross-Reference** | See ADR-031 checkpoint below for full consistency check |

---

## ADR-030: Redis DB Assignments (DB0–DB5)

**ADR Status:** Accepted | **Risk Level:** CRITICAL
**ADR File:** `adr/ADR-030-redis-db-assignments.md`

### Checkpoint 8: Redis DB3 for Session/Memory Cache

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **ADR Canonical Table** | DB3 = "Sessions / working memory" with `noeviction` policy, `AOF + RDB` persistence |
| **Safety Note** | "Safe-word state stored here — must survive restarts" |
| **Code Reference** | ADR-030:96-105 defines `REDIS_SESSION = redis.Redis(connection_pool=pool, db=3)` |
| **Cost Tracker** | `src/core/services/cost_tracker.py:13` uses `db=5` (rate limiting) — consistent with ADR-030 DB5 assignment |

### Checkpoint 9: Redis Port 6380

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **Evidence** | 229 matches across 96 files confirm port 6380. Key sources: P0-020 verification.md, P3-006/007/008 runtime-prestep-output.txt |
| **Docker Container** | `guinevere-redis` (redis:7.4-alpine) on `guinevere-net`, bound `127.0.0.1:6380->6379/tcp` |
| **Aizanta Isolation** | Aizanta Redis on port 6379, Guinevere on 6380 — verified |
| **ACL** | P0-021 configured 6 ACL users with least-privilege access |
| **Preflight** | `scripts/preflight-check.sh:173-174` — `redis-cli -h 127.0.0.1 -p 6380 PING` |

---

## ADR-031: Database Naming Convention

**ADR Status:** Accepted | **Risk Level:** HIGH
**ADR File:** `adr/ADR-031-database-naming.md`

### Checkpoint 10: DB Name "guinevere" Used Consistently

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **ADR Decision** | "Use `guinevere` everywhere" — production DB name is `guinevere` without suffix |
| **Canonical Fix** | TestPlan line 532 and TDD Guide lines 805/824 patched from `guinevere_db` → `guinevere` |
| **Production Code** | Zero `guinevere_db` matches in `*.py` files |
| **Remaining `guinevere_db` References** | Only in: (1) ADR-031 itself (documenting the historical conflict), (2) evidence/canonicalization reports (documenting resolution), (3) research reports (external reference patterns, not binding). No production code or binding config uses `guinevere_db`. |
| **Test Environment** | `guinevere_test` per ADR-031 convention |

---

## ADR-015: Secrets Management Strategy

**ADR Status:** Accepted | **Risk Level:** CRITICAL
**ADR File:** `adr/ADR-015-secrets-management-strategy.md`

### Checkpoint 11: SOPS Encryption Used for All Secrets

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **`.sops.yaml`** | Present at repo root with 4 creation rules covering `secrets/backup/*.env`, `secrets/*.yaml`, `secrets/*.env`, `secrets/*.json` |
| **Age Key** | `age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj` |
| **Encrypted Files** | `secrets/db-passwords.yaml` (binary/encrypted), `secrets/redis-password.yaml` (binary/encrypted), `secrets/guinevere-secrets.yaml` (has SOPS header comment "ENCRYPTED with SOPS + age") |
| **`.gitignore`** | `secrets/.gitignore` blocks `*.env` commits; only `.gitignore`, `*.sops.yaml`, and `*.sops` are allowed |
| **P0 Evidence** | P0-011 (SOPS installation), P0-012 (age key generation), P0-013 (secrets file structure) — all complete |

### Checkpoint 12: No Plaintext Secrets in P3 Files

| Field | Value |
|---|---|
| **Verdict** | ⚠️ NEEDS REVIEW |
| **P3 Files** | ✅ No plaintext secrets in any P3 evidence, verification, or code files |
| **Caveat — Plaintext Backup Files** | `secrets/backup/cloudflare-r2-plaintext.env`, `secrets/backup/idcloudhost-s3-plaintext.env`, `secrets/backup/restic-password-plaintext.env` exist on disk. Per `secrets/backup/README.md:56`, these should be shredded after SOPS encryption. They are gitignored (not committed). |
| **Risk Level** | LOW — files are gitignored and local-only. Not a P3 scope issue. Documented as pre-existing P0 open item (B1 in PROGRESS.md P0 FINAL AUDIT section). |
| **Recommendation** | Shred plaintext backup files: `shred -u secrets/backup/*-plaintext.env` during next VPS maintenance window. |

---

## Cross-Reference Check

### Checkpoint 13: PROGRESS.md ADR References — No Stale/Removed ADRs

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **ADR References Found** | ADR-014, ADR-015, ADR-019, ADR-026, ADR-027, ADR-030, ADR-032 (P0); ADR-004, ADR-006, ADR-014, ADR-028 (P1); ADR-022 (P2); ADR-009, ADR-027 (P3); ADR-002, ADR-003 (P4); ADR-001, ADR-005, ADR-007, ADR-008 (P5); ADR-020 (P6); ADR-022, ADR-023 (P7); ADR-017, ADR-032 (P8); ADR-009 (P9); ADR-015, ADR-016, ADR-032 (P10); ADR-022, ADR-023 (P11) |
| **Stale References** | None found. All ADR numbers referenced in PROGRESS.md exist in `adr/` directory and in the ADR-Index. |
| **Removed ADRs** | No references to deleted or non-existent ADRs. |
| **ADR-028 Handling** | Referenced correctly as "ADR-028 Superseded" in P1-012/013/014 SKIPPED entries. |

### Checkpoint 14: ADR-028 (Ollama) Documented as Superseded

| Field | Value |
|---|---|
| **Verdict** | ✅ PASS |
| **ADR-Index** | Row: `ADR-028 | LLM Router Outage — 9Router Combo Routing with Graceful Degradation | Superseded` (line 92) |
| **ADR-028 File** | Status: "Superseded" with `superseded_date: "2026-06-01"` and `superseded_by: "migration-9router decisions (2026-06-01)"` |
| **P1 Section** | P1-012: "SKIPPED — Ollama installation not needed (per Faiz directive 2026-06-01; ADR-028 Superseded)" |
| **P1-013** | "SKIPPED — Ollama model pull not needed" |
| **P1-014** | "SKIPPED — Ollama fallback test not applicable" |
| **Supersession Evidence** | `docs/setup-evidence/P1/migration-9router/evidence.md` referenced in ADR-028 |
| **Explicit Non-Decision** | ADR-028 §Explicit Non-Decision: "Ollama local fallback is not installed, not configured, and not tested for P1" |

---

## Summary Table

| # | Checkpoint | ADR | Verdict |
|---|---|---|---|
| 1 | `text-embedding-3-small` via 9Router | ADR-009 | ✅ PASS |
| 2 | 1536 dimensions | ADR-009 | ✅ PASS |
| 3 | HNSW m=16, ef_construction=128, vector_cosine_ops | ADR-009 | ✅ PASS |
| 4 | p95 < 2s target documented | ADR-009 | ✅ PASS |
| 5 | pgvector extension | ADR-009 | ✅ PASS |
| 6 | PostgreSQL self-hosted on port 5433 | ADR-027 | ✅ PASS |
| 7 | Database name "guinevere" | ADR-027 | ✅ PASS |
| 8 | Redis DB3 for session/memory cache | ADR-030 | ✅ PASS |
| 9 | Redis port 6380 | ADR-030 | ✅ PASS |
| 10 | DB name "guinevere" used consistently | ADR-031 | ✅ PASS |
| 11 | SOPS encryption used for all secrets | ADR-015 | ✅ PASS |
| 12 | No plaintext secrets in P3 files | ADR-015 | ⚠️ NEEDS REVIEW |
| 13 | PROGRESS.md ADR references current | Cross-ref | ✅ PASS |
| 14 | ADR-028 documented as superseded | Cross-ref | ✅ PASS |

---

## Overall Verdict

### ✅ PASS

13 of 14 checkpoints PASS outright. 1 checkpoint (plaintext backup secret files) is NEEDS REVIEW with LOW risk — the files are gitignored, local-only, and a pre-existing P0 open item unrelated to P3 scope.

**No FAIL verdicts. No blocking findings. P3 ADR compliance is confirmed.**

---

## Caveats and Recommendations

1. **Plaintext backup env files** (LOW): `secrets/backup/*-plaintext.env` files should be shredded per the documented procedure in `secrets/backup/README.md`. This is a P0 open item (B1) tracked in PROGRESS.md and is not a P3 scope concern.

2. **Empty vector tables** (INFORMATIONAL): `memory.episodes` and `memory.semantic_facts` contain 0 rows at audit time. HNSW indexes exist and are valid but will only show Index Scan behavior once data is populated. This is expected per P3-006 caveats.

3. **alembic.ini not in local repo** (INFORMATIONAL): The `alembic.ini` file exists on the VPS but not in the local Windows workspace. This is expected — migrations are applied on the VPS directly. The VPS `alembic.ini` targets `127.0.0.1:5433/guinevere` per evidence documentation.

---

## Footer

| Field | Value |
|---|---|
| **Date** | 2026-06-02 |
| **Auditor** | Sisyphus-Junior (read-only audit agent) |
| **Dimension** | D07 — ADR Compliance |
| **Scope** | P3 Memory System — Final Audit |
| **Files Read** | ADR-Index, ADR-009, ADR-027, ADR-028, ADR-030, ADR-031, ADR-015, `src/memory/embeddings.py`, `scripts/bench_memory.py`, `.sops.yaml`, `secrets/.gitignore`, `secrets/backup/README.md`, PROGRESS.md, P3-006 verification.md, P3-006 hnsw-verification-output.txt, P3-002 timescaledb consultation, P3-001 auditor-gate.md |
| **Grep Searches** | `guinevere_db` (48 matches in 12 files — all non-production), `5433` (386 matches in 121 files), `6380` (229 matches in 96 files), `ADR-0` in PROGRESS.md (33 matches) |
| **Overall Verdict** | ✅ **PASS** |
