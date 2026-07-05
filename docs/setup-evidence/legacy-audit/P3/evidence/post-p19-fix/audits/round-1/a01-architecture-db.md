# Lane B (P3 Post-P19 Memory Fix) — Architecture & DB Schema Audit Report

**Round:** 1 — Pre-fix baseline audit
**Auditor:** Independent auditor (subagent)
**Date:** 2026-06-27
**Scope:** Schema correctness, project isolation, idempotency, NULL-fallback, P19 namespace compliance.

---

## 1. Executive Summary

Lane B's stated intent — "every write requires a `project_id`, and every `SemanticFacts` row carries its source episode's namespace" — is conceptually sound but the implementation has multiple alignment gaps between ORM, migration, write path, consolidation fallback, and the public API surface:

| # | Finding | Severity |
|---|---|---|
| F-01 | ORM declares `nullable=True` for `Episodes.project_id` and `SemanticFacts.project_id`, but the new migration enforces `NOT NULL` on those columns. Migration will apply, but new ORM writes will diverge from the live DB schema. | **CRITICAL** |
| F-02 | `store_episode` / `store_episode_batch` accept `project_id: uuid.UUID | None = None`. There is no API-level guard against `None`; callers passing `None` will produce rows that violate the new NOT NULL constraint. | **CRITICAL** |
| F-03 | `SemanticFacts.project_id` mirror column on consolidation accepts the per-episode project_id, but the comment on Episode ORM claims NULL = "global-scope entity", which contradicts the P19 namespace contract once NOT NULL is enforced. | HIGH |
| F-04 | `consolidate_episodes_to_facts` falls back to `ProjectRegistry.DEFAULT_PROJECT_ID` for legacy episodes with NULL `project_id`. This silently re-classifies null-episode rows into the canonical default bucket, breaking project isolation invariants and the contract that "NULL = global-scope legacy data". | HIGH |
| F-05 | `_fact_exists_by_key` performs an O(n) full scan over all `SemanticFacts` rows and re-hashes each on every consolidation run. Idempotency is preserved (deterministic SHA-256) but correctness degrades with table size. | MEDIUM |
| F-06 | P19-002 migration pre-check fails closed on any NULL count, but the fallback in `consolidation.py` actively writes NULL→`DEFAULT_PROJECT_ID` mappings, so post-upgrade re-runs of consolidation BEFORE the backfill script will re-create the same mismatch (contradictory positions). | HIGH |
| F-07 | `store_episode_batch` defaults `project_scope="project"` but a missing `project_id` will silently default to `None` — an inconsistent tuple (`scope="project"`, `project_id=None`) that the constrained schema must reject. | HIGH |
| F-08 | `_DEFAULT_PROJECT_ID` is fixed at `00000000-0000-0000-0000-000000000001` (UUID v4-format reserved range). Mixing sentinel logic with real UUIDs is risky if any real project ever generates that UUID. | LOW |
| F-09 | `AuditTrail.chain_version` comment mentions "P19+ (project_id in payload)" but no migration or assertion enforces that fact rows carry `project_id`. | LOW |
| F-10 | No index on `SemanticFacts.project_id` (or `Episodes.project_id`). P19 namespace-aware queries will full-table-scan. | MEDIUM |

---

## 2. Schema Correctness — Schema ↔ ORM Delta

### 2.1 `Episodes.project_id` and `SemanticFacts.project_id` (F-01 — CRITICAL)

**Live DB** (after P19-002 applies): `memory.episodes.project_id` — `NOT NULL`; `memory.semantic_facts.project_id` — `NOT NULL`.

**ORM** (`src/memory/models.py`):

- `Episodes.project_id`: `Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, comment="P19 project namespace")` (lines 160–162)
- `SemanticFacts.project_id`: `Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, comment="Project namespace UUID. NULL = global-scope entity visible from all projects.")` (lines 266–269)

**Delta:**

The ORM still says `nullable=True` for both columns and types them as `Optional[uuid.UUID]`. After the migration runs live, SQLAlchemy will permit inserts that the Postgres server rejects with an `IntegrityError`. Conversely, `Base.metadata.create_all()` would emit `DROP+CREATE` statements that fight the migration (or fail if it accepts the existing columns as up-to-date).

This is a hard contradiction: the migration's intent ("not null after backfill") and the ORM's permission ("nullable") cannot both be true simultaneously.

**Remediation:** Update `Episodes.project_id` and `SemanticFacts.project_id` to `Mapped[uuid.UUID]` (non-Optional) with `nullable=False`. Update SQLite/dev annotations where appropriate.

### 2.2 `project_scope` declarations

Both `Episodes.project_scope` and `SemanticFacts.project_scope` are correctly `nullable=False` with `server_default=text("'project'")`. This part is consistent.

However, `Episodes.project_scope` in ORM (lines 163–166) uses `nullable=False` but the migration only touches `project_id`, not `project_scope`. If a legacy row exists with NULL `project_scope`, the migration does not address it. Likely safe (default `'project'` was likely added in P19-001) but unverified.

### 2.3 Index coverage (F-10 — MEDIUM)

`SemanticFacts.__table_args__` declares indexes on `source_episode` and `embedding` (HNSW) but **no index on `project_id` or composite `(project_id, project_scope)`**. After NOT NULL applies, project-filtered queries will full-scan and disable index-only plans.

`Episodes.__table_args__` likewise has no `project_id` index. The HNSW embedding index is the dominant cost path so the impact is lower, but project-list queries still suffer.

**Remediation:** Add `Index("ix_semantic_facts_project_id", "project_id")` and a copy on `Episodes.project_id`. Consider composite `(project_id, project_scope)` indexes for "global vs project" partition queries.

---

## 3. Project Isolation — Propagation Audit

### 3.1 `store_episode` and `store_episode_batch` write path (F-02 — CRITICAL, F-07 — HIGH)

`store_episode` (write_pipeline.py:111) accepts `project_id: uuid.UUID | None = None`. The body (lines 200–215) constructs the ORM instance with `project_id=project_id`. If the caller passes `None`, the ORM accepts it (because the column is `nullable=True` in ORM), but Postgres will reject after the migration runs. There is no precondition check at the API boundary.

`store_episode_batch` (write_pipeline.py:245) — per-episode override logic at lines 269–270 correctly coerces fields via `_opt_uuid_field`, but also defaults `project_id` to `None` if both batch-level and per-episode values are absent. Same defect propagates per-episode.

**Remediation:** Tighten signatures:

- `project_id: uuid.UUID` (no default) for all `store_episode*` functions
- Add explicit guard: `if project_id is None: raise WritePipelineError("P19: project_id is required")`
- Update batch helper to require `project_id` at batch level OR per-episode

### 3.2 `consolidation.py` extraction (F-04, F-06 — HIGH)

`consolidate_episodes_to_facts` (line 363–372):

```python
_ep_project_id_raw: object = getattr(ep, "project_id", None)
_ep_project_id: uuid.UUID | None = (
    _ep_project_id_raw if isinstance(_ep_project_id_raw, uuid.UUID)
    else ProjectRegistry.DEFAULT_PROJECT_ID
)
```

The fallback to `ProjectRegistry.DEFAULT_PROJECT_ID` for legacy `NULL` episodes removes the "NULL = legacy unscoped" signal and silently re-buckets all null-episode semantic facts into the default project.

This contradicts:

1. The ORM comment on `SemanticFacts.project_id`: "NULL = global-scope entity visible from all projects."
2. The pre-check in `p19_002_project_id_not_null.py`: if any row has NULL `project_id`, the migration aborts. So how can consolidation ever produce new NULL-PID rows? — it can't, but it can silently rewrite NULL→DEFAULT pre-migration, which then breaks the migration's guarantee that "every row has been explicitly backfilled".

The two systems disagree on what NULL means: the migration treats NULL as a backfill error; consolidation treats NULL as an implicit "this belongs to default".

**Remediation:** Remove the fallback. Consolidation that encounters a NULL-`project_id` episode should:

- Either SKIP the episode and log a `consolidation_legacy_null_project_id` warn event (preserving the NULL semantics), or
- Emit a typed `LegacyEpisodeBackfillNeeded` audit event so the orchestrator can route the episode to `scripts/p19_backfill.py`

The fallback is a silent data-rewrite that violates the "explicit > implicit" principle of P19.

### 3.3 `project_scope` extraction

`_ep_project_scope_raw` correctly defaults to `"project"` (line 369–372) when missing. This is benign because `project_scope` defaults to `'project'` at the DB level too.

---

## 4. Idempotency — Safe Re-Run Analysis

### 4.1 `consolidate_episodes_to_facts` (F-05 — MEDIUM)

Idempotent in principle: `make_content_key` (line 649) produces a deterministic SHA-256 over `(subject, predicate, object_val, source_episode)`, and `_fact_exists_by_key` checks for existing facts before insert.

`_fact_exists_by_key` (lines 664–684) issues `SELECT SemanticFacts *` and Pythonically re-hashes each row. Functionally correct for any size N but performance regression at scale:

- For N = 10K facts, the check is O(N) per inserted fact, so total work is O(N²). With `prune_stale_facts` adding its own full scan (line 741), the consolidation job is O(N²).

**Additional concern:** `_extract_facts_from_episode` produces 1–N facts per episode with naive subjects like `title or f"episode_{getattr(ep, 'id', 'unknown')}"`. If `title` is empty (very common) and the episode has no `key_insights`, every unkeyed episode will collide on `episode_<id>` — which is fine because `_ep_id` is in the content key, but the deduplication is by *content*, not by *project*. Two projects producing identical summaries will get different facts (different `project_id`), but `_fact_exists_by_key` does **NOT** consider `project_id` — so a project-A fact and a project-B fact with identical subject/predicate/object/episode will not collide because the `source_episode` is per-project unique. This works accidentally, not by design.

**Remediation:**

- Add `content_hash BINARY(32)` column with unique index on `(content_hash, project_id)` for O(1) lookup
- Update `make_content_key` to include `project_id` explicitly
- Or keep the in-memory check but cap with pagination + failure-log for O(N²) growth

### 4.2 Re-run safety with NOT NULL migration

If consolidation runs **after** the migration applies:

- It will read only rows where `project_id IS NOT NULL`, since legacy null rows cause migration abort.
- New facts will get `project_id = _ep_project_id` from the per-episode value.
- Safe to re-run: deterministic SHA-256 keys + `_fact_exists_by_key` short-circuit.

If consolidation runs **before** the migration (or until backfill completes):

- The fallback at line 366 silently rewrites NULL→DEFAULT.
- Re-running produces a *different* fact (because `source_episode.project_id` will now be DEFAULT instead of NULL, and `_ep_id` is unchanged in the content key, so the content key may or may not differ depending on whether `make_content_key` includes `project_id`).
- Currently `make_content_key` does **NOT** include `project_id`, so re-runs produce *identical content keys* and dedupe correctly. This is a happy accident.

If consolidation runs and migration runs *after*:

- Pre-migration: legacy null episodes → DEFAULT_PROJECT_ID facts at lines 401–413. Migration pre-check (line 56–64 of P19-002) sees no NULLs in `semantic_facts` (because we've already filled them with DEFAULT_PROJECT_ID). Migration succeeds.
- Post-migration: those facts now have `project_id = DEFAULT_PROJECT_ID, project_scope = 'project'` — they no longer surface as "global unallocated legacy data" the way they would if NULL were preserved. **Data distortion.**

### 4.3 `prune_stale_facts`

Documented as idempotent (mode "archive" is metadata-only). No project-aware filtering: it prunes globally without checking `project_id`. After NOT NULL applies, this is acceptable (every fact has a project_id), but the prune could affect one project while leaving another untouched. Acceptable for v1 but should be project-aware once multi-project lifecycles are exercised.

---

## 5. Fallback Behaviour — Legacy NULL-PID Episodes

The system has TWO conflicting fallback policies (F-04 + F-06):

| Layer | Behaviour for NULL `project_id` |
|---|---|
| Migration `p19_002_project_id_not_null.py` | **ABORT** upgrade (raise RuntimeError) |
| `consolidate_episodes_to_facts` | **SILENTLY REWRITE** to `DEFAULT_PROJECT_ID` |
| `Episodes.project_id` ORM column | Accepts NULL (per `nullable=True` declaration) |
| `SemanticFacts.project_id` ORM column | Accepts NULL (per `nullable=True` declaration + "NULL = global" comment) |

These cannot coexist. The migration assumes "every row has been explicitly placed" while consolidation assumes "NULLs are fill-in-the-blank for the default project". Whoever runs first wins and the other's invariant is broken.

**Recommendation:** Pick one of:

A. **Treat NULL as legacy-only.** Both ORM and consolidation must skip/reject NULL pre-migration; consolidation emits audit events pointing to a backfill workflow.
B. **Treat DEFAULT_PROJECT_ID as the canonical default.** Migration does not abort on rows without a project_id — instead it backfills DEFAULT_PROJECT_ID for them. The P19-002 pre-check needs to be removed or relaxed.
C. **Don't backfill at all.** Every new write is annotated by caller code; migration runs only on truly-empty tables.

Lane B's stated intent matches **(A)** based on the migration pre-check semantics, but consolidation implements **(B)**. This is a logical contradiction.

---

## 6. P19 Namespace Contract Compliance

The P19 namespace contract, as the migration docstring states, is:

> "Project namespace UUID. NULL = global-scope entity visible from all projects." (`SemanticFacts`, line 268)

After the migration, NULL is no longer permitted for project-scoped tables. So the contract is: "rows have a project_id; project_scope='global' rows are visible cross-project; project_scope='project' rows are isolated." (This is consistent with the registry's `_DEFAULT_PROJECT_ID` being seeded with `project_scope='global'`, line 185 of registry.py.)

Compliance check:

| Requirement | Status |
|---|---|
| Every new episode must carry project_id | **FAILS** at API boundary (F-02) |
| Every new semantic fact carries source episode's project_id | **FAILS** for legacy episodes (F-04 silently writes DEFAULT_PROJECT_ID) |
| Project_id defaults to a real, named project (not sentinel) | **HOLDS** — `_DEFAULT_PROJECT_ID` is a real UUID with project_scope='global' |
| Default project can never be archived | **HOLDS** — registry.archive() rejects (line 350–351) |
| Default project is seeded automatically | **HOLDS** — `_ensure_default_seeded` (line 173) on first op |
| Project-filtered queries are fast | **FAILS** — no index on `project_id` (F-10) |

---

## 7. Pragmatic Risks

### 7.1 Reserved sentinel UUID (F-08 — LOW)

`_DEFAULT_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")` falls in the UUID v1 to v4 reserved range. The nil-UUID is `00000000-0000-0000-0000-000000000000`; the chosen sentinel is adjacent. A genuinely random `uuid.uuid4()` collision is astronomically unlikely, but the choice of v4-format reserved positions is folklore-laden:

- 0x0...: nil
- 0xF...: future reserved

The current sentinel sits in an unreserved but visually-confusing position. **Recommendation:** Pick a deterministic v5 UUID derived from a project namespace (e.g., `uuid.uuid5(uuid.NAMESPACE_DNS, "guinevere.default")`) instead of an arbitrary literal.

### 7.2 `AuditTrail.chain_version` comment drift (F-09 — LOW)

`AuditTrail.chain_version = SmallInteger(..., comment="...: 2=P19+ (project_id in payload)")` (line 1109). The comment is aspirational; there is no trigger or write path that explicitly includes `project_id` in payload. New audit rows for v2 are not actually verifiable at write time.

---

## 8. Remediation Roadmap (Recommended Order)

| Phase | Fix | Files |
|---|---|---|
| 1 | Make ORM `nullable=False` for `Episodes.project_id` and `SemanticFacts.project_id`; remove `Optional[...]` type hints on these cols. | `src/memory/models.py` |
| 2 | Tighten write_pipeline signatures: require `project_id: uuid.UUID` (no None default); add a precondition guard. | `src/memory/write_pipeline.py` |
| 3 | Remove silent NULL→DEFAULT fallback in consolidation; replace with explicit skip + structured audit event. | `src/memory/consolidation.py` |
| 4 | Add `ix_semantic_facts_project_id` and `ix_episodes_project_id` indexes; composite `(project_id, project_scope)` recommended. | `src/memory/models.py` + new migration |
| 5 | Add `content_hash` column to `SemanticFacts` with unique composite on `(content_hash, project_id)`; switch `_fact_exists_by_key` to indexed lookup. | `src/memory/models.py`, `src/memory/consolidation.py`, new migration |
| 6 | Consider replacing `_DEFAULT_PROJECT_ID` literal with `uuid.uuid5(NAMESPACE_DNS, "guinevere.default")` for deterministic-but-non-v4-collision semantics. | `src/projects/registry.py` |

---

## 9. Severity Cross-Reference Table

| ID | Title | Severity | Dimension(s) |
|----|-------|----------|--------------|
| F-01 | ORM nullable mismatch with NOT NULL migration | **CRITICAL** | Schema correctness |
| F-02 | `store_episode`/`store_episode_batch` accept None project_id | **CRITICAL** | Schema correctness, project isolation |
| F-03 | ORM "NULL = global" comment contradicts post-migration reality | HIGH | P19 compliance |
| F-04 | Consolidation silently rewrites NULL→DEFAULT_PROJECT_ID | HIGH | Project isolation, fallback |
| F-05 | `_fact_exists_by_key` is O(N²) full-scan | MEDIUM | Idempotency, performance |
| F-06 | Migration aborts on NULL but consolidation mutes NULL→DEFAULT — contradictory policies | HIGH | Fallback, idempotency |
| F-07 | `store_episode_batch` can emit `(scope='project', project_id=None)` tuples | HIGH | Project isolation |
| F-08 | `_DEFAULT_PROJECT_ID` uses UUID-v4-form sentinel literal | LOW | Pragmatic risk |
| F-09 | `AuditTrail.chain_version` comment drift | LOW | P19 compliance |
| F-10 | No index on `Episodes.project_id` / `SemanticFacts.project_id` | MEDIUM | Project isolation (perf), schema correctness |

---

## 10. Verdict

Lane B **does not yet satisfy the P19 namespace contract on the application layer**. The migration is well-formed (with explicit pre-check and idempotent upgrade/downgrade), the registry is well-designed (lazy default seeding, archival protection, audit emission), and the consolidation flow demonstrates P19 awareness. However:

- The ORM schema still permits NULL on the very columns the migration will mark NOT NULL.
- The write path silently permits NULL `project_id`, breaking the very contract Lane B is trying to enforce.
- Consolidation's NULL→DEFAULT fallback contradicts the migration's treatment of NULL.

The fix is two-sided: push enforcement down into the API (write pipeline, ORM) and remove implicit silent rewrites (consolidation fallback). Once these are addressed and proper indexes are added, the architecture will satisfy P19.

**Audit sign-off:** Ready for round 2 once remediation Phase 1–2 are applied. Phases 3–6 are recommended for hardening but not blocking the core fix.
