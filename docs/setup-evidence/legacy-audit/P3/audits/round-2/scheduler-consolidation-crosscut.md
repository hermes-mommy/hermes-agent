# P3 Scheduler/Consolidation Cross-cut Audit (Round 2)

**Date:** 2026-06-25
**Agent:** Wave-2 Adversarial Audit (read-only)
**Scope:** Is the daily consolidation actually running? Integration-liveness cross-cut
**Read-only affirmation:** YES. No services restarted. No migrations run. No DB accessed.

---

## EXECUTIVE SUMMARY

**The daily consolidation scheduler is NOT running. It was never wired into the application lifespan.** This is a [CRITICAL] finding. P3 is code-complete but not running. `semantic_facts` remains empty in production. The P3-015 evidence document itself explicitly acknowledges this ("No live services started") yet its auditor gate gives PASS, creating a misleading impression of operational completeness.

---

## (a) register_consolidation_job: Commented Out, Zero Call Sites

**File:** `C:/Users/faizz/guinevere/src/core/main.py`, lines 22-38

The entire consolidation scheduler registration is commented out as a documentation block:

```python
# ---------------------------------------------------------------------------
# P3-015 consolidation scheduler registration (optional — no DB by default)
# ---------------------------------------------------------------------------
# To activate the daily consolidation scheduler at runtime, inject an async
# SQLAlchemy session factory (async_sessionmaker) into the lifespan:
#
#   from apscheduler.schedulers.asyncio import AsyncIOScheduler
#   from src.memory.consolidation import register_consolidation_job
#
#   scheduler = AsyncIOScheduler()
#   await register_consolidation_job(scheduler, session_factory=AsyncSessionLocal)
#   scheduler.start()
```

These are **comment lines** (prefixed with `#`), not executable code. The import of `register_consolidation_job` appears only in commented text at `main.py:29` and `main.py:32`.

**Grep across all `src/` confirms zero live call sites:**
- `register_consolidation_job` appears in:
  - `src/memory/__init__.py` — re-export only (lines 58, 250)
  - `src/memory/consolidation.py` — function definition (line 851)
  - `src/knowledge_graph/ingestion/cron.py` — docstring reference only (line 12)
  - `src/knowledge_graph/ingestion/__init__.py` — docstring reference only (line 20)
  - `tests/memory/test_consolidation.py` — test usage only (lines 53, 491, 499, 515, 538-539)
  - `src/core/main.py` — **commented out** (lines 29, 32)

**No other call site activates the consolidation scheduler.** [CRITICAL]

The lifespan function at `main.py:60-462` does wire up:
- Report scheduler (line 116-120): `register_monthly_report_scheduler()` — RUNNING
- KG ingestion scheduler (lines 167-201): `register_kg_ingestion_job()` — RUNNING
- Surveillance consumer (lines 123-165) — RUNNING
- Heartbeat service (lines 401-411) — RUNNING

But **NOT** the memory consolidation scheduler or the decay sweep scheduler.

---

## (b) Cascade Gap: What Happens When Consolidation Never Runs

**Severity: [CRITICAL]**

If consolidation never runs:

1. **`semantic_facts` table stays empty.** Episodes are written by the memory write pipeline (`src/memory/write_pipeline.py`) into the `episodes` table, but no code path ever converts them to semantic facts.

2. **P3 recall quality degrades to single-tier.** The `recall_memories` function in `src/memory/read_pipeline.py` queries both episodes and semantic facts via hybrid search. With `semantic_facts` empty, the semantic tier returns nothing. The recall becomes episodes-only.

3. **KG ingestion runs but has nothing to process.** The KG ingestion cron IS wired (`main.py:167-201`) and runs at 03:30 ICT daily. However, it reads `semantic_facts` created by consolidation (`src/knowledge_graph/ingestion/cron.py:2-8`). With no semantic facts, the `BatchProcessor.process_unprocessed_facts()` finds zero candidates every run. The KG cron is running but is effectively a no-op.

4. **Post-consolidation KG hook never triggers.** The inline KG ingestion hook inside `consolidate_episodes_to_facts()` at `consolidation.py:456-489` is never reached because the function is never called.

5. **FSRS post-consolidation review never triggers.** The inline FSRS review at `consolidation.py:410-453` is similarly dead code in production.

**Net effect: P3 is effectively a single-tier memory (episodes only) with no semantic layer.**

---

## (c) Daily Consolidation Job Idempotency Analysis

**File:** `C:/Users/faizz/guinevere/src/memory/consolidation.py`, lines 275-497

The `consolidate_episodes_to_facts()` function accepts an optional `watermark: datetime | None = None` parameter (line 278). When provided, it filters to only episodes created after the watermark (`line 325: stmt = stmt.where(Episodes.created_at > watermark)`).

**However, `daily_consolidation_job()` at line 823 calls `consolidate_episodes_to_facts(session)` WITHOUT passing a watermark.** This means:
- On each run, it processes ALL non-DNR episodes ever created.
- It relies entirely on the content-key deduplication (`make_content_key()` SHA-256 at line 633-645 and `_fact_exists_by_key()` at line 648-668) to prevent double-consolidation.

**Is this idempotent?** Mostly yes, but with a performance concern:
- The `_fact_exists_by_key()` function at line 656-658 does `SELECT * FROM semantic_facts` (full table scan) for every candidate fact, then iterates all existing facts in Python to compare SHA-256 keys. This is O(episodes * existing_facts) — a cross-product scan.
- The verification doc (`verification.md:119`) itself acknowledges: "No `content_hash` column on `SemanticFacts`; O(n) per fact. Production deployment should add `content_hash` column with a unique constraint for O(1) dedup."
- On restart after a crash mid-consolidation, it would re-scan all episodes and re-check all facts. The dedup prevents double-insert, but the performance cost is severe at scale.

**The watermark parameter exists but is never used by the job wrapper.** There is no persisted watermark (no last-run timestamp stored anywhere). Every run is a full-table re-scan with dedup.

[MEDIUM] — Idempotent in correctness, but O(n^2) in performance and no watermark persistence.

---

## (d) prune_stale_facts — Could It Prune Facts Still in Use?

**File:** `C:/Users/faizz/guinevere/src/memory/consolidation.py`, lines 700-777

The `RetentionConfig` defaults (lines 237-267):
- `max_age_days: int = 365` — only facts older than 1 year are eligible
- `protected_categories: ["strategy", "preference"]` — these tags are never pruned
- `protected_importance_floor: float = 0.7` — facts with confidence >= 0.7 are never pruned
- `mode: str = "archive"` — default is metadata-only (sets `deletion_state='archived'`, does NOT delete the row)

**The pruning function (line 730-777) checks three protections:**
1. Protected categories (tags containing "strategy" or "preference") — line 736-741
2. High-importance facts (confidence >= 0.7) — line 744-746
3. Age (created_at < max_age_days) — line 749-753

**Could it prune facts still in use?**
- Consolidation produces facts with `confidence: 0.7` (summary facts, line 601) and `confidence: 0.6` (insight facts, line 613) and `confidence: 0.5` (fallback facts, line 626).
- Summary facts (0.7) are exactly at the protection floor — they pass the `>= 0.7` check and are protected.
- Insight facts (0.6) and fallback facts (0.5) are NOT protected by importance floor. After 365 days, they could be archived.
- However, since `mode="archive"` is default, the row is preserved — only `deletion_state` changes. The fact is not deleted from the table.

**Risk assessment:** LOW for data loss (archive mode preserves rows). But the confidence values for consolidated facts (0.5-0.7) sit right at the protection boundary. If someone changes `protected_importance_floor` to 0.8, summary facts would become eligible for archival. The design is fragile at the boundary.

[LOW] — Default mode is safe (archive). But protection thresholds are tight.

---

## (e) APScheduler Dependency in pyproject.toml

**File:** `C:/Users/faizz/guinevere/pyproject.toml`, line 17

```
"apscheduler>=3",
```

APScheduler v3 is declared as a project dependency. This is correct — the consolidation module uses APScheduler v3 `AsyncIOScheduler` API (`scheduler.add_job()` with keyword arguments).

[MATCH] — Dependency is declared.

---

## (f) Systemd/Cron Alternatives for Out-of-Band Consolidation

**There is NO systemd timer or cron job that runs consolidation out-of-band.**

Examined:
- `C:/Users/faizz/guinevere/systemd/guinevere-scheduler.service` — This runs `src.loops.scheduler` (the LoopScheduler for daily rituals/loops), NOT the memory consolidation scheduler. The LoopScheduler (`src/loops/scheduler.py`) has zero references to `consolidat`, `decay_sweep`, `register_decay`, or `register_consolidation`.
- No `.timer` files relate to memory consolidation. The existing timers are: `guinevere-shadow-monitor.timer`, `guinevere-health-check.timer`, `guinevere-backup-weekly@.timer`, `guinevere-backup@.timer`, `guinevere-prune-weekly@.timer`, `guinevere-wearable-analysis.timer`, `guinevere-wearable-sync.timer`.
- `guinevere-prune-weekly@.timer` appears to be for general pruning, not memory consolidation.
- No Python scripts in `scripts/` call consolidation.
- No CLI entry points in `src/` invoke consolidation.
- The `src/loops/scheduler.py` `main()` entry point (line 158) starts only the LoopScheduler, which schedules daily rituals via `add_daily_ritual()` — not memory consolidation.

**There is no out-of-band mechanism to run consolidation.** The only path is the commented-out code in `main.py`.

[CRITICAL] — No alternative execution path exists.

---

## (g) P18 Decay Sweep (register_decay_job) — Same Gap

**File:** `C:/Users/faizz/guinevere/src/memory/consolidation.py`, lines 1087-1127

`register_decay_job()` is defined and exported via `src/memory/__init__.py` (lines 114, 272, 279). It registers a 6-hourly interval sweep for FSRS decay and active forgetting.

**Grep confirms zero live call sites:**
- `register_decay_job` appears only in:
  - `src/memory/__init__.py` — re-export (lines 114, 272, 279)
  - `src/memory/consolidation.py` — function definition (line 1087)

**It is never called in `main.py` lifespan, never called in any systemd service, never called in any script.** The decay sweep is dead code in production.

This means FSRS spaced repetition review scores are never updated after initial creation, and episodes older than 90 days with low retrievability are never archived.

[CRITICAL] — Decay sweep is not wired anywhere.

---

## (h) P3-015 Evidence — What It Actually Claims vs. What It Implies

**File:** `C:/Users/faizz/guinevere/docs/setup-evidence/P3/STEP-P3-015/verification.md`

**What the verification document explicitly says:**

Line 21-22: "`src/core/main.py`: Added doc-commented integration surface with instructions for activating the scheduler when a DB sessionmaker is available. **No live services started.**"

Line 122: "No `systemctl` / service integration -- All testing is synthetic/unit-level; scheduler activation requires DB sessionmaker"

Line 125: "The `register_consolidation_job()` helper requires an active `AsyncIOScheduler` and a valid async DB `session_factory`. **Neither exists in the current `main.py` bootstrap.** To activate in production: create `AsyncSessionLocal`..."

**The auditor gate** (`auditor-gate.md`) line 123: "APScheduler activation requires runtime DB sessionmaker: `register_consolidation_job()` and `daily_consolidation_job()` are tested with synthetic sessions. **Production activation needs** `async_sessionmaker(engine)` + `AsyncIOScheduler.start()` in the app lifespan, as documented in `main.py`. **This is a documented limitation, not a defect.**"

**Assessment:** The verification document is honest about the limitation. It correctly states the scheduler is not running. However, the auditor gate's verdict of "PASS" with the framing "This is a documented limitation, not a defect" is misleading. A consolidation scheduler that is code-complete but never activated is not a limitation — it is an incomplete deployment. The auditor should have flagged this as a gating issue rather than calling it PASS with a caveat.

The verification document's AC mapping (line 150) claims "Scheduler registers `daily_consolidation` at 03:00 Asia/Bangkok: PASS" — but this PASS is for the test that verifies `register_consolidation_job()` correctly configures a mock scheduler, not that the scheduler is actually running in production. The acceptance criteria were written to test code correctness, not operational liveness.

[HIGH] — Evidence is technically honest but auditor gate is misleading. PASS verdict on a non-running scheduler creates false confidence.

---

## (i) Production State of semantic_facts — Impact Analysis

**If consolidation has never run (confirmed by code audit):**

1. **`semantic_facts` table exists** (created by migration `e401bb5fd274_initial_schema_47_tables.py`, line 447) but contains zero rows from consolidation. Any rows would be from other sources (manual insertion, tests, or the inline KG hook on a hypothetical manual consolidation call).

2. **P3 memory is single-tier:** Only episodes. The semantic fact layer described in the Memory Schema v2.0 is architecturally present but operationally empty.

3. **Hybrid recall (`recall_memories`) degrades gracefully** — it queries both tables and merges results. With empty semantic_facts, it returns only episode-based results. The system does not crash, but the semantic tier contributes nothing.

4. **KG ingestion cron runs daily at 03:30 ICT** (wired in `main.py:167-201`) but processes zero facts every run since `semantic_facts` is empty. This is wasted compute.

5. **The P3 recall quality claims** (if any exist in benchmark docs) cannot be validated against production since the semantic tier is inactive.

**Net assessment: P3 is PARTIALLY IMPLEMENTED (code-complete, not running).**

---

## COMPARATIVE ANALYSIS: What IS Running vs. What IS NOT

| Component | Status | Evidence |
|---|---|---|
| Monthly report scheduler | RUNNING | `main.py:116-120`, `register_monthly_report_scheduler()` called and started |
| KG ingestion cron (03:30 ICT) | RUNNING | `main.py:167-201`, `register_kg_ingestion_job()` called, `kg_scheduler.start()` called |
| Surveillance consumer | RUNNING | `main.py:123-165`, task created and started |
| Heartbeat service | RUNNING | `main.py:401-411`, `heartbeat.start()` called |
| **Memory consolidation (03:00 ICT)** | **NOT RUNNING** | `main.py:22-38` — commented out |
| **P18 decay sweep (6-hourly)** | **NOT RUNNING** | Not referenced in `main.py` at all |

The pattern is clear: the consolidation and decay schedulers are the only two APScheduler jobs that were **not** wired into the lifespan. Every other scheduled job is live.

---

## FINDINGS SUMMARY

| # | Finding | Severity | Location |
|---|---|---|---|
| F-1 | `register_consolidation_job` is commented out in `main.py`; zero live call sites anywhere in `src/` | [CRITICAL] | `main.py:22-38` |
| F-2 | `register_decay_job` (P18 decay sweep) is never called anywhere in production code | [CRITICAL] | Not in `main.py` lifespan |
| F-3 | `semantic_facts` table is empty in production; P3 is single-tier (episodes only) | [CRITICAL] | Consequence of F-1 |
| F-4 | KG ingestion cron runs daily but is a no-op (zero semantic facts to process) | [HIGH] | `main.py:167-201` |
| F-5 | No watermark persistence; `daily_consolidation_job` calls `consolidate_episodes_to_facts(session)` without watermark; relies on O(n^2) content-key dedup | [MEDIUM] | `consolidation.py:823` |
| F-6 | `_fact_exists_by_key` does full-table scan + Python iteration (O(n) per fact); no `content_hash` column | [MEDIUM] | `consolidation.py:648-668` |
| F-7 | P3-015 auditor gate gives PASS despite scheduler not running; framing as "documented limitation, not a defect" is misleading | [HIGH] | `auditor-gate.md:123` |
| F-8 | No systemd timer, cron job, or CLI entry point provides alternative execution path for consolidation | [CRITICAL] | Audit of all `.service`, `.timer`, `scripts/` |
| F-9 | `prune_stale_facts` protection floor (0.7) is exactly at the confidence of consolidated summary facts; fragile boundary | [LOW] | `consolidation.py:245, 601` |
| F-10 | APScheduler dependency declared in pyproject.toml (line 17) — correctly present | [MATCH] | `pyproject.toml:17` |

---

## VERDICT

**P3 Memory Foundation is PARTIALLY IMPLEMENTED (code-complete, not running).**

The consolidation engine (`src/memory/consolidation.py`) is well-designed and well-tested (50 unit tests, all passing). The idempotency, DNR exclusion, safe-word filtering, classification preservation, and pruning safety are all correctly implemented at the code level. The code quality is high.

However, the critical integration step — wiring `register_consolidation_job()` into the application lifespan at `main.py` — was never done. The code sits behind a comment block. The decay sweep is similarly unwired. No alternative execution path (systemd timer, cron, CLI) exists.

As a result:
- `semantic_facts` is empty in production
- The semantic tier of P3 memory is non-functional
- The KG ingestion cron runs but processes nothing
- FSRS decay/forgetting never executes
- P3 functions as episodes-only memory with no semantic layer

**This is not a "documented limitation." This is an incomplete deployment.** The P3-015 auditor gate PASS verdict is technically accurate for code-level acceptance criteria but operationally misleading. The scheduler needs to be wired into the `main.py` lifespan (alongside the already-running KG and report schedulers) before P3 can claim its semantic memory tier is operational.

---

## REMEDIATION REQUIRED (for mama, no fixes in this audit)

1. Wire `register_consolidation_job()` into `main.py` lifespan, using the same `_session_factory` already created for the surveillance consumer (lines 148-152).
2. Wire `register_decay_job()` into the same or adjacent scheduler.
3. Add a `content_hash` column to `semantic_facts` for O(1) dedup (eliminate the O(n^2) scan).
4. Consider persisting a watermark timestamp so consolidation does not re-scan all episodes every run.
5. Add a health-check endpoint or Prometheus metric that reports last successful consolidation run time.