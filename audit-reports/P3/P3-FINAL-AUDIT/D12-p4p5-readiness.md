# D12 — P4/P5 Readiness Audit

| Field | Value |
|---|---|
| Dimension | 12 — P4/P5 Readiness |
| Scope | Verify P3 APIs, schemas, and wiring are stable and consumable by P4 (Persona Engine) and P5 (Agent Loop) |
| Date | 2026-06-02 |
| Auditor | Guinevere Final Audit Suite |
| Status | **PASS** (17 PASS, 1 NEEDS REVIEW, 0 FAIL) |

---

## §1 Summary

| Area | Checkpoints | PASS | NEEDS REVIEW | FAIL |
|---|---|---|---|---|
| Memory Write API (P4) | 3 | 3 | 0 | 0 |
| Memory Read API (P5) | 3 | 3 | 0 | 0 |
| DNR API | 2 | 2 | 0 | 0 |
| Safe-mode gate | 2 | 2 | 0 | 0 |
| Consolidation job | 2 | 1 | 1 | 0 |
| Database schema (P4) | 3 | 3 | 0 | 0 |
| No P3 blockers for P4/P5 | 2 | 2 | 0 | 0 |
| API stability | 2 | 2 | 0 | 0 |
| **Total** | **19** | **18** | **1** | **0** |

**Overall Verdict: PASS** — All P3 APIs required by P4 and P5 are implemented, exported, and stable. One NEEDS REVIEW item (consolidation scheduler not auto-wired in `main.py`) is a documented deployment decision, not a code defect.

---

## §2 Memory Write API — Available for P4

### CP-01: `store_episode` and `store_episode_batch` exported from `src.memory`

**Verdict: PASS**

| Check | Evidence |
|---|---|
| `store_episode` imported in `__init__.py` | Line 39: `from src.memory.write_pipeline import store_episode` |
| `store_episode_batch` imported in `__init__.py` | Line 40: `from src.memory.write_pipeline import store_episode_batch` |
| `store_episode` in `__all__` | Line 150 |
| `store_episode_batch` in `__all__` | Line 151 |

### CP-02: Function signatures match specification

**Verdict: PASS**

**`store_episode`** (lines 111-125, `src/memory/write_pipeline.py`):

```python
async def store_episode(
    session: EpisodeSession,
    content: str,
    *,
    source: str,
    classification: str = RESTRICTED,
    importance: int = 5,
    title: str | None = None,
    summary: str | None = None,
    episode_type: str = "conversation",
    tags: list[str] | None = None,
    metadata: JsonObject | None = None,
    embedding_service: EmbeddingClient | None = None,
    started_at: datetime | None = None,
) -> uuid.UUID
```

Signature matches specification exactly. Return type `uuid.UUID` confirmed.

**`store_episode_batch`** (lines 235-240):

```python
async def store_episode_batch(
    session: EpisodeSession,
    episodes: list[JsonObject],
    *,
    embedding_service: EmbeddingClient | None = None,
) -> list[uuid.UUID]
```

Signature matches specification exactly.

### CP-03: Importable from `src.memory`

**Verdict: PASS**

Both functions are imported at the package level (`src/memory/__init__.py`) and listed in `__all__`. Any P4/P5 consumer can write `from src.memory import store_episode, store_episode_batch`.

---

## §3 Memory Read API — Available for P5

### CP-04: `recall_memories` exported from `src.memory`

**Verdict: PASS**

| Check | Evidence |
|---|---|
| `recall_memories` imported in `__init__.py` | Line 116: `from src.memory.read_pipeline import recall_memories` |
| In `__all__` | Line 184 |

### CP-05: `recall_memories` function signature matches specification

**Verdict: PASS**

Signature (lines 727-737, `src/memory/read_pipeline.py`):

```python
async def recall_memories(
    session: RecallSession,
    query_text: str,
    limit: int = 20,
    *,
    exclude_dnr: bool = True,
    safe_mode: bool = False,
    principal: str = "guinevere_core",
    embedding_service: EmbeddingClient | None = None,
    token_budget: int = DEFAULT_TOKEN_BUDGET,  # = 4000
) -> RecallResults  # list[dict[str, object]]
```

All parameters match specification:
- `limit=20` — matches
- `exclude_dnr=True` — matches
- `safe_mode=False` — matches
- `principal="guinevere_core"` — matches
- `embedding_service=None` — matches
- `token_budget=4000` (via `DEFAULT_TOKEN_BUDGET`) — matches
- Return type `list[dict[str, object]]` (via `RecallResults` alias) — matches

### CP-06: `assemble_system_prompt_with_memory` available in `prompt_loader`

**Verdict: PASS**

Function exists at `src/core/services/prompt_loader.py` lines 119-182.

```python
async def assemble_system_prompt_with_memory(
    session: RecallSession,
    query_text: str,
    *,
    mood: str = "Content",
    safe_mode: bool = False,
    hard_stop_handler: object | None = None,
    principal: str = "guinevere_core",
    limit: int = 3,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    embedding_service: EmbeddingClient | None = None,
) -> str
```

Orchestrates: recall -> format -> inject -> return. Integrates `recall_memories()` with `get_system_prompt_with_context()`.

---

## §4 DNR API — Available

### CP-07: DNR mark/unmark/verify APIs exported from `src.memory`

**Verdict: PASS**

| API | Imported in `__init__.py` | In `__all__` | Defined in `dnr.py` |
|---|---|---|---|
| `mark_memory_dnr` | Line 70 | Line 189 | Lines 179-257 |
| `unmark_memory_dnr` | Line 71 | Line 190 | Lines 265-345 |
| `is_memory_dnr` | Line 72 | Line 191 | Lines 353-373 |
| `verify_recall_results_dnr_free` | Line 74 | Line 192 | Lines 385-418 |
| `DNRAuthorizationError` | Line 66 | Line 186 | Line 61 |
| `DNRStateError` | Line 67 | Line 187 | Line 65 |
| `DNRViolationError` | Line 68 | Line 188 | Line 381 |

### CP-08: DNR API surface and query-level filter

**Verdict: PASS**

**Mutation APIs:**
- `mark_memory_dnr(session, memory_id, *, reason, principal="guinevere_core") -> uuid.UUID` — authorized, audited, fail-closed
- `unmark_memory_dnr(session, memory_id, *, reason, principal="guinevere_core") -> uuid.UUID` — authorized, audited, fail-closed
- `is_memory_dnr(session, memory_id) -> bool` — query helper

**Pre-injection guard:**
- `verify_recall_results_dnr_free(results) -> None` — raises `DNRViolationError` if any DNR entry detected

**Query-level DNR filter:**
- `recall_memories()` defaults to `exclude_dnr=True` (line 732)
- All 3 query builders (`build_vector_query`, `build_fts_query`, `build_recency_query`) apply `.where(Episodes.do_not_recall.is_(False))` when `exclude_dnr=True`
- Double-check in consolidation: `consolidate_episodes_to_facts()` filters `do_not_recall` at query level (line 274) and defensively re-checks per episode (line 289)

---

## §5 Safe-Mode Gate — Wired

### CP-09: HardStopHandler integration in `prompt_loader`

**Verdict: PASS**

| Element | Evidence |
|---|---|
| `hard_stop_handler` parameter | `prompt_loader.py` line 125: `hard_stop_handler: object | None = None` |
| `is_safe` property resolution | Lines 156-158: `resolved_safe_mode = bool(getattr(hard_stop_handler, "is_safe", False))` |
| Authoritative override | `hard_stop_handler.is_safe` overrides the explicit `safe_mode` parameter when handler is provided |
| HardStopHandler class | `src/core/services/hard_stop_handler.py` line 34, `.is_safe` property at line 60-61 |

The HardStopHandler is a P1 component that is correctly consumed by P3's prompt loader. The integration pattern uses duck-typing (`getattr`) for loose coupling, which is architecturally sound.

### CP-10: `safe_mode` parameter propagation chain

**Verdict: PASS**

Full propagation chain verified:

1. **Entry**: `assemble_system_prompt_with_memory(safe_mode, hard_stop_handler)` (prompt_loader.py:119)
2. **Resolution**: `resolved_safe_mode = hard_stop_handler.is_safe` if handler provided, else `safe_mode` (lines 155-158)
3. **Recall**: `recall_memories(safe_mode=resolved_safe_mode)` (line 166)
4. **Ceiling downgrade**: `_resolve_ceiling(principal, safe_mode)` (read_pipeline.py:804) — downgrades classification ceiling in safe mode
5. **Content substitution**: `build_safe_content(episode, safe_mode)` (read_pipeline.py:873) — substitutes raw content with placeholders
6. **Three-layer defense**:
   - Classification ceiling downgrade (guinevere_core -> Internal in safe mode)
   - Content substitution (Critical -> placeholder, Restricted/Confidential -> summary or placeholder)
   - Emotional/surveillance/persona-escalation content blocking via tag/episode_type/source inspection

---

## §6 Consolidation Job — Schedulable

### CP-11: `daily_consolidation` function is callable

**Verdict: PASS**

| Function | File | Line | Callable |
|---|---|---|---|
| `consolidate_episodes_to_facts` | `src/memory/consolidation.py` | 241 | Yes — async, accepts `session` + optional `watermark`/`now` |
| `daily_consolidation_job` | `src/memory/consolidation.py` | 648 | Yes — async, accepts optional `session_factory` |
| `register_consolidation_job` | `src/memory/consolidation.py` | 714 | Yes — async, accepts `scheduler` + optional `session_factory` |

All three are exported from `src.memory` (__init__.py lines 48-56).

`daily_consolidation_job` handles `session_factory=None` gracefully: logs warning and returns empty `ConsolidationResult()`.

### CP-12: Job registration code exists in `main.py`

**Verdict: NEEDS REVIEW**

| Check | Evidence |
|---|---|
| Active registration | **NOT active** — `main.py` does not call `register_consolidation_job()` |
| Documentation | Lines 8-25 contain a comment block documenting the activation pattern with exact code |
| Intentional decision | Comment explicitly states: "DO NOT start a live APScheduler without a valid async DB sessionmaker" |
| D09 audit finding | Same finding: "NEEDS REVIEW — not a defect, deployment decision" |

**Assessment:** The consolidation infrastructure is fully implemented and correctly configured (cron at 03:00 Asia/Bangkok, APScheduler v3, `replace_existing=True`, `misfire_grace_time=3600`). The decision to not auto-wire it is intentional — it requires a valid async DB `sessionmaker` that is not available in all environments.

**For P4/P5:** This is NOT a blocker. P4 (Persona Engine) and P5 (Agent Loop) can call `consolidate_episodes_to_facts()` directly or register the job when deploying with a live database. The activation pattern is documented and ready to uncomment.

---

## §7 Database Schema — Ready for P4

### CP-13: P4-related `persona.*` tables exist in `models.py`

**Verdict: PASS**

The `persona` schema contains 5 tables that directly support P4 (Persona Engine):

| Table | Class | Schema | Key Columns | P4 Use |
|---|---|---|---|---|
| `persona_state` | `PersonaState` | `persona` | `state_key`, `state_value` (JSONB), `updated_by` | Current persona state storage |
| `drift_log` | `DriftLog` | `persona` | `drift_type`, `before_state`, `after_state`, `delta`, `safety_score`, `rollback_available` | Persona drift detection and rollback |
| `mood_history` | `MoodHistory` | `persona` | `mood`, `intensity`, `trigger`, `duration_minutes` | Mood tracking and history |
| `punishment_log` | `PunishmentLog` | `persona` | `violation_type`, `severity`, `safe_word_triggered`, `safe_word_bypassed` | Punishment system logging |
| `reward_log` | `RewardLog` | `persona` | `reward_type`, `streak_count` | Reward system logging |

Additional supporting tables in `memory` schema:

| Table | P4 Use |
|---|---|
| `EmotionalEvents` | Emotional event tracking (linked to episodes) |
| `InnerJournal` | Persona self-reflection journal |
| `FaizPredictions` | Behavioral predictions about operator |
| `Episodes` (with `mood_at_start`, `mood_at_end`, `emotional_tone`, `faiz_behavior` columns) | Mood and emotional state per episode |

### CP-14: 47-table migration includes P4 tables

**Verdict: PASS**

| Check | Evidence |
|---|---|
| Migration ID | `e401bb5fd274_initial_schema_47_tables` (D03 §2) |
| Table count | 47 tables across 12 schemas |
| Persona schema | 5 tables (PersonaState, DriftLog, MoodHistory, PunishmentLog, RewardLog) |
| Verified on VPS | D03 confirms all 47 tables deployed on PostgreSQL 16 |

Schema breakdown:
- `memory`: 8 tables
- `persona`: 5 tables
- `surveillance`: 4 tables
- `financial`: 4 tables
- `projects`: 4 tables
- `social`: 3 tables
- `agents`: 3 tables
- `consent`: 3 tables
- `security`: 3 tables
- `audit`: 3 tables
- `ops`: 4 tables
- `extensions`: 3 tables

### CP-15: P3 evidence confirms table inventory

**Verdict: PASS**

| Source | Claim | Verified |
|---|---|---|
| D03-database-integrity | "47 tables, 12 schemas, 61 indexes, 2 HNSW, 11 FKs, 4 hypertables" | Yes — full audit PASS |
| D03 §3 | "SELECT 1 succeeds on all 47 tables" | Yes — VPS verification |
| D03 §6.3 | "ClassificationMetaMixin applied to 41 of 47 tables" | Yes — 6 exempt tables are operational/non-classified |

---

## §8 No P3 Blocking Items for P4/P5

### CP-16: Compile and assess all P3 caveats

**Verdict: PASS**

All P3 caveats from 10 audit dimensions assessed for P4/P5 blocking potential:

| Source | Caveat | P4 Blocker? | P5 Blocker? | Assessment |
|---|---|---|---|---|
| D01 | P3-001 auditor FAIL (Alembic) | NO | NO | Deployment tooling, not API |
| D01 | StepPrompts.md stale | NO | NO | Documentation hygiene |
| D01 | PROGRESS.md conflicting counts | NO | NO | Documentation hygiene |
| D01 | Batch plans lack scaffolds | NO | NO | Process compliance, not API |
| D02 | LSP errors (structlog, discord.py) | NO | NO | Environment issue, code is correct |
| D03 | alembic.ini/migration files absent locally | NO | NO | VPS-only artifacts |
| D04 | .gitignore patterns (.env*, age-key*) | NO | NO | Advisory defense-in-depth |
| D07 | Plaintext backup secrets (gitignored) | NO | NO | Pre-P3, local-only |
| D09 | Consolidation not auto-wired | NO | NO | Deployment decision, API available |
| D10 | Missing monitoring/alerting | NO | NO | Operational tooling gap |
| D10 | Missing runbooks | NO | NO | Operational documentation |
| D10 | content_hash O(1) optimization | NO | NO | Performance optimization |
| D10 | Classification ceiling SQL pushdown | NO | NO | Performance optimization |

**Conclusion: ZERO hard blockers for P4 or P5.** All caveats are documentation hygiene, deployment decisions, environment issues, or performance optimizations — none affect API availability or correctness.

### CP-17: Missing imports, broken APIs, or incomplete wiring

**Verdict: PASS**

| Check | Result |
|---|---|
| All P3 functions exported from `src.memory.__init__` | Confirmed — `store_episode`, `store_episode_batch`, `recall_memories`, DNR APIs, consolidation APIs all in `__all__` |
| `assemble_system_prompt_with_memory` importable | Confirmed — defined in `src/core/services/prompt_loader.py` |
| `HardStopHandler` importable by P5 | Confirmed — defined in `src/core/services/hard_stop_handler.py`, used by `src/discord/cmd_safeword.py` |
| Protocol compatibility | Confirmed — `EpisodeSession`, `RecallSession`, `DNRSession`, `EmbeddingClient` protocols match SQLAlchemy `AsyncSession` subset |
| ORM models referenced correctly | Confirmed — `Episodes`, `SemanticFacts`, `AuditTrail` imported and used consistently |
| No circular imports | Confirmed — clean dependency graph: embeddings -> models -> write/read/dnr/consolidation -> prompt_loader |

---

## §9 API Stability

### CP-18: P3 APIs have stable signatures (no TODO/FIXME)

**Verdict: PASS**

Grep for `TODO|FIXME|HACK|XXX|BROKEN` across all `src/memory/*.py` files: **0 matches**.

All function signatures are concrete with:
- Typed parameters (no bare `Any`)
- Explicit defaults
- Complete docstrings
- Return type annotations

### CP-19: No TODO/FIXME/HACK affecting API stability

**Verdict: PASS**

| File | TODO/FIXME Count |
|---|---|
| `src/memory/__init__.py` | 0 |
| `src/memory/embeddings.py` | 0 |
| `src/memory/write_pipeline.py` | 0 |
| `src/memory/read_pipeline.py` | 0 |
| `src/memory/dnr.py` | 0 |
| `src/memory/consolidation.py` | 0 |
| `src/memory/models.py` | 0 |

Zero technical debt markers in the entire memory module. APIs are stable and production-ready for P4/P5 consumption.

---

## §10 Detailed Verdict Table

| CP | Checkpoint | Verdict | Evidence |
|---|---|---|---|
| 01 | `store_episode` / `store_episode_batch` exported | **PASS** | `__init__.py` lines 39-40, 150-151 |
| 02 | Write API signatures match spec | **PASS** | `write_pipeline.py` lines 111-125, 235-240 |
| 03 | Importable from `src.memory` | **PASS** | Package-level imports + `__all__` |
| 04 | `recall_memories` exported | **PASS** | `__init__.py` line 116, 184 |
| 05 | `recall_memories` signature matches spec | **PASS** | `read_pipeline.py` lines 727-737 |
| 06 | `assemble_system_prompt_with_memory` available | **PASS** | `prompt_loader.py` lines 119-182 |
| 07 | DNR mark/unmark/verify APIs exported | **PASS** | `__init__.py` lines 64-78, 186-194 |
| 08 | DNR API surface + query-level filter | **PASS** | `dnr.py` lines 179-418; read_pipeline `exclude_dnr` |
| 09 | HardStopHandler integration | **PASS** | `prompt_loader.py` lines 125, 155-158 |
| 10 | safe_mode propagation chain | **PASS** | 6-step chain verified, 3-layer defense confirmed |
| 11 | `daily_consolidation` callable | **PASS** | `consolidation.py` lines 241, 648, 714 |
| 12 | Job registration in `main.py` | **NEEDS REVIEW** | Comment block documents activation; intentional deployment decision |
| 13 | P4 `persona.*` tables exist | **PASS** | 5 persona tables + 4 supporting memory tables |
| 14 | 47-table migration includes P4 tables | **PASS** | `e401bb5fd274` verified on VPS |
| 15 | P3 evidence confirms table inventory | **PASS** | D03 audit: 47 tables, 12 schemas verified |
| 16 | No P3 caveats block P4/P5 | **PASS** | 13 caveats assessed, 0 blockers |
| 17 | No broken imports/wiring | **PASS** | All exports, protocols, ORM references verified |
| 18 | Stable API signatures | **PASS** | 0 TODO/FIXME/HACK in src/memory/ |
| 19 | No API stability risks | **PASS** | All 7 memory files clean |

---

## §11 P4/P5 API Consumption Summary

### APIs available for P4 (Persona Engine — 23 steps):

| API | Import Path | Purpose for P4 |
|---|---|---|
| `store_episode` | `src.memory` | Store persona state changes as episodes |
| `store_episode_batch` | `src.memory` | Batch store mood/punishment/reward events |
| `mark_memory_dnr` | `src.memory` | Mark traumatic episodes as do-not-recall |
| `unmark_memory_dnr` | `src.memory` | Reverse DNR when appropriate |
| `is_memory_dnr` | `src.memory` | Query DNR state of specific memories |
| `Episodes` (ORM) | `src.memory.models` | Direct ORM access with `mood_at_start`, `mood_at_end`, `emotional_tone`, `faiz_behavior` columns |
| `PersonaState` (ORM) | `src.memory.models` | Persona state storage |
| `DriftLog` (ORM) | `src.memory.models` | Drift detection logging |
| `MoodHistory` (ORM) | `src.memory.models` | Mood history tracking |
| `PunishmentLog` (ORM) | `src.memory.models` | Punishment system |
| `RewardLog` (ORM) | `src.memory.models` | Reward system |
| `EmotionalEvents` (ORM) | `src.memory.models` | Emotional event recording |
| `InnerJournal` (ORM) | `src.memory.models` | Persona self-reflection |

### APIs available for P5 (Agent Loop — 23 steps):

| API | Import Path | Purpose for P5 |
|---|---|---|
| `recall_memories` | `src.memory` | Hybrid memory recall for context injection |
| `assemble_system_prompt_with_memory` | `src.core.services.prompt_loader` | Full system prompt with memory context |
| `verify_recall_results_dnr_free` | `src.memory` | Pre-injection DNR guard |
| `HardStopHandler` | `src.core.services.hard_stop_handler` | HARD STOP detection (P1, consumed by P5) |
| `consolidate_episodes_to_facts` | `src.memory` | Trigger consolidation on demand |
| `daily_consolidation_job` | `src.memory` | Scheduled consolidation |
| `register_consolidation_job` | `src.memory` | Register APScheduler job |
| `store_episode` | `src.memory` | Store agent loop execution episodes |
| `SemanticFacts` (ORM) | `src.memory.models` | Access consolidated semantic facts |

---

## §12 Recommendations

### For P4 (Persona Engine):

1. **Direct ORM access**: P4 can use `PersonaState`, `DriftLog`, `MoodHistory`, `PunishmentLog`, `RewardLog` ORM models directly from `src.memory.models` — all table definitions are complete with `ClassificationMetaMixin`.

2. **Episode metadata**: The `Episodes` model already includes `mood_at_start`, `mood_at_end`, `emotional_tone`, and `faiz_behavior` (JSONB) columns. P4 can populate these during episode writes via `store_episode(metadata={...})`.

3. **DNR for safe-word episodes**: P4 should use `mark_memory_dnr()` for episodes associated with HARD STOP events, ensuring they never resurface in recall.

### For P5 (Agent Loop):

1. **Memory injection**: Use `assemble_system_prompt_with_memory()` as the primary integration point. Pass the `HardStopHandler` instance for authoritative safe-mode resolution.

2. **Post-recall guard**: Call `verify_recall_results_dnr_free()` as a defense-in-depth check before injecting memories into the LLM prompt.

3. **Consolidation scheduling**: When deploying P5 with a live database, uncomment `main.py` lines 8-25 to activate the daily consolidation job. The API is ready.

---

## §13 Caveats and Known Limitations

| ID | Caveat | Severity | Impact on P4/P5 |
|---|---|---|---|
| C1 | Consolidation scheduler not auto-wired in `main.py` | LOW | P5 must activate during deployment; API is ready |
| C2 | `_fact_exists_by_key` iterates all facts (O(n)) | LOW | Documented for production optimization; not blocking |
| C3 | Classification ceiling filter is Python post-processing, not SQL | LOW | Deferred optimization; functional correctness verified |
| C4 | Alembic migration files exist only on VPS | LOW | Deployment hygiene; does not affect API availability |
| C5 | Empty vector tables (0 rows at audit time) | INFORMATIONAL | HNSW indexes valid; will show Index Scan once populated |

---

## §14 Boundary Compliance

- No secrets exposed in this report
- No intimate/personal data
- No raw surveillance data
- Persona boundaries: audit describes ORM table structures for persona domain without interpreting persona behavior
- Consent: DNR APIs correctly enforce consent revocation at the data level

---

## §15 Footer

| Field | Value |
|---|---|
| Report | D12-p4p5-readiness.md |
| Dimension | 12 of 12 — P4/P5 Readiness |
| Files Audited | `src/memory/__init__.py`, `src/memory/write_pipeline.py`, `src/memory/read_pipeline.py`, `src/memory/dnr.py`, `src/memory/consolidation.py`, `src/memory/models.py`, `src/core/services/prompt_loader.py`, `src/core/services/hard_stop_handler.py`, `src/core/main.py` |
| Cross-references | D01 through D10 audit reports |
| Verdict | **PASS** (18 PASS, 1 NEEDS REVIEW, 0 FAIL) |

**P3 provides stable, complete, and well-documented APIs for P4 (Persona Engine) and P5 (Agent Loop) consumption. No blocking items identified. P4/P5 can proceed without requiring P3 modifications.**
