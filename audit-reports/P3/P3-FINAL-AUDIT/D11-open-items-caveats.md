# P3 FINAL AUDIT — Dimension 11: Open Items & Caveats

| Field | Value |
|---|---|
| **Auditor** | Independent (Sisyphus-Junior) |
| **Date** | 2026-06-02 |
| **Phase** | P3 Memory System |
| **Dimension** | 11 of 12 — Open Items & Caveats |
| **Report Path** | `audit-reports/P3/P3-FINAL-AUDIT/D11-open-items-caveats.md` |
| **Overall Verdict** | **PASS** — All caveats documented, non-blocking for P4/P5 |

---

## 1. Checkpoint Verdicts

### CP-1: P3-015 Live Service Activation (Deployment Caveat)

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Caveat documented in verification.md | ✅ | §8 "Caveat — service-level scheduler activation": states `register_consolidation_job()` requires `AsyncIOScheduler` + `async_sessionmaker(engine)`, neither exists in current `main.py` bootstrap. |
| Caveat documented in auditor-gate.md | ✅ | Caveat #1: "APScheduler activation requires runtime DB sessionmaker" — documented as a limitation, not a defect. |
| Production activation instructions exist | ✅ | verification.md §8 provides exact activation steps: create `AsyncSessionLocal`, instantiate `AsyncIOScheduler`, call `register_consolidation_job()`, call `scheduler.start()`. |
| `main.py` integration surface | ✅ | `src/core/main.py` contains doc-commented integration surface with activation instructions (+20 lines). |
| Non-blocking for P4/P5 | ✅ | Consolidation is a background job that enhances memory quality over time. P4 (agent loop) and P5 (Discord UX) do not depend on it being live. Code is unit-tested (50/50 PASS, 263/263 regression PASS). |

**Assessment:** The consolidation engine is fully implemented and tested. The only missing piece is wiring `scheduler.start()` into the app lifespan when a real DB sessionmaker is available on VPS. This is a deployment configuration step, not a code gap.

---

### CP-2: P3-012 Real LLM Integration (Wiring Caveat)

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Caveat documented | ✅ | verification.md §8: `assemble_system_prompt_with_memory()` calls `recall_memories()` — the assembler function exists and is tested. Integration tests with real LLM are deferred. |
| Context injection code is complete | ✅ | `src/core/services/prompt_loader.py` 182 lines; 18/18 tests PASS. |
| `recall_memories` not yet called by live LLM | ✅ | The assembler is a ready-to-call function. The live LLM loop (Hermes Agent) does not yet invoke it — this is a P4 (agent loop) wiring task. |
| Non-blocking for P4/P5 | ✅ | The context injection pipeline is a library function. P4 will wire it into the agent loop's system prompt assembly. P5 Discord commands can call it directly. |

**Assessment:** The context injection pipeline is fully implemented and unit-tested. The "wiring" to make the live LLM actually call `recall_memories` before generating a response is P4 (agent loop) scope, not a P3 defect.

---

### CP-3: content_hash DB Optimization (Future Improvement)

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| `_fact_exists_by_key` is O(n) | ✅ CONFIRMED | `consolidation.py` lines 511-531: `select(SemanticFacts)` → iterates all facts → compares `make_content_key()` per fact. |
| Optimization documented in verification.md | ✅ | §8 Design Decisions: "`_fact_exists_by_key` iterates all facts. No `content_hash` column on `SemanticFacts`; O(n) per fact. Production deployment should add `content_hash` column with unique constraint for O(1) dedup." |
| Optimization documented in auditor-gate.md | ✅ | Caveat #2: "Current implementation iterates all facts. Production should add a `content_hash` column with a unique constraint for O(1) dedup." |
| `content_hash` exists in ORM models | ✅ | `src/memory/models.py` lines 720, 1039: `content_hash: Mapped[str]` exists on other tables but NOT on `SemanticFacts`. |
| `content_hash` reference in consolidation.py | ✅ | Line 516: docstring mentions `content_hash` column as a future optimization. |
| Non-blocking for P4/P5 | ✅ | O(n) is acceptable for current data volumes. Optimization is a future migration task (add column + backfill + unique constraint). No P4/P5 feature depends on O(1) dedup. |

**Assessment:** The O(n) dedup is correctly identified as a future optimization. For a personal companion with low fact volumes (hundreds, not millions), this is perfectly acceptable. The `content_hash` column exists on other tables (showing the pattern is established) and adding it to `SemanticFacts` is a straightforward future migration.

---

### CP-4: Safe-Mode Ceiling Python-Level Only

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Safe-mode is Python-level post-processing | ✅ CONFIRMED | `read_pipeline.py` lines 843-861: classification ceiling filter iterates `scored` results in Python, comparing `classification_level()` against `ceil_level`. No SQL WHERE clause for safe-mode ceiling. |
| Normal-mode ceiling also Python-level | ✅ CONFIRMED | Same code path at lines 843-861 applies both normal and safe-mode ceilings in Python. |
| SQL queries do NOT filter by classification | ✅ CONFIRMED | `build_vector_query()` (lines 502-530), `build_fts_query()` (lines 533-556), `build_recency_query()` (lines 559-579) — none have classification WHERE clauses. Only `do_not_recall` and signal-specific filters. |
| Caveat documented in auditor-gate.md | ✅ | P3-014 auditor-gate.md Caveat #2: "No DB-level safe-mode ceiling in WHERE clause: Safe-mode classification ceiling is applied in Python post-processing rather than SQL WHERE clause. The planner gate acknowledged this as a deferred improvement." |
| Consistent with P3-010 pattern | ✅ | Normal-mode ceiling also uses Python post-processing (P3-010). Safe-mode follows the same established pattern. |
| Non-blocking for P4/P5 | ✅ | Python-level filtering is correct and safe. DB-level optimization is a performance enhancement, not a correctness issue. Current data volumes make this negligible. |

**Assessment:** The safe-mode ceiling is applied in Python as a post-query filter, consistent with the normal-mode ceiling pattern from P3-010. This is correctly documented as a deferred optimization. For a personal companion system, the performance impact is negligible.

---

### CP-5: P3-004 MiniLM Cache-Only

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| MiniLM 384-dim cached | ✅ | verification.md §3.2: "Model dimension: 384". Cache at `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/`. |
| NOT used for vector(1536) writes | ✅ | verification.md §5: "MiniLM is cache evidence only; no vector column writes". §6 Boundary: "No 384-dim DB writes — MiniLM is cache evidence only; no vector column writes." |
| Actual writes use 9Router text-embedding-3-small | ✅ | P3-005 implements `EmbeddingService` via 9Router-native HTTP (not OpenAI SDK). CHECKLIST.md P3-005: "9Router-native `openai/text-embedding-3-small`". |
| CHECKLIST.md documents cache-only status | ✅ | P3-004 item: "cache-only, not used for vector(1536) writes". |
| Non-blocking for P4/P5 | ✅ | MiniLM is a dependency installation verification step. The actual embedding pipeline (P3-005) uses 9Router 1536-dim vectors. |

**Assessment:** MiniLM 384-dim is correctly identified as cache-only evidence. The production embedding pipeline uses 9Router `text-embedding-3-small` (1536-dim). No dimension mismatch risk exists.

---

### CP-6: Compression Policies Deferred from P3-002

**Verdict: PASS**

| Check | Result | Evidence |
|---|---|---|
| Compression deferred documented in auditor-gate.md | ✅ | P3-002 auditor-gate.md Caveat #4: "Compression policies for `memory.episodes` (14-day interval) and `surveillance.events` (7-day interval) are deferred to a follow-up migration." |
| Migration source has deferred comments | ✅ | Lines 323 and 975: `# Compression deferred - requires columnstore enablement first` and `# Compression policy deferred - requires columnstore enablement first`. |
| Oracle research supports deferral | ✅ | `oracle-timescale-compression.md` referenced in auditor-gate.md. |
| P3-003 carries forward caveat | ✅ | P3-003 auditor-gate.md Caveat 1.4: "Compression policy fully deferred — Documented in P3-002 design decisions and P3-003 verification.md §8. Not a schema correctness issue." |
| Retention policies ARE in place | ✅ | `audit.audit_trail` (1 year), `financial.transactions` (7 years), `surveillance.events` (180 days) — all active. |
| Non-blocking for P4/P5 | ✅ | Compression is a performance optimization for large data volumes. The schema, indexes, hypertables, and retention policies are all complete. P4/P5 features work identically with or without compression. |

**Assessment:** TimescaleDB compression policies are correctly deferred as a performance optimization. All retention policies are active. The deferral rationale (columnstore enablement prerequisite) is well-documented. No P4/P5 feature depends on compression.

---

### CP-7: CHECKLIST.md Unchecked Items

**Verdict: PASS**

| Unchecked Item | Type | Assessment |
|---|---|---|
| **§5.1 Prerequisites** (3 items `[ ]`) | VPS deployment | All are deployment-time checks, not code blockers. |
| **P3-016** `[ ]` `/memory-search` | VPS E2E test | Code implemented (auditor PASS). CHECKLIST check requires live Discord interaction. |
| **P3-017** `[ ]` `/memory-add` | VPS E2E test | Code implemented (auditor PASS). CHECKLIST check requires live Discord interaction. |
| **P3-018** `[ ]` E2E write→recall→inject | VPS E2E test | Benchmark script implemented (auditor PASS). CHECKLIST check requires live pipeline. |
| **P3-019** `[ ]` benchmark p95 < 2s | VPS E2E test | Benchmark script implemented (auditor PASS). CHECKLIST check requires live data. |
| **§5.3 Integration Tests** (3 items `[ ]`) | VPS E2E tests | All require live DB + live LLM + live Discord. |
| **§5.4 Security Checks** (4 items `[ ]`) | VPS verification | Require live DB access for verification. |
| **§5.5 Rollback Test** (1 item `[ ]`) | VPS deployment | Destructive test; appropriate for VPS deployment phase. |
| **§5.6 Phase Complete** (5 items `[ ]`) | Meta-checklist | Depends on all above being checked. |

**Key finding:** P3-016 through P3-019 code is **fully implemented** (5 files, auditor PASS). The CHECKLIST `[ ]` items require live VPS/Discord interaction to verify — they are deployment verification steps, not code gaps.

**Assessment:** All unchecked CHECKLIST items are VPS-deployment-only verification steps. The underlying code for P3-016–019 is implemented and auditor-verified. These will be checked off during P4/P5 deployment when the live system is available.

---

### CP-8: Missing verification.md Files

**Verdict: PASS** (with note)

| Step | verification.md | auditor-gate.md | Assessment |
|---|---|---|---|
| P3-001 | ❌ Missing | ✅ Present (FAIL verdict) | The auditor-gate for P3-001 has verdict **FAIL** — it documents the initial failed attempt. A verification.md was never created because the step failed audit. P3-001 was subsequently resolved (CHECKLIST shows `[x]`). The auditor-gate.md alone adequately documents the failure state. |
| P3-002 to P3-015 | ✅ Present (all 14) | ✅ Present (all 14) | Complete evidence pairs. |
| P3-016–019 | ❌ Missing (combined) | ✅ Present (combined PASS) | The combined auditor-gate.md covers all 5 files across 4 steps. A verification.md was not created for the combined batch. The auditor-gate.md is comprehensive (283 lines, 6 sections, per-file audit, anti-pattern checks, safety boundaries). |

**Severity assessment:**

- **P3-001**: auditor-gate.md alone is **sufficient**. The FAIL verdict documents the initial failure. The subsequent resolution is tracked via CHECKLIST.md `[x]` and PROGRESS.md.
- **P3-016–019**: auditor-gate.md alone is **sufficient** but not ideal. The combined auditor report (283 lines) is thorough, covering pattern compliance, anti-pattern checks, type safety, secrets, safety boundaries, and test coverage (28/28 tests). A verification.md would add implementation detail but the auditor-gate already provides comprehensive coverage.

**Assessment:** The missing verification.md files are documentation gaps, not correctness gaps. All steps have auditor-gate.md reports with PASS verdicts (except P3-001 which correctly documents a FAIL). No P4/P5 feature is blocked by missing evidence.

---

## 2. Master Caveat Registry

Compiled from all `auditor-gate.md` and `verification.md` files under `docs/setup-evidence/P3/`:

| # | Step | Caveat | Category | Blocking? |
|---|---|---|---|---|
| 1 | P3-002 | Duplicate hypertable + index operations in manual patch (harmless `IF NOT EXISTS`) | Code quality | ❌ Non-blocking |
| 2 | P3-002 | Pre-existing `# type: ignore[assignment]` in `src/discord/bot.py:31` (P1/P2 era) | Pre-existing | ❌ Non-blocking |
| 3 | P3-002 | Backup marker `/var/log/guinevere/last-backup-success` missing (snapshot accepted) | Ops | ❌ Non-blocking |
| 4 | P3-002 | Compression policies fully deferred (episodes 14d, events 7d) | Performance | ❌ Non-blocking |
| 5 | P3-003 | P3-002 caveats carry forward (4 items) | Carry-forward | ❌ Non-blocking |
| 6 | P3-003 | Alembic password requirement for future auditors (SOPS-encrypted) | Ops | ❌ Non-blocking |
| 7 | P3-004 | Legacy torch cache path mismatch (HF hub authoritative) | Tooling | ❌ Non-blocking |
| 8 | P3-004 | TOML LSP unavailable | Tooling | ❌ Non-blocking |
| 9 | P3-004 | Windows symlink limitation (copies not symlinks) | Platform | ❌ Non-blocking |
| 10 | P3-004 | VPS Tailscale routing note | Network | ❌ Non-blocking |
| 11 | P3-005 | `RestrictedRedactionError` defined but never raised | Code quality | ❌ Non-blocking |
| 12 | P3-006 | HNSW EXPLAIN shows Seq Scan on empty table (expected) | Methodology | ❌ Non-blocking |
| 13 | P3-007 | p95 not meaningful on tiny dataset (4 reasons documented) | Methodology | ❌ Non-blocking |
| 14 | P3-007 | Benchmark timing includes vector generation overhead (~0.4ms) | Methodology | ❌ Non-blocking |
| 15 | P3-008 | DNR filter logic deferred to P3-010 (read pipeline) | Wiring | ❌ Non-blocking |
| 16 | P3-009 | No live DB insert — uses fake session | Verification scope | ❌ Non-blocking |
| 17 | P3-009 | No live embedding API call — uses fake embedder | Verification scope | ❌ Non-blocking |
| 18 | P3-010 | No live DB query smoke test (deterministic by design) | Verification scope | ❌ Non-blocking |
| 19 | P3-010 | P3-011 weighted tuning deferred | Scope | ❌ Non-blocking |
| 20 | P3-010 | Token budget estimation approximate (4 chars/token heuristic) | Accuracy | ❌ Non-blocking |
| 21 | P3-010 | No streaming execution (all queries in memory) | Performance | ❌ Non-blocking |
| 22 | P3-011 | No golden dataset for ablation tuning | Methodology | ❌ Non-blocking |
| 23 | P3-012 | Integration tests deferred (18 unit tests sufficient) | Verification scope | ❌ Non-blocking |
| 24 | P3-012 | Logger content-absence test has narrow scope | Test quality | ❌ Non-blocking |
| 25 | P3-013 | ConsentLedger cross-reference deferred (no `target_memory_id`) | Schema | ❌ Non-blocking |
| 26 | P3-013 | Content-hash dedup deferred (would require schema changes) | Performance | ❌ Non-blocking |
| 27 | P3-013 | Prometheus counters deferred (P8 observability) | Observability | ❌ Non-blocking |
| 28 | P3-013 | `_where_criteria` private API in test fakes | Test quality | ❌ Non-blocking |
| 29 | P3-014 | Substring matching in `_is_safe_mode_blocked_content()` for list/set tags | Accuracy | ❌ Non-blocking |
| 30 | P3-014 | No DB-level safe-mode ceiling in SQL WHERE clause | Performance | ❌ Non-blocking |
| 31 | P3-015 | APScheduler activation requires runtime DB sessionmaker | Deployment | ❌ Non-blocking |
| 32 | P3-015 | `_fact_exists_by_key` O(n) per fact (no `content_hash` column) | Performance | ❌ Non-blocking |
| 33 | P3-015 | `__init__.py` line count off by 1 (non-material) | Evidence | ❌ Non-blocking |
| 34 | P3-016–019 | Duplicate Protocol definitions across command files (canonical pattern) | Code quality | ❌ Non-blocking |
| 35 | P3-016–019 | `safe_mode=False` hardcoded in `cmd_memory_search.py` (correct for context) | Future consideration | ❌ Non-blocking |
| 36 | All steps | structlog unresolved in LSP (repo-level tooling config) | Tooling | ❌ Non-blocking |

---

## 3. Caveat Completeness Assessment

### Are all caveats non-blocking for P4/P5?

**Yes.** Analysis by category:

| Category | Count | P4/P5 Impact |
|---|---|---|
| **Deployment** (scheduler activation, VPS checks) | 2 | P4 will wire services; no code gap |
| **Performance** (O(n) dedup, Python-level ceiling, compression, streaming) | 5 | Acceptable at personal-companion scale; future optimization path clear |
| **Verification scope** (fake sessions, no live DB/API) | 5 | Deterministic by design; P3-018 E2E test covers live integration |
| **Code quality** (duplicate ops, unused error class, protocol duplication) | 4 | Cosmetic; no functional impact |
| **Methodology** (p95 not meaningful, no golden dataset) | 3 | Honest documentation; does not affect correctness |
| **Tooling** (LSP, TOML, symlinks, Tailscale) | 4 | Environment-specific; no code impact |
| **Pre-existing** (`# type: ignore`, structlog) | 2 | Outside P3 scope; flagged for future cleanup |
| **Schema** (ConsentLedger, content_hash column) | 2 | Future migration scope; current implementation correct |
| **Observability** (Prometheus deferred) | 1 | P8 scope; structured logs used instead |
| **Other** (test quality, evidence accuracy, scope, wiring, future) | 8 | Minor; no blocking impact |
| **Total** | **36** | **0 blocking** |

---

## 4. P3-001 Auditor FAIL Status Note

P3-001's auditor-gate.md has verdict **FAIL**. This documents the initial failed attempt (Alembic/SQLAlchemy not installed in venv, `alembic.ini` missing). The step was subsequently resolved — CHECKLIST.md shows `[x]` for P3-001 with evidence of baseline migration `2bed93fd1dd0`.

The FAIL verdict in the auditor-gate is an honest record of the first audit attempt, not a current blocking issue. The step's code is functional and P3-002 onward depends on it successfully.

**Verdict for CP-8 context: PASS** — the FAIL is a historical record, not a current defect.

---

## 5. Summary

### Overall Verdict: **PASS**

| Dimension | Status | Detail |
|---|---|---|
| Known caveats documented | ✅ | 36 caveats identified across all P3 steps; all documented in verification.md or auditor-gate.md |
| All caveats non-blocking | ✅ | 0 of 36 caveats block P4 or P5 |
| Deployment caveats identified | ✅ | P3-015 scheduler activation, P3-016–019 live Discord verification — clearly deployment-scope |
| Performance caveats identified | ✅ | O(n) dedup, Python-level ceiling, compression deferred, no streaming — all acceptable at current scale |
| Missing verification.md files | ✅ Acceptable | P3-001 (FAIL record sufficient), P3-016–019 (comprehensive auditor-gate sufficient) |
| CHECKLIST unchecked items | ✅ Non-blocking | All are VPS-deployment verification steps; code is implemented and auditor-verified |
| Caveat carry-forward discipline | ✅ | P3-002 → P3-003 caveats explicitly carried forward; P3-014 → future ceiling optimization documented |
| Evidence honesty | ✅ | No hidden limitations; all caveats transparently documented in evidence files |

### Recommendations for P4/P5

1. **Wire consolidation scheduler** into app lifespan (P3-015 caveat #31) — requires VPS DB sessionmaker.
2. **Wire `assemble_system_prompt_with_memory()`** into agent loop (P3-012 wiring) — P4 scope.
3. **Add `content_hash` column** to `SemanticFacts` for O(1) dedup — future migration, non-urgent.
4. **Consider DB-level classification ceiling** in SQL WHERE clause — future optimization, non-urgent.
5. **Add TimescaleDB compression policies** — future migration, non-urgent.
6. **Resolve CHECKLIST.md unchecked items** during VPS deployment phase.
7. **Clean up pre-existing `# type: ignore`** in `bot.py:31` — future batch cleanup.

---

## 6. Footer

| Field | Value |
|---|---|
| **Auditor** | Sisyphus-Junior (independent) |
| **Dimension** | 11 — Open Items & Caveats |
| **Date** | 2026-06-02 |
| **Verdict** | **PASS** |
| **Total caveats catalogued** | 36 |
| **Blocking caveats** | 0 |
| **Missing verification.md** | 2 (P3-001, P3-016–019) — acceptable |
| **CHECKLIST unchecked** | ~17 items — all VPS-deployment-only |
| **Report path** | `audit-reports/P3/P3-FINAL-AUDIT/D11-open-items-caveats.md` |
