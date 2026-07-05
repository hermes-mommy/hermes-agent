# P3 Post-P19 Memory Fix — Executable Implementation Plan

**Date:** 2026-06-27
**Phase:** 2 — Planner Gate
**Lane:** B
**Author:** Guinevere (orchestrator)
**Status:** READY FOR IMPLEMENTATION
**Evidence Root:** `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/`

---

## Executive Summary

P19 deployed to production. `semantic_facts.project_id` is now NOT NULL. `consolidate_episodes_to_facts()` has zero project awareness — enabling the consolidation scheduler WILL crash. Life-kernel recall path has no embedding service. KG ORM is raw-SQL-only. Episodes with NULL embeddings have no backfill.

**6 bugs, 2 CRITICAL, 2 HIGH, 2 MEDIUM.**

---

## Master Todo

| # | Step | Severity | Deps | Parallel |
|---|------|----------|------|----------|
| B1 | Fix SemanticFacts ORM model — add project_id/project_scope columns | CRITICAL | None | parallel |
| B2 | Fix consolidate_episodes_to_facts — project-aware | CRITICAL | B1 | sequential |
| B3 | Fix store_episode_batch — forward project_id | HIGH | B1 | parallel |
| B4 | Wire EmbeddingService into life-kernel recall path | HIGH | None | parallel |
| B5 | Create embedding backfill job | MEDIUM | B4 | sequential |
| B6 | KG ORM — add adapter/compatibility layer | MEDIUM | None | parallel |
| B7 | Activate consolidation scheduler (post-fix) | LOW | B2 | sequential |
| B8 | Run all tests, verify P20 regression | GATE | B1-B7 | sequential |

---

## Dependency Map

```
B1 (models.py fix)
├── B2 (consolidation fix) ── B7 (activate scheduler)
│   └── B8 (tests + P20 regression)
├── B3 (write_pipeline batch fix)
B4 (embedding service wiring)
├── B5 (embedding backfill)
B6 (KG ORM adapter)
```

---

## Collision Scan

| Step | Files Touched | Collision Risk |
|------|--------------|----------------|
| B1 | `src/memory/models.py` | HIGH — also touched by B2, B3, B6 |
| B2 | `src/memory/consolidation.py` | MEDIUM |
| B3 | `src/memory/write_pipeline.py` | LOW |
| B4 | `src/core/main.py` | HIGH — P20 hot path |
| B5 | NEW: `src/memory/embedding_backfill.py` | NONE |
| B6 | `src/memory/models.py` | HIGH — shares with B1 |
| B7 | `src/core/main.py` | HIGH — shares with B4 |

**Mitigation:** B1 executes first (models.py), then B2+B3+B6 can run in parallel. B4 and B7 are sequential on main.py. Parent handles main.py edits.

---

## Per-Step Verification Scaffolds

### B1: Fix SemanticFacts ORM Model

**Expected Files:**
- `src/memory/models.py` — modified (SemanticFacts class)

**Forbidden Patterns:**
- `# type: ignore`
- `as any`
- `except Exception` (bare)
- Duplicate `project_id` declaration (Episodes already has 2 — do NOT add another)

**Required Commands:**
- `python -m pytest tests/memory/test_models.py -v` → exit 0
- `python -c "from src.memory.models import SemanticFacts; assert hasattr(SemanticFacts, 'project_id')"` → exit 0

**Hard Rejection:**
- SemanticFacts still has no project_id attribute
- Existing tests break

**Evidence:**
- `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/implementation/B1-orm-model-fix.md`

---

### B2: Fix consolidate_episodes_to_facts — Project-Aware

**Expected Files:**
- `src/memory/consolidation.py` — modified

**Forbidden Patterns:**
- `# type: ignore`
- `except Exception` swallowing
- Hardcoded project UUID (must use `ProjectRegistry.DEFAULT_PROJECT_ID`)

**Required Commands:**
- `python -m pytest tests/memory/test_consolidation.py -v` → exit 0
- `python -c "from src.memory.consolidation import consolidate_episodes_to_facts; import inspect; sig = inspect.signature(consolidate_episodes_to_facts); print(sig)"` → shows project_id parameter

**Hard Rejection:**
- SemanticFacts created without project_id
- Consolidation tests fail
- ProjectRegistry not imported

**Evidence:**
- `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/implementation/B2-consolidation-project-aware.md`

---

### B3: Fix store_episode_batch

**Expected Files:**
- `src/memory/write_pipeline.py` — modified

**Forbidden Patterns:**
- Silent drop of project_id

**Required Commands:**
- `python -m pytest tests/memory/test_write_pipeline.py -v` → exit 0

**Hard Rejection:**
- store_episode_batch still doesn't pass project_id
- Existing tests break

**Evidence:**
- `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/implementation/B3-write-pipeline-batch-fix.md`

---

### B4: Wire EmbeddingService into Life-Kernel

**Expected Files:**
- `src/core/main.py` — modified

**Forbidden Patterns:**
- Hardcoded API key
- Blocking sync call in async path
- `except Exception` swallowing

**Required Commands:**
- `python -c "from src.core.main import app; print('OK')"` → exit 0 (no crash on import)
- `grep -c 'EmbeddingService' src/core/main.py` → ≥ 1

**Hard Rejection:**
- Life-kernel startup crashes
- embedding_service still not passed to recall_memories
- P20 regression (NRestarts > 0 after deploy)

**Evidence:**
- `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/implementation/B4-embedding-service-wiring.md`

---

### B5: Create Embedding Backfill Job

**Expected Files:**
- `src/memory/embedding_backfill.py` — NEW

**Forbidden Patterns:**
- Hard delete of episodes
- Unbounded batch sizes
- No idempotency check

**Required Commands:**
- `python -c "from src.memory.embedding_backfill import backfill_null_embeddings; print('OK')"` → exit 0
- `python -m pytest tests/memory/test_embedding_backfill.py -v` → exit 0

**Hard Rejection:**
- Backfill modifies episodes with existing embeddings
- No idempotency guard
- No batch size limit

**Evidence:**
- `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/implementation/B5-embedding-backfill.md`

---

### B6: KG ORM Adapter

**Expected Files:**
- `src/memory/models.py` — modified (OR new KG models file)
- `src/knowledge_graph/adapter.py` — NEW (optional)

**Forbidden Patterns:**
- Breaking existing raw SQL queries
- Removing the legacy KnowledgeGraph class without migration

**Required Commands:**
- `python -m pytest tests/knowledge_graph/ -v` → exit 0

**Hard Rejection:**
- KG queries fail
- Existing tests break

**Evidence:**
- `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/implementation/B6-kg-orm-adapter.md`

---

### B7: Activate Consolidation Scheduler

**Expected Files:**
- `src/core/main.py` — modified (uncomment scheduler registration)

**Forbidden Patterns:**
- Activating without B2 fix verified
- No error handling for scheduler failures

**Required Commands:**
- `python -c "from src.core.main import app; print('scheduler check OK')"` → exit 0

**Hard Rejection:**
- Consolidation scheduler crashes on startup
- B2 not verified before activation

**Evidence:**
- `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/implementation/B7-scheduler-activation.md`

---

### B8: Test Suite + P20 Regression

**Expected Files:**
- All test files pass

**Required Commands:**
- `python -m pytest tests/memory/ -v` → exit 0
- `python -m pytest tests/knowledge_graph/ -v` → exit 0
- `python -m pytest tests/life_kernel/ -v` → exit 0

**Hard Rejection:**
- Any test failure
- P20 NRestarts > 0
- Secret leak in any file

**Evidence:**
- `docs/setup-evidence/legacy-audit/P3/evidence/post-p19-fix/verification/p3-post-p19-memory-fix-verification.md`

---

## Rollback Plan

Per step:
1. `git diff HEAD` → review changes
2. `git stash` → revert all
3. Restart guinevere-core

For B7 (scheduler activation):
1. Comment out scheduler registration in main.py
2. Restart guinevere-core

## Deploy Policy

- **NO auto-deploy.** All changes are code-only until operator approval.
- **B4 (main.py change)** requires: backup main.py → canary restart → smoke test → verify P20 alive → full deploy
- **B7 (scheduler activation)** requires: B2 verified → B4 smoke test passed → operator approval → activate

## Auditor Matrix

| Step | Auditor Dimensions |
|------|-------------------|
| B1 | DB schema, code quality, type safety |
| B2 | Memory recall, project isolation, consolidation |
| B3 | Write pipeline, batch correctness |
| B4 | Life-kernel, embedding, recall quality |
| B5 | DB safety, idempotency, performance |
| B6 | KG schema, query compatibility |
| B7 | Scheduler, ops safety |
| B8 | Full regression, P20 boundary, secrets |