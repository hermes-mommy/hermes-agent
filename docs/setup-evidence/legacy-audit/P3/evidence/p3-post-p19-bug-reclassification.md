# P3 Post-P19 Bug Reclassification

**Date:** 2026-06-27
**Agent:** Read-only (parent, Opus 4.8)
**Basis:** Live VPS SSH data + P19-012 production deploy report + original P3 bug register (67 bugs)
**Read-only affirmation:** YES. No source changes. No DB writes. No deploy.

---

## Classification Legend

| Tag | Meaning |
|---|---|
| STILL_VALID_LIVE | Bug exists in current source AND is observable/triggerable on live DB post-P19 |
| SUPERSEDED_BY_P19_DEPLOY | Bug was real pre-P19 but P19 deploy fixed or eliminated it |
| PARTIALLY_CHANGED_BY_P19 | Bug still exists but its scope/impact/severity changed after P19 deploy |
| HISTORICAL_ONLY | Bug was a pre-P19 snapshot finding; no longer current |
| NEEDS_SOURCE_FIX_APPROVAL | Bug confirmed live, requires source fix (mama approval needed) |
| FALSE_POSITIVE | Bug was wrong when originally filed |
| UNKNOWN_NEEDS_MORE_READONLY_PROOF | Cannot classify without additional read-only verification |

---

## Reclassification Table

### CRITICAL Bugs (6)

| ID | Title | Old Status | Post-P19 Classification | Evidence |
|---|---|---|---|---|
| BUG-001 | `verify_recall_results_dnr_free()` never called | CONFIRMED_CURRENT_SOURCE | **STILL_VALID_LIVE** | VPS source unchanged. Zero call sites. 0 DNR episodes means dormant. Not affected by P19. |
| BUG-002 | Consolidation scheduler commented out | CONFIRMED_LIVE_DB | **STILL_VALID_LIVE — severity ESCALATED** | Scheduler still commented out. **NEW blocker:** `semantic_facts.project_id` is now NOT NULL (P19). If consolidation is enabled without fixing BUG-008, it will crash with NOT NULL violation. |
| BUG-003 | `store_episode_batch` loses project_id | SUPERSEDED (P19 not deployed) | **STILL_VALID_LIVE — NEEDS_SOURCE_FIX_APPROVAL** | P19 deployed. project_id columns exist on episodes. `store_episode_batch` still doesn't forward project_id. Now a live bug, not a P19 readiness issue. |
| BUG-004 | SemanticFacts/KG ORM lack project_id | SUPERSEDED (P19 not deployed) | **PARTIALLY_CHANGED_BY_P19 — NEEDS_SOURCE_FIX_APPROVAL** | P19 added `project_id` to semantic_facts (NOT NULL), kg_entities (NOT NULL), kg_edges (nullable). ORM models need updating to match. KnowledgeGraph ORM still maps to non-existent table. |
| BUG-005 | Four btree DESC indexes missing | REFUTED_BY_LIVE_DB | **FALSE_POSITIVE** | All 4 indexes confirmed on live DB (pre-P19 AND post-P19). TimescaleDB created them. Remove from register. |
| BUG-006 | DNR result dicts lack `do_not_recall` key | CONFIRMED_CURRENT_SOURCE | **STILL_VALID_LIVE** | VPS source unchanged. compute_scored_results still builds dicts without do_not_recall key. Dormant (0 DNR episodes). |

### HIGH Bugs (12)

| ID | Title | Old Status | Post-P19 Classification | Evidence |
|---|---|---|---|---|
| BUG-007 | safe_mode never reaches life-kernel recall during HARD STOP | CONFIRMED_CURRENT_SOURCE | **STILL_VALID_LIVE** | VPS source unchanged. observe_node still recalls before decide_node detects HARD STOP. Not affected by P19. |
| BUG-008 | Consolidation has zero project_id awareness | SUPERSEDED (P19 not deployed) | **STILL_VALID_LIVE — severity ESCALATED to CRITICAL** | P19 deployed. `semantic_facts.project_id` is NOT NULL. `consolidate_episodes_to_facts()` has no project_id parameter. Enabling consolidation without fixing this will crash. **This is now a CRITICAL blocker for consolidation scheduler activation.** |
| BUG-009 | SessionSummary missing ClassificationMetaMixin columns | CONFIRMED_LIVE_DB | **PARTIALLY_CHANGED_BY_P19** | session_summaries now has 8 columns (was 7). P19 added `project_id NOT NULL`. But still missing 11 ClassificationMetaMixin columns (classification, purpose, source, retention_class, retention_until, access_policy, encryption_profile, deletion_state, key_id, key_version, updated_at). ORM INSERT would still fail. |
| BUG-010 | 19+ columns in DB not in ORM | PARTIALLY_REFUTED | **PARTIALLY_CHANGED_BY_P19** | P19 columns now exist on live DB (were refuted pre-P19). ORM models need to match. KnowledgeGraph ORM still stale. 15 base tables + 3 views in memory schema vs 9 ORM classes. |
| BUG-011 | HermesMemoryBridge embedding_service=None | CONFIRMED_LIVE_DB | **STILL_VALID_LIVE** | 3/3 episodes still have NULL embedding. P19 did not address this. |
| BUG-012 | Batch write lacks transaction atomicity | CONFIRMED_CURRENT_SOURCE | **STILL_VALID_LIVE** | VPS source unchanged. store_episode_batch still iterates with individual session.add()+flush(). Dormant (never called in production). |
| BUG-013 | Query embedding dim not validated | CONFIRMED_CURRENT_SOURCE | **STILL_VALID_LIVE** | VPS source unchanged. Life-kernel recall still omits embedding_service (defaults to None). Dormant. |
| BUG-014 | No classification validation on write | CONFIRMED_CURRENT_SOURCE | **STILL_VALID_LIVE** | VPS source unchanged. All 3 episodes have valid classification. Dormant. |
| BUG-015 | Broad except on embedding fallback | CONFIRMED_CURRENT_SOURCE | **STILL_VALID_LIVE** | VPS source unchanged. Life-kernel recall still omits embedding_service. Dormant. |
| BUG-016 | P3-007 benchmark 20 rows | DOC_STALE_ONLY | **HISTORICAL_ONLY** | HNSW indexes exist. 0 embeddings. Benchmark doc is a static snapshot. Not affected by P19. |
| BUG-017 | All 235 tests use FakeSession | CONFIRMED_CURRENT_SOURCE | **STILL_VALID_LIVE** | VPS source unchanged. Not affected by P19. |
| BUG-018 | KG facts leak across projects | SUPERSEDED (P19 not deployed) | **PARTIALLY_CHANGED_BY_P19 — NEEDS_SOURCE_FIX_APPROVAL** | P19 deployed. project_id on kg_entities (NOT NULL) and kg_edges (nullable). Cross-project leak structurally addressable now. But consolidation doesn't populate project_id on facts (BUG-008). |

### MEDIUM Bugs (14)

| ID | Title | Post-P19 Classification | Notes |
|---|---|---|---|
| BUG-019 | _fact_exists_by_key O(n) scan | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-020 | ContextCompactor sensitive content in summaries | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-021 | Dual token budget inconsistent | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-022 | DNR tag stringified list | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-023 | Token budget chars/4 rough | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-024 | P19 project_id filter may bypass HNSW | **STILL_VALID_LIVE — NOW LIVE** | P19 deployed. project_id composite btree indexes created. HNSW index exists separately. Planner behavior with project_id filter never benchmarked. |
| BUG-025 | No ef_search configuration | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-026 | Consolidation never runs / semantic_facts empty | **PARTIALLY_CHANGED_BY_P19** | semantic_facts has 6 rows (manual run). Consolidation still not automated. But now that project_id is NOT NULL on semantic_facts, enabling consolidation requires BUG-008 fix first. |
| BUG-027 | life-kernel recall degraded parameter surface | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-028 | consolidation.py exception coverage gap | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-029 | Merge migration header misleading | **HISTORICAL_ONLY** | Migration chain is now fully deployed. Header comment is cosmetic. |
| BUG-030 | audit_journal table outside migration system | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-031 | surveillance.events chunk interval 1d vs 7d | **STILL_VALID_LIVE** | Not affected by P19. |
| BUG-032 | gamification schema excluded from autogenerate | **STILL_VALID_LIVE** | Not affected by P19. |

### LOW Bugs (23)

| ID | Title | Post-P19 Classification | Notes |
|---|---|---|---|
| BUG-033 | AsyncClient per request | STILL_VALID_LIVE | Unchanged |
| BUG-034 | 8 tables without ClassificationMetaMixin | STILL_VALID_LIVE | Unchanged |
| BUG-035 | Discord /memory-search safe_mode=False | STILL_VALID_LIVE | Unchanged |
| BUG-036 | Logging discipline by convention | STILL_VALID_LIVE | Unchanged |
| BUG-037 | compaction substring matching | STILL_VALID_LIVE | Unchanged |
| BUG-038 | No DNR remediation path | STILL_VALID_LIVE | Unchanged |
| BUG-039 | verify_recall can't guard SQLite results | STILL_VALID_LIVE | Unchanged |
| BUG-040 | safe_mode inconsistent across paths | STILL_VALID_LIVE | Unchanged |
| BUG-041 | TierManager not integrated | STILL_VALID_LIVE | Unchanged |
| BUG-042 | ContextCompactor integration unclear | STILL_VALID_LIVE | Unchanged |
| BUG-043 | store_episode hard-codes do_not_recall=False | STILL_VALID_LIVE | Unchanged |
| BUG-044 | Write silently skips embedding | STILL_VALID_LIVE | Unchanged |
| BUG-045 | KG signal default with silent fallback | STILL_VALID_LIVE | Unchanged |
| BUG-046 | No dimension validation on write | STILL_VALID_LIVE | Unchanged |
| BUG-047 | Recency query no relevance signal | STILL_VALID_LIVE | Unchanged |
| BUG-048 | P3-004 UTF-16 BOM | HISTORICAL_ONLY | Static evidence file |
| BUG-049 | P3-016-019 missing verification.md | HISTORICAL_ONLY | Static evidence |
| BUG-050 | sentence-transformers dead weight | STILL_VALID_LIVE | Unchanged |
| BUG-051 | MiniLM cached but useless | STILL_VALID_LIVE | Unchanged |
| BUG-052 | No EXPLAIN regression tests | STILL_VALID_LIVE | Unchanged |
| BUG-053 | procedural_skills IVFFlat not HNSW | STILL_VALID_LIVE | Unchanged |
| BUG-054 | No caller identity gate | STILL_VALID_LIVE | Unchanged |
| BUG-055 | Consolidation watermark no project filter | **STILL_VALID_LIVE — severity ESCALATED** | Now that project_id is NOT NULL on semantic_facts, watermark without project filter will produce cross-project mixing OR crash. |

### COSMETIC Bugs (12)

| ID | Title | Post-P19 Classification | Notes |
|---|---|---|---|
| BUG-056 | models.py says 47 tables, actual 48 | STILL_VALID_LIVE | Unchanged |
| BUG-057 | consolidation.py misleading comment | STILL_VALID_LIVE | Unchanged |
| BUG-058 | Hardcoded DEFAULT_BASE_URL | STILL_VALID_LIVE | Unchanged |
| BUG-059 | FaizProfile LargeBinary | STILL_VALID_LIVE | Unchanged |
| BUG-060 | HNSW created twice in migration | HISTORICAL_ONLY | Migration deployed |
| BUG-061 | P3-001 FAIL-to-PASS undocumented | HISTORICAL_ONLY | Static evidence |
| BUG-062 | Token budget log recomputes | STILL_VALID_LIVE | Unchanged |
| BUG-063 | CHECKLIST sections unchecked | HISTORICAL_ONLY | Static evidence |
| BUG-064 | D01/D11 stale FAIL reference | HISTORICAL_ONLY | Static evidence |
| BUG-065 | P19 research stale snapshot | **SUPERSEDED_BY_P19_DEPLOY** | P19 now deployed. Research claim "zero project_id" is moot. |
| BUG-066 | No pgvector/TimescaleDB version docs | STILL_VALID_LIVE | Unchanged |
| BUG-067 | P3-003 memory table count stale | HISTORICAL_ONLY | Static evidence |

---

## Summary

| Classification | Count |
|---|---|
| STILL_VALID_LIVE | 41 |
| STILL_VALID_LIVE (severity escalated) | 3 (BUG-002, BUG-008, BUG-055) |
| PARTIALLY_CHANGED_BY_P19 | 4 (BUG-004, BUG-009, BUG-010, BUG-018) |
| SUPERSEDED_BY_P19_DEPLOY | 2 (BUG-065, plus BUG-005 was already FALSE_POSITIVE) |
| FALSE_POSITIVE | 1 (BUG-005) |
| HISTORICAL_ONLY | 10 (BUG-016, BUG-029, BUG-048, BUG-049, BUG-060, BUG-061, BUG-063, BUG-064, BUG-067) |
| NEEDS_SOURCE_FIX_APPROVAL | 4 (BUG-003, BUG-004, BUG-008, BUG-018) |
| **TOTAL** | **67** |

### Severity Changes Post-P19

| Bug | Pre-P19 Severity | Post-P19 Severity | Reason |
|---|---|---|---|
| BUG-008 | HIGH | **CRITICAL** | semantic_facts.project_id is now NOT NULL. Consolidation without project_id will crash. Blocks scheduler activation. |
| BUG-055 | LOW | **MEDIUM** | Same as BUG-008 — watermark without project filter now causes crash, not just mixing. |

### P19 Deploy Impact on P3 Findings

| Category | Count | Impact |
|---|---|---|
| Bugs unaffected by P19 | 43 | Status quo |
| Bugs escalated by P19 | 2 | BUG-008, BUG-055 — consolidation now crashes without project_id |
| Bugs partially changed by P19 | 4 | BUG-004, BUG-009, BUG-010, BUG-018 — scope/impact changed |
| Bugs superseded by P19 | 2 | BUG-065 (stale research), BUG-005 (already false positive) |
| Bugs now live (were dormant) | 4 | BUG-003, BUG-024, BUG-008, BUG-055 |
| Bugs now blockers for scheduler | 2 | BUG-002 (scheduler not wired), BUG-008 (consolidation crashes) |

---

## Explicit Affirmation

No source code modified. No DB writes. No migration. No deploy. No restart. No secrets printed. Classification based on live VPS SSH data + P19-012 production report + original P3 bug register.

**Output file:** `docs/setup-evidence/legacy-audit/P3/evidence/p3-post-p19-bug-reclassification.md`