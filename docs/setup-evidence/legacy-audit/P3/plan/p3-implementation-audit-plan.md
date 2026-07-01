# P3 (Memory Foundation) Implementation Audit Plan

**Date:** 2026-06-25
**Agent:** P3 Implementation Audit (plan synthesis, read-only)
**Repo:** C:/Users/faizz/guinevere (git main, commit 63c5285)
**Status:** PLAN -- ready for wave-1 and wave-2 execution

---

## Research Digest

Five research scouts executed read-only investigations. Key synthesized findings:

1. **Consolidation scheduler (P3-015) is dead in production.** `register_consolidation_job()` and `register_decay_job()` are commented out in `src/core/main.py:23-35`. No `AsyncIOScheduler` is started for these jobs. The KG ingestion scheduler (P16) IS wired alongside -- the pattern works, but consolidation was deliberately excluded. NR-4 from the prior 2026-06-02 final audit remains open 23 days later.

2. **Four core pipeline steps have zero live API or DB verification.** P3-005 (embeddings), P3-009 (write), P3-010 (read), P3-011 (ranking) all use mocked responses (`httpx.MockTransport`, `_FakeAsyncSession`, `_FakeRecallSession`). No real embedding API call or PostgreSQL query has ever been executed through these modules.

3. **P3-016-019 (combined batch) has no `verification.md`.** Only an `auditor-gate.md` exists. This batch covers Discord commands, E2E tests, and the benchmark script -- four steps without the standard implementation evidence artifact.

4. **48 ORM classes vs 47-table docstring claim.** The `KnowledgeGraph` table was added post-P3-002 (likely during P16) and the models.py header was never updated. The `memory` schema comment also says "8 tables" when it has 9.

5. **Massive ORM drift.** At least 20 columns exist in the DB (via migrations) but are absent from `models.py`: `procedural_skills.embedding` (p5_015), `procedural_skills.project_id/project_scope` (p19_001), `semantic_facts.project_id/project_scope` (p19_001), `knowledge_graph.project_id/project_scope` (p19_001), `loop_instances.checkpoint_data/error_message/phase/phase_artifacts/parent_loop_id` (p5_012), and `session_summaries` lacking `ClassificationMetaMixin` columns. Six `gamification.*` tables and three `life_kernel.*` tables have zero ORM models.

6. **Duplicated/mismatched DDL.** `surveillance.events` has conflicting chunk intervals (1d inline vs 7d in manual patch). HNSW index DDL is duplicated with `IF NOT EXISTS`. p5_012 tries to add `status` and `retry_count` columns that already exist.

7. **P19 project_id support exists in Episodes ORM but not in SemanticFacts or KnowledgeGraph.** The Episodes ORM (`models.py:179-187`) already has `project_id` + `project_scope` columns, and all three query builders (`build_vector_query`, `build_fts_query`, `build_recency_query`) in `read_pipeline.py:531-641` already support `project_id` filtering. P19 research was written from a stale snapshot claiming zero column support.

8. **P20 HARD STOP safe_mode propagation gap.** `graph.py:observe_node` calls `p18_adapter.MemoryRecallAdapter.recall()` without passing `safe_mode=True`. When HARD STOP is active, memory recall returns full content.

9. **All 235 memory tests use `FakeSession`/`AsyncMock`.** No test runs against a real PostgreSQL database. A schema-breaking migration would pass all tests.

10. **MiniLM 384-dim model (~87MB cached)** is never invoked by any `src/memory/` code path. The `sentence-transformers>=5.5` dependency pulls `torch` and `transformers` for no memory-pipeline benefit.

11. **Alembic chain converges to single head (`p19_002`).** Migration structure is sound with a clean 2-parent merge at `f47a9c2e8b1d`. No branch labels or multiple heads.

12. **`recall_memories` is wired into three active runtime subsystems** (life kernel via `p18_adapter`, Hermes plugins, prompt loader), making it a critical-path function with zero live-DB coverage.

---

## 1. Wave 1: Eight Audit Dimensions

Each dimension is a focused, verifiable audit scope. Every dimension produces a self-contained markdown file with findings, evidence references, severity tags, and a status verdict.

### DIM-01: Architecture-Implementation Consistency

**What to check:**
- Whether the `src/memory/` module structure (12 files, 284-line `__init__.py`, protocol-based typing, no `# type: ignore`, no `Any` misuse) matches the ADR-009 and P3-001..003 design.
- Whether the embedding pipeline is truly 9Router-native (no OpenAI SDK, httpx-based, ADR-009 compliant).
- Whether the multi-signal RRF fusion architecture (vector + FTS + recency + KG + FSRS) is correctly designed and each signal's weight/role is documented.
- Whether `EmbeddingService` protocol, `EpisodeSession`/`RecallSession` protocols, and `DNRSession` protocol are consistently used.
- Whether the `ContextCompactor` (P5) and `TierManager` (P18) have documented integration points in the pipeline, or are orphaned scaffolds.
- Whether the consolidation module's O(n) `_fact_exists_by_key` dedup (`consolidation.py:648-668`) is a design limitation that should be flagged.

**Key source files to inspect:**
- `src/memory/__init__.py` (exports audit)
- `src/memory/embeddings.py` (httpx/OpenRouter compliance)
- `src/memory/write_pipeline.py` (protocol usage)
- `src/memory/read_pipeline.py` (RRF fusion design)
- `src/memory/dnr.py` (authorization design)
- `src/memory/consolidation.py` (dedup efficiency)
- `src/memory/compaction.py` (integration point verification)
- `src/memory/tiers.py` (scaffold or integrated?)
- `src/memory/spaced_repetition.py` (FSRS-6 thin wrapper)
- `docs/20-security/ADR-009.md` or equivalent design doc
- Prior audit: `audit-reports/P3/P3-FINAL-AUDIT/D08-architecture-consistency.md`

**Expected output:** Architecture gaps or DELETEs with severity.

---

### DIM-02: Evidence-Documentation Consistency

**What to check:**
- Whether every P3 step (P3-001 through P3-019) has a verification.md with real output or honest caveats.
- Whether the P3-016-019 missing verification.md gap is the only structural evidence gap, or if others exist.
- Whether `CHECKLIST.md` sections 5.1, 5.3, 5.4, 5.5, 5.6 remain unchecked (20+ items) and what they cover.
- Whether `PROGRESS.md` P3 descriptions are accurate and reference live evidence paths.
- Whether the claim-type classification (LIVE-DB vs LOCAL vs DRY-RUN) is honest and consistent.
- Whether the 5 NR items from the prior final audit (NR-1 through NR-5) remain open.
- Whether any other evidence files have encoding issues like P3-004's binary-garbled `verification-output.txt`.
- Whether the `research-004-010/` empty directory is an abandoned artifact.

**Key source files to inspect:**
- `docs/setup-evidence/P3/STEP-P3-*/verification.md` (all 15 existing)
- `docs/setup-evidence/P3/STEP-P3-016-019/auditor-gate.md` (only evidence)
- `docs/setup-evidence/P3/batch-plan-*.md` (4 files)
- `CHECKLIST.md` sections 5.1-5.6
- `PROGRESS.md` P3 section
- `audit-reports/P3/P3-FINAL-AUDIT/D01-completeness.md`
- `audit-reports/P3/P3-FINAL-AUDIT/P3-FINAL-AUDIT.md` (NR items)

**Expected output:** List of evidence gaps, stale docs, encoding issues, and unchecked checklist items with severity.

---

### DIM-03: DB Schema and Migration Chain Integrity

**What to check:**
- Whether the migration chain converges to a single head (p19_002 confirmed).
- Whether the 2-parent merge at `f47a9c2e8b1d` is structurally correct.
- Whether ORM models.py `__tablename__` entries match migration DDL table creations.
- Whether every column in the migration DDL has a corresponding ORM attribute (and vice versa) -- **drift analysis**.
- Whether `gamification` schema is absent from `GUINEVERE_SCHEMAS` in `alembic/env.py:19-24` (COSMETIC gap).
- Whether `surveillance.events` hypertable chunk interval is 1d or 7d (duplicated DDL conflict).
- Whether `life_kernel.*` (3 tables) and `gamification.*` (6 tables) have zero ORM models.
- Whether `SessionSummary.ClassificationMetaMixin` columns were ever migrated or only exist via `metadata.create_all()`.
- Whether p5_012's duplicate column adds (`status`, `retry_count`) indicate poor migration coordination.
- Whether the `p5_012` header comment is misleading (lists one parent instead of two).

**Key source files to inspect:**
- `alembic/env.py`
- `alembic/versions/e401bb5fd274_initial_schema_47_tables.py`
- `alembic/versions/65f863220922_add_search_vector_do_not_recall.py`
- `alembic/versions/p5_012_extend_loop_instances.py`
- `alembic/versions/p5_015_add_skill_embedding.py`
- `alembic/versions/p5_024_*.py`
- `alembic/versions/p6_gamification_schema.py`
- `alembic/versions/p18_add_memory_tiers_fsrs.py`
- `alembic/versions/p20_001_life_kernel_schema.py`
- `alembic/versions/p19_001_project_namespaces.py`
- `alembic/versions/p19_002_project_id_not_null.py`
- `alembic/versions/p5_extend_loops.py`
- `alembic/versions/p5_add_loop_indexes.py`
- `alembic/versions/7239fd4b3b5a_*.py`
- `src/memory/models.py` (full ORM audit)
- `src/memory/db.py` (connection config)
- Prior audit: `audit-reports/P3/P3-FINAL-AUDIT/D03-database-integrity.md`

**Expected output:** List of ORM drift items, DDL anomalies, missing models, and structural issues with severity.

---

### DIM-04: Read/Write Pipeline Correctness

**What to check:**
- Whether `store_episode()` (write_pipeline.py:111-237) correctly handles all parameters: classification defaults, Critical fail-closed, embedding via `aembed()`, DNR default False, project_id/scope pass-through, metadata-only logging.
- Whether `recall_memories()` (read_pipeline.py:801-920) correctly handles: project_id filtering, DNR exclusion, classification ceiling, safe-mode content substitution, token budget enforcement, multi-signal RRF fusion (vector + FTS + KG + FSRS).
- Whether `build_safe_content()` (read_pipeline.py:377-475) correctly handles all classification levels, blocked-content detection, safe-mode placeholders.
- Whether `apply_token_budget()` (read_pipeline.py:493-523) correctly trims from bottom with 4 chars/token approximation.
- Whether all three query builders (`build_vector_query`, `build_fts_query`, `build_recency_query`) correctly include `do_not_recall` WHERE clause and `project_id` filter.
- Whether `dnr.mark_memory_dnr()` and `verify_recall_results_dnr_free()` are correctly integrated into the recall path.
- Whether the `HermesMemoryBridge` (P5 integration point) correctly calls both pipelines.
- Whether the `prompt_loader` (P3-012 context injection) correctly calls `recall_memories` and formats results.

**Key source files to inspect:**
- `src/memory/write_pipeline.py`
- `src/memory/read_pipeline.py`
- `src/memory/dnr.py`
- `src/memory/embeddings.py`
- `src/memory/models.py` (column definitions for episodes, semantic_facts)
- `src/hermes/_memory_bridge.py`
- `src/core/services/prompt_loader.py`
- `src/discord/cmd_memory_search.py`
- `src/discord/cmd_memory_add.py`
- Prior audit: `audit-reports/P3/P3-FINAL-AUDIT/D08-architecture-consistency.md`

**Expected output:** Pipeline correctness verification, edge-case coverage, integration gap analysis.

---

### DIM-05: DNR, Safe-Mode, and Security Boundaries

**What to check:**
- Whether DNR is enforced at THREE layers: SQL WHERE clause (query builders), pre-injection guard (`verify_recall_results_dnr_free`), and post-hoc marking (`mark_memory_dnr`).
- Whether DNR authorization restricts marking to `guinevere_core` only (`dnr.py:113`).
- Whether DNR audit events store metadata only (reason_hash, reason_length), never raw reason.
- Whether `verify_recall_results_dnr_free()` (dnr.py:385-419) correctly fails closed on `do_not_recall=True` (bool or string "true").
- Whether safe-mode (`_SAFE_MODE_CEILING`) correctly downgrades classification: `guinevere_core` -> INTERNAL, `guinevere_subagent` -> PUBLIC, `default` -> PUBLIC.
- Whether `build_safe_content()` correctly handles unknown classification (fail-closed to placeholder).
- Whether `_is_safe_mode_blocked_content()` (detects emotional, surveillance, persona-escalation) has false-positive risk from substring matching.
- Whether the `ConsentLedger` cross-reference (Layer 1 of DNR defense) is genuinely deferred -- verify no stub or partial implementation exists.
- Whether embedding privacy boundaries (`prepare_embedding_text()` single choke-point, 7 regex redaction patterns) correctly strip PII before API submission.
- Whether metadata-only logging is consistently applied across ALL modules (embeddings, write_pipeline, dnr, consolidation).

**Key source files to inspect:**
- `src/memory/dnr.py`
- `src/memory/read_pipeline.py` (safe-mode constants, build_safe_content, _SAFE_MODE_CEILING)
- `src/memory/embeddings.py` (prepare_embedding_text, redaction patterns)
- `src/memory/write_pipeline.py` (classification default, Critical fail-closed)
- `src/core/services/prompt_loader.py` (safe_mode resolution, DNR exclusion)
- Prior audit: `audit-reports/P3/P3-FINAL-AUDIT/D04-security-secrets.md`
- Prior audit: `audit-reports/P3/P3-FINAL-AUDIT/D05-safety-compliance.md`

**Expected output:** Security boundary verification, privacy guard assessment, deferred items list.

---

### DIM-06: Context Injection and Privacy

**What to check:**
- Whether `assemble_system_prompt_with_memory()` (prompt_loader.py:208-294) correctly orchestrates: recall -> safe-content format -> inject.
- Whether `get_system_prompt_with_context()` (prompt_loader.py:41-101) correctly formats recalled memories with safe_content only -- never raw_content.
- Whether the `exclude_dnr=True` hardcoded parameter is appropriate (no caller override).
- Whether safe_mode is resolved from `HardStopHandler.is_safe` (authoritative source) or passed param (prompt_loader.py:252-254).
- Whether `ReadPipelineSafetyError` is correctly caught and returns the base prompt + mood (discardable).
- Whether KG context append (prompt_loader.py:273-275, 287-293) is gated by safe_mode.
- Whether the default `top_k=3` and `token_budget=4000` are appropriate for context injection.
- Whether the P20 HARD STOP safe_mode propagation gap (`graph.py:observe_node` not passing `safe_mode=True`) is confirmed as an open issue.
- Whether any prompt injection path could expose `raw_content` instead of `safe_content`.

**Key source files to inspect:**
- `src/core/services/prompt_loader.py`
- `src/life_kernel/graph.py` (observe_node, idle_node)
- `src/life_kernel/p18_adapter.py` (memory recall adapter)
- `src/life_kernel/cognition.py` (memory loop placeholder)
- `src/hermes/_memory_bridge.py`
- Prior audit: `audit-reports/P3/P3-FINAL-AUDIT/D04-security-secrets.md`

**Expected output:** Privacy boundary verification, context injection gap analysis, safe_mode propagation status.

---

### DIM-07: Performance Benchmark Validity

**What to check:**
- Whether the P3-007 HNSW benchmark used real data that was rolled back (20 seed rows per table -- documented as too small).
- Whether the benchmark claims are honest about "Seq Scan + Sort for 0-row tables" (P3-007).
- Whether `scripts/bench_memory.py` (P3-019, 760 lines) has dry-run and live-DB modes, and ADR-009 targets are documented (vector p95 < 2s, FTS < 500ms, hybrid < 3s).
- Whether `ef_search=100` was retained as default based on evidence or by default.
- Whether the `MAX_CANDIDATE_POOL=200` and `EXPANDED_LIMIT_MULTIPLIER=3` constants in `read_pipeline.py` are reasonable or arbitrary.
- Whether the token budget estimation (`CHARS_PER_TOKEN=4` at `read_pipeline.py:103`) is a documented approximation without tiktoken.
- Whether any performance regression tests exist (none found in research -- verify).
- Whether HNSW index parameters (m=16, ef_construction=128) are documented as defaults pending real data tuning.

**Key source files to inspect:**
- `docs/setup-evidence/P3/STEP-P3-007/benchmark-report.md`
- `docs/setup-evidence/P3/STEP-P3-007/hnsw-benchmark-raw.txt`
- `scripts/bench_memory.py`
- `src/memory/read_pipeline.py` (constants: RRF_K, RECENCY_HALF_LIFE_DAYS, VECTOR_WEIGHT, MAX_CANDIDATE_POOL, etc.)
- `src/memory/models.py` (HNSW index params)
- Prior audit: `audit-reports/P3/P3-FINAL-AUDIT/D10-performance-operational.md`

**Expected output:** Benchmark honesty assessment, constant reasonableness review, performance regression test status.

---

### DIM-08: Downstream P19/P20/P21/P22/P23/P24 Compatibility

**What to check:**
- Whether `p18_adapter.MemoryRecallAdapter` passes `project_id` to `recall_memories` (p18_adapter.py:86-97) -- verify wires exist or are absent.
- Whether P19 project_id filtering works for ALL memory tables (Episodes YES, SemanticFacts NO, KnowledgeGraph NO -- confirm as the CRITICAL gap).
- Whether P20 HARD STOP `safe_mode` propagation gap is confirmed (observe_node does not pass `safe_mode=True` to adapters).
- Whether P21 voice transcripts can use `store_episode` with `episode_type='voice_turn'` -- verify column support.
- Whether P22's planned direct `store_episode` calls bypass `HermesMemoryBridge` injection gates -- document architectural risk.
- Whether P23 action context via `DecisionContextBuilder` uses `p18_adapter` (which uses P3 `recall_memories`) -- verify dependency chain.
- Whether P24 fork would need to preserve ALL 5 RRF signals plus DNR/classification/safe-mode/token-budget/project_id filtering.
- Whether P16 KG ingestion hook (in `consolidation.py`) and 4th RRF signal (in `read_pipeline.py`) are correctly wired.

**Key source files to inspect:**
- `src/life_kernel/p18_adapter.py`
- `src/life_kernel/p16_adapter.py` (if exists)
- `src/life_kernel/graph.py` (observe_node, idle_node)
- `src/life_kernel/cognition.py`
- `src/memory/models.py` (project_id on SemanticFacts, KnowledgeGraph)
- `src/memory/read_pipeline.py` (project_id filter in query builders)
- `src/memory/write_pipeline.py` (project_id parameter)
- `src/memory/consolidation.py` (KG ingestion hook)
- `src/hermes/_memory_bridge.py`
- `src/hermes_plugins/commands_memory/memory_search.py`
- P19 research: `docs/setup-evidence/P19/research/p19-memory-namespace-research.md`
- P20 research: `docs/setup-evidence/P20/`
- P21 research: `docs/setup-evidence/P21/`
- P24 research: `docs/setup-evidence/P24/`
- `audit-reports/P3/P3-FINAL-AUDIT/D12-p4p5-readiness.md`

**Expected output:** Compatibility matrix per downstream phase, gap severity, documented risks.

---

## 2. Wave 2: Six Adversarial Re-Audits

Wave 2 selects the highest-risk dimensions from wave-1 findings and re-verifies them with an adversarial mindset -- assume the documentation is wrong and attempt to disprove it.

### ADV-01: DNR and Safe-Mode Adversarial Re-Audit (DIM-05 re-verify)

**Why adversarial:** DNR and safe-mode are the primary privacy/safety boundaries. If either has a bypass path, the entire safety model is compromised.

**Adversarial approach:**
- Attempt to bypass DNR by tracing every code path that reads episodes: `recall_memories`, `consolidate_episodes_to_facts`, `decay_sweep_job`, `_fact_exists_by_key`, KG ingestion hook -- verify ALL paths filter `do_not_recall`.
- Attempt to bypass safe-mode: trace `build_safe_content()` for every classification level and every caller. Verify no path returns `raw_content` when `safe_mode=True`.
- Check classification ceiling enforcement: verify ALL callers of `recall_memories` that pass `principal` values not in the ceiling map get the default (fail-closed).
- Check DNR authorization: verify no principal other than `guinevere_core` can call `mark_memory_dnr` or `unmark_memory_dnr`.
- Check `ConsentLedger` cross-reference: verify it does NOT exist as stub/placeholder that could give false confidence.
- Check `verify_recall_results_dnr_free()` is actually called before context injection in all paths (Hermes bridge, prompt_loader, Discord commands).

**Expected output:** Confirmation or refutation of privacy boundary integrity.

---

### ADV-02: Context Injection and Raw Content Exposure (DIM-06 re-verify)

**Why adversarial:** The most sensitive privacy risk is raw content leaking into a system prompt.

**Adversarial approach:**
- Search for ANY code path that passes `raw_content` (not `safe_content`) from an episode into a prompt or output.
- Check all `recall_memories` callers and verify they use `safe_content` field from results.
- Check `prompt_loader.py` format functions -- verify only `safe_content` is injected.
- Check Discord command `/memory-search` output -- verify `safe_content` is used, not `raw_content`.
- Check the `recall_memories` return structure -- verify `raw_content` is present in the return dict but no caller accesses it unsafely.
- Check `build_safe_content()` for any classification level that returns `raw_content` (only PUBLIC/INTERNAL when not blocked -- verify this is correct by design).

**Expected output:** Confirmed safe-content enforcement or leaked raw_content paths.

---

### ADV-03: Read/Write Pipeline Edge Cases (DIM-04 re-verify)

**Why adversarial:** The pipelines have never been tested against a real database. Edge cases that would surface in production may be invisible in unit tests.

**Adversarial approach:**
- Check `store_episode` for missing required parameters: what happens if `embedding_service` is None? If `session` is None? If `content` is empty string?
- Check `recall_memories` for empty result handling: what happens when query returns 0 episodes? When all results are DNR-filtered? When all results exceed token budget?
- Check classification resolution for unknown labels: verify `classification_level()` returns level 5 (fail-closed beyond Critical).
- Check RRF fusion with single signal: what happens if one query builder returns 0 results? Does the RRF formula divide by zero?
- Check `apply_token_budget` with empty list: verify it handles edge case.
- Check `verify_recall_results_dnr_free` with empty results list: verify it does not raise.
- Check `build_safe_content` with missing `raw_content` key: verify it does not KeyError.
- Check `store_episode` Critical fail-closed: verify it raises `WritePipelineCriticalError` and that callers catch it (Discord command, Hermes bridge).

**Expected output:** Edge case coverage assessment, robustness gaps.

---

### ADV-04: ORM Drift and Migration Chain Adversarial Re-Audit (DIM-03 re-verify)

**Why adversarial:** ORM drift is the most common source of silent data corruption in SQLAlchemy applications.

**Adversarial approach:**
- For every table created by migrations, verify the ORM class has matching columns. Use `grep` to cross-check column names from migration `add_column`/`create_table` calls against ORM attribute names.
- For every ORM class (48 total), verify the migration DDL creates all columns the ORM expects (including mixin columns).
- Specifically verify `SessionSummary` ClassificationMetaMixin columns are present in migration DDL or document as `metadata.create_all()` only.
- Verify `p5_024` migration DDL for `session_summaries` includes all 11 mixin columns, not just 7.
- Verify `p5_012` duplicate column adds (`status`, `retry_count`) are truly no-ops with `IF NOT EXISTS`.
- Verify `surveillance.events` hypertable interval by reading the actual `op.create_hypertable()` call that would execute FIRST (inline, 1d) vs the manual patch (7d).
- Verify `models.py` docstring table count against actual `__tablename__` entries.
- Verify `alembic/env.py` `GUINEVERE_SCHEMAS` inclusion of `gamification`.

**Expected output:** Comprehensive ORM drift list, DDL correctness confirmation.

---

### ADV-05: Performance and Benchmark Claim Re-Audit (DIM-07 re-verify)

**Why adversarial:** P3-007 benchmark claims "passed" despite zero meaningful data. The benchmark may give false confidence.

**Adversarial approach:**
- Read the raw benchmark output files and identify ANY statistically meaningful result. Verify the caveat "Seq Scan for 0-row tables" is prominently documented.
- Check `ef_search=100` default rationale: is it documented as "retained pending real data" or as a verified result?
- Check `scripts/bench_memory.py` for dry-run mode: verify it produces plausible output without a live DB.
- Check `MAX_CANDIDATE_POOL=200` and `VECTOR_WEIGHT=0.5`/`FTS_WEIGHT=0.5` in `read_pipeline.py` -- are any of these supported by evidence or are they plan defaults?
- Check `CHARS_PER_TOKEN=4` (read_pipeline.py:103) -- verify it is documented as approximation (no tiktoken).
- Check if any HNSW parameter tuning was done beyond 20-row benchmark (should find none).
- Check if any E2E benchmark test exists in CI (should find none).

**Expected output:** Honest assessment of benchmark validity -- whether claims are materially misleading or honestly caveated.

---

### ADV-06: Consolidation Scheduler Adversarial Cross-Cut (cross-dimension)

**Why adversarial:** The consolidation scheduler is the most severe finding (CRITICAL -- dead in production). This re-audit verifies NO alternative wiring exists.

**Adversarial approach:**
- Grep ENTIRE `src/` tree for `register_consolidation_job`, `register_decay_job`, `AsyncIOScheduler`, `CronTrigger`, `apscheduler` -- verify NO active call site exists outside comments.
- Grep ENTIRE repo for `consolidate_episodes_to_facts` call sites outside tests and `consolidation.py` itself. Verify consolidation logic is never triggered by any cron, systemd timer, or alternative entry point.
- Check `src/core/main.py` thoroughly (not just lines 22-38) -- verify no alternative scheduler wiring exists elsewhere in the file.
- Check all `main.py` files in subdirectories (`src/gmail/main.py`, `src/x_poster/main.py`, etc.) for scheduler imports.
- Check if `systemd` timer files exist in the repo (`*.timer`, `*.service` files in `deploy/` or `infra/` directories that might call consolidation outside main.py).
- Verify the KG ingestion scheduler (P16) IS correctly wired (as documented) to confirm the pattern works.
- Check `tests/memory/test_consolidation.py` for the scheduler registration test -- verify it tests registration against a fake scheduler, not actual cron execution.
- Document that this finding requires VPS runtime verification to confirm (Windows environment limitation).

**Expected output:** Definitive confirmation (or refutation) that consolidation/decay schedulers are dead code.

---

## 3. Four Evidence Registers

Every finding discovered during wave 1 and wave 2 must be recorded in one of four registers. Registers are append-only markdown tables.

### REG-01: Bug Register (All Severities)

**Schema:**

```markdown
| ID | Dimension | File:Line | Finding | Severity | Status | Prior NR# |
|----|-----------|-----------|---------|----------|--------|-----------|
| BUG-01 | DIM-03 | src/core/main.py:23-35 | Consolidation scheduler commented out | CRITICAL | CONFIRMED | NR-4 |
```

**Fields:**
- `ID`: `BUG-NNN` auto-incrementing
- `Dimension`: Which wave-1 dimension or wave-2 adversarial re-audit discovered this
- `File:Line`: Exact source file and line (absolute path preferred)
- `Finding`: One-sentence description
- `Severity`: CRITICAL | HIGH | MEDIUM | LOW | COSMETIC
- `Status`: CONFIRMED | NEEDS_VERIFICATION | DISPUTED | FIXED
- `Prior NR#`: Reference to prior audit NR item if applicable

**Severity definitions:**
- **CRITICAL:** Production data loss, privacy leak, security bypass, safety-system failure, or core functionality dead in production.
- **HIGH:** Significant functionality gap, incorrect behavior under normal conditions, ORM drift that could cause silent data corruption, missing test coverage for critical path.
- **MEDIUM:** Deferred functionality with documented acceptance, minor ORM drift with no immediate impact, dependency hygiene issues, moderate test coverage gaps.
- **LOW:** Docstring staleness, minor evidence file issues (encoding), unchecked checklist items, orphaned code scaffolds.
- **COSMETIC:** Comment typos, formatting issues, header mismatch in migration file, empty placeholder directories.

### REG-02: Missing Docs Register

**Schema:**

```markdown
| ID | Expected Doc | Actual State | Gap Description | Severity | Prior NR# |
|----|-------------|--------------|-----------------|----------|-----------|
| DOC-01 | STEP-P3-016-019/verification.md | MISSING -- only auditor-gate.md exists | Combined 4-step batch lacks standard evidence artifact | HIGH | NR-2 |
```

**Fields:**
- `ID`: `DOC-NNN`
- `Expected Doc`: Path or description of document that should exist
- `Actual State`: What exists instead (or nothing)
- `Gap Description`: What information is missing
- `Severity`: CRITICAL | HIGH | MEDIUM | LOW | COSMETIC
- `Prior NR#`: Reference to prior audit NR item if applicable

### REG-03: Implementation Gap Register

**Schema:**

```markdown
| ID | Claimed Feature | Implementation State | Gap Description | Severity |
|----|----------------|---------------------|-----------------|----------|
| GAP-01 | Daily consolidation at 03:00 ICT | Code exists, NOT WIRED at runtime | register_consolidation_job() is commented-out in main.py | CRITICAL |
```

**Fields:**
- `ID`: `GAP-NNN`
- `Claimed Feature`: What P3 or evidence claims exists
- `Implementation State`: What actually exists
- `Gap Description`: The delta between claim and reality
- `Severity`: CRITICAL | HIGH | MEDIUM | LOW | COSMETIC

### REG-04: Superseded/Transition Register

**Schema:**

```markdown
| ID | Original P3 Claim | Superseded By | Current Status | Recommendation |
|----|------------------|---------------|----------------|----------------|
| SUP-01 | 47-table docstring | Post-P3 additions (KnowledgeGraph P16, gamification P6, life_kernel P20) | Stale -- 48 ORM classes + 7 tables without ORM models | Update docstring; consider adding ORM models for gamification/life_kernel |
```

**Fields:**
- `ID`: `SUP-NNN`
- `Original P3 Claim`: What P3 documentation or code claimed
- `Superseded By`: Which later phase, migration, or code change made the claim stale
- `Current Status`: What the correct state is now
- `Recommendation`: What mama should consider (NO FIXES from audit)

---

## 4. Read-Only Guardrails and Reconciliation Points

### Guardrails (enforced throughout audit)

1. **No runtime code edits.** The `src/`, `alembic/`, `tests/` directories are read-only. No file in any of these directories may be created, modified, or deleted.

2. **No docs edits except audit output.** The only files that may be created/modified are under `docs/setup-evidence/legacy-audit/P3/`. `CHECKLIST.md`, `PROGRESS.md`, `README.md`, `AGENTS.md` may NOT be modified.

3. **No DB mutations.** No `alembic upgrade/downgrade`, no `INSERT/UPDATE/DELETE`, no `CREATE/DROP` operations. Read-only introspection only: `SELECT`, `\dt`, `\di`, `\d+`, `\dx`, EXPLAIN.

4. **No secrets printing.** No DB passwords, API keys, decrypted env vars, raw memory content, or personal data in output.

5. **No deployment/restart/migration.** No `systemctl start/stop/restart`, no `docker compose up/down`, no schema changes.

6. **Everything in writing.** All findings, evidence, and verdicts go into markdown files under the audit output path. Inline-only findings = FAIL.

7. **VPS verification deferred where impossible.** Any finding that requires VPS access, systemd, or live PostgreSQL must be tagged `NEEDS RUNTIME VERIFICATION` and documented as a deployment gap.

### Seven Known Reconciliation Points

These are the pre-identified tension points between P3 claims and reality that every audit dimension must explicitly address:

1. **Consolidation scheduler wiring status.** P3-015 claims daily consolidation. Reality: code exists but is not auto-wired. Every dimension that touches P3-015 or runtime readiness must confirm or refute this finding.

2. **P3-005 embedding pipeline never tested against real API.** Every dimension that evaluates the embedding pipeline (DIM-01, DIM-04, DIM-07) must assess the risk of zero live API testing.

3. **P3-009/P3-010 pipelines never tested against real DB.** Every dimension evaluating read/write pipelines must document the FakeSession gap.

4. **P3-016-019 missing verification.md.** Any dimension evaluating evidence completeness must flag this gap.

5. **CHECKLIST.md sections 5.1-5.6 unchecked.** Any dimension evaluating completeness must document the 20+ unchecked items.

6. **P19 project_id on SemanticFacts/KG missing (ORM).** DIM-08 and ADV-04 must confirm this CRITICAL finding.

7. **P20 HARD STOP safe_mode not propagated to memory recall.** DIM-06 and ADV-02 must confirm this HIGH finding.

---

## 5. Final Report Structure

After all wave-1 and wave-2 audits complete, a synthesis agent produces the final report at:
`docs/setup-evidence/legacy-audit/P3/P3-IMPLEMENTATION-AUDIT-FINAL.md`

### Report Outline

```markdown
# P3 (Memory Foundation) Implementation Audit -- FINAL REPORT

## Metadata
- Audit date, agent, read-only affirmation
- Repo state (commit, branch, date)
- Scope (which dimensions executed, which registers populated)

## Executive Summary
- 3-5 sentence overview
- Overall status verdict
- Count of findings by severity (CRITICAL, HIGH, MEDIUM, LOW, COSMETIC)
- Count of items per register (BUGS, DOCS, GAPS, SUPERSEDED)

## Wave 1 Results (8 Dimensions)
### DIM-01: Architecture-Implementation Consistency
- Key findings, evidence, verdict
### DIM-02: Evidence-Documentation Consistency
- Key findings, evidence, verdict
### DIM-03: DB Schema and Migration Chain Integrity
- Key findings, evidence, verdict
### DIM-04: Read/Write Pipeline Correctness
- Key findings, evidence, verdict
### DIM-05: DNR, Safe-Mode, and Security Boundaries
- Key findings, evidence, verdict
### DIM-06: Context Injection and Privacy
- Key findings, evidence, verdict
### DIM-07: Performance Benchmark Validity
- Key findings, evidence, verdict
### DIM-08: Downstream P19/P20/P21/P22/P23/P24 Compatibility
- Key findings, evidence, verdict

## Wave 2 Results (6 Adversarial Re-Audits)
### ADV-01: DNR and Safe-Mode Adversarial Re-Audit
- Attack vectors tested, results, verdict
### ADV-02: Context Injection and Raw Content Exposure
- Attack vectors tested, results, verdict
### ADV-03: Read/Write Pipeline Edge Cases
- Attack vectors tested, results, verdict
### ADV-04: ORM Drift and Migration Chain Adversarial Re-Audit
- Attack vectors tested, results, verdict
### ADV-05: Performance and Benchmark Claim Re-Audit
- Attack vectors tested, results, verdict
### ADV-06: Consolidation Scheduler Adversarial Cross-Cut
- Attack vectors tested, results, verdict

## Evidence Registers (4 tables)
### REG-01: Bug Register (All Severities)
### REG-02: Missing Docs Register
### REG-03: Implementation Gap Register
### REG-04: Superseded/Transition Register

## Overall Verdict
One of the 8 allowed statuses:
| Status | Meaning |
|--------|---------|
| VERIFIED IMPLEMENTED | All claims substantiated, no material gaps |
| IMPLEMENTED WITH BUGS | Code works but has defects needing correction |
| IMPLEMENTED WITH DOC GAPS | Code works but evidence/documentation incomplete |
| PARTIALLY IMPLEMENTED | Significant features exist but have material gaps |
| PARTIALLY SUPERSEDED BY P18/P20 | Later phases made parts obsolete |
| SUPERSEDED BY LATER PHASE | Entire P3 replaced by later work |
| DOCS CLAIM ONLY / NOT PROVEN | Claims unverifiable from available evidence |
| NEEDS RUNTIME VERIFICATION | Assessment requires live VPS access |

## Recommendations for Mama (NO FIXES)
- Ordered by severity, with rationale
- Each recommendation references register IDs (BUG-NNN, GAP-NNN, etc.)
- Deployment-only items clearly marked
- Items requiring mama decision vs items needing ticket/plan
```

---

## 6. Execution Order

### Phase 1: Wave 1 (8 parallel audit dimensions)
Execute DIM-01 through DIM-08 in parallel (no cross-dependency). Each produces a standalone markdown file.

### Phase 2: Register Population
After all 8 dimensions complete, populate REG-01 through REG-04 from their findings.

### Phase 3: Wave 2 (6 adversarial re-audits)
Execute ADV-01 through ADV-06 in parallel. Each reads the wave-1 findings for its dimension(s) and attempts to disprove or deepen them.

### Phase 4: Register Update
Update REG-01 through REG-04 with any new findings from wave 2.

### Phase 5: Final Synthesis
Produce the final report at `P3-IMPLEMENTATION-AUDIT-FINAL.md` by aggregating all dimension outputs and registers.

---

## Appendix: Output File Paths

### Wave 1 (8 files)
- `docs/setup-evidence/legacy-audit/P3/audits/round-1/DIM-01-architecture-implementation.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-1/DIM-02-evidence-docs-consistency.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-1/DIM-03-db-schema-migration.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-1/DIM-04-read-write-pipeline.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-1/DIM-05-dnr-safe-mode-security.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-1/DIM-06-context-injection-privacy.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-1/DIM-07-performance-benchmark.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-1/DIM-08-downstream-compatibility.md`

### Wave 2 (6 files)
- `docs/setup-evidence/legacy-audit/P3/audits/round-2/ADV-01-dnr-safe-mode.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-2/ADV-02-context-injection-privacy.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-2/ADV-03-read-write-pipeline-edge.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-2/ADV-04-orm-drift-migration.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-2/ADV-05-performance-benchmark.md`
- `docs/setup-evidence/legacy-audit/P3/audits/round-2/ADV-06-consolidation-scheduler.md`

### Registers (4 files)
- `docs/setup-evidence/legacy-audit/P3/evidence/REG-01-bug-register.md`
- `docs/setup-evidence/legacy-audit/P3/evidence/REG-02-missing-docs-register.md`
- `docs/setup-evidence/legacy-audit/P3/evidence/REG-03-implementation-gap-register.md`
- `docs/setup-evidence/legacy-audit/P3/evidence/REG-04-superseded-transition-register.md`

### Final Report (1 file)
- `docs/setup-evidence/legacy-audit/P3/P3-IMPLEMENTATION-AUDIT-FINAL.md`
