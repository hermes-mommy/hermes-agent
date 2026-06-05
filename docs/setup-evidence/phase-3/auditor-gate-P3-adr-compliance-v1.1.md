# Auditor Gate — Phase 3 ADR-035 Compliance Audit v1.1

**Auditor**: ADR-035 Compliance Auditor (Independent, Read-Only)
**Date**: 2026-06-05
**Target**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md` v1.1 (726 lines)
**Scope**: Verify batch-plan-phase-3.md faithfully implements ADR-035 Pillar 2, phase-3-memory.md canonical procedure, master batch-plan-migration.md Phase 3 section, and related governance documents.
**Method**: Cross-reference ALL 10 audit criteria against source documents with line-number evidence.

---

## Overall Verdict: **NEEDS REVIEW**

Two findings require resolution before execution. Neither is blocking at the architectural level — both are documentation/specification alignment issues that can be fixed in the planner gate without changing implementation design.

---

## Detailed Findings

### C1: ADR-035 Pillar 2 Compliance — **PASS**

| Check | Evidence | Verdict |
|---|---|---|
| Memory = HYBRID | Batch plan Section 4.1: PostgreSQL is write authority. P3-001 delegates to read_pipeline/write_pipeline unchanged | PASS |
| Hermes READ-ONLY supplement | P3-007: Verify zero PG writes. RBAC: SELECT-only role | PASS |
| Zero PostgreSQL writes from Hermes | P3-007 scaffold: Hard rejection if any write query detected. log_statement=mod configured | PASS |
| Compression at 70% (not 50%) | P3-002: threshold=0.7. ADR-035 line 1473: "70% initially (not 50%)". ADR-035 line 1593: same | PASS |
| Hermes must NEVER write to PG directly | ADR-035 line 1593: "never writes to PostgreSQL". P3-007 enforces this | PASS |

**Evidence**: ADR-035 Pillar 2 (line 240) declares "Memory = HYBRID (PostgreSQL+pgvector primary write authority unchanged; Hermes compression and session_search adopted as read-only supplements)." The batch plan faithfully implements this. The 70% threshold is explicitly confirmed at ADR-035 lines 1473 and 1593 — no 50% conflict exists.

---

### C2: phase-3-memory.md Step Coverage — **NEEDS REVIEW**

phase-3-memory.md specifies 6 canonical steps. The batch plan maps them as follows:

| Canonical Step | Batch Plan Step | Mapping Quality | Notes |
|---|---|---|---|
| 3.1 Compression at 70% | P3-002 | EXACT | Threshold 0.7, protect_last 20 — matches |
| 3.2 session_search FTS5 | P3-003 | EXACT | Session_search enabled with safety gates — matches |
| 3.3 memory_plugin.py (~180 lines) | P3-001 | EXACT | Refactored to MemoryProvider ABC — superset of canonical spec |
| **3.4 Mirror sync MEMORY.md/USER.md** | **NO DEDICATED STEP** | **MISSING** | **See finding below** |
| 3.5 A/B test 100 queries p>0.05 | P3-005 + P3-006 | EXACT | Split into infrastructure + execution — acceptable |
| 3.6 Zero PG writes | P3-007 | EXACT | Verification-focused — matches |

**Finding — Step 3.4 Gap**: The canonical `phase-3-memory.md` Step 3.4 specifies configuring Hermes mirror sync to write critical PostgreSQL facts to `MEMORY.md` and `USER.md` files every 5 messages. The batch plan P3-004 is titled "Configure PostgreSQL Mirror Sync" but implements **database-level streaming replication** (Hot Standby, RBAC roles, RLS policies) — an entirely different operation.

The Hermes-level mirror sync (`memory.mirrors.enabled: true`, `memory.mirrors.memory_md_path`, `memory.mirrors.user_md_path`, `memory.mirrors.sync_interval_messages: 5`) is not assigned to any P3-XXX step. It is referenced only in safety checkpoint P3-T4 ("Mirror sync safe — no classified data in MEMORY.md/USER.md") and in the rollback plan ("Set memory.mirrors.enabled false"), but has no implementation step.

**Impact**: Without configuring Hermes mirror sync, the MEMORY.md and USER.md files that Hermes uses for skill creation and agent self-improvement will not be populated. This undermines ADR-035's Hybrid approach which explicitly includes mirror sync as a Phase 3 deliverable (ADR-035 line 1475: "Mirror sync: critical facts written to MEMORY.md/USER.md (batch every 5 messages)").

**Recommendation**: Either (a) add Hermes mirror sync configuration to P3-004 as a sub-step alongside the DB-level work, or (b) create a dedicated step P3-004b that enables `memory.mirrors.enabled true` and verifies MEMORY.md/USER.md creation. Option (a) is simpler since the RBAC and mirror sync both relate to Hermes-PostgreSQL interaction.

---

### C3: Gate Criteria Alignment — **PASS**

All 5 gates from `phase-3-memory.md` Gate Criteria table are present and verifiable:

| Gate | Canonical Source | Batch Plan Location | Verdict |
|---|---|---|---|
| Recall quality unchanged (p > 0.05) | phase-3-memory.md Gate Criteria row 1 | P3-006 scaffold: Hard Rejection if p < 0.05 | PASS |
| Zero DNR leaks | phase-3-memory.md Gate Criteria row 2 | P3-003: DNR post-recall gate. P3-006: zero DNR violations | PASS |
| Zero Hermes PG writes | phase-3-memory.md Gate Criteria row 3 | P3-007 scaffold: Hard Rejection if any write query detected | PASS |
| Compression at 70% | phase-3-memory.md Gate Criteria row 4 | P3-002: Hard Rejection if threshold != 0.7 | PASS |
| Classification fail-closed | phase-3-memory.md Gate Criteria row 5 | P3-003: Classification enrichment with fail-closed on PG error | PASS |

All gates have concrete, machine-checkable scaffold criteria with explicit hard rejection conditions.

---

### C4: Master Batch Plan Alignment — **PASS**

Comparison of `batch-plan-phase-3.md` against `batch-plan-migration.md` Phase 3 section (lines 997-1126):

| Dimension | Master Plan (lines 997-1126) | Phase 3 Plan | Match |
|---|---|---|---|
| Duration | 4-5 days | 4-5 days (header) | YES |
| Risk Level | MEDIUM | MEDIUM (header) | YES |
| Downtime | ~10s config reload | ~10s config reload (Caveat 6) | YES |
| Rollback time | < 3 minutes | Per-scenario all < 3 min except full (< 10 min) | YES |
| Safety checkpoints P3-T1..T4 | All 4 listed in master plan | All 4 present in Safety Checkpoint section | YES |
| Gate criteria | Recall quality, DNR, PG writes, compression, classification | All present in per-step scaffolds | YES |
| Step count | 6 canonical (3.1-3.6) | 8 atomic (P3-001..P3-008) — more granular, same scope | YES |
| Step numbering | 3.1-3.6 | P3-001..P3-008 | Different scheme, same content |

The batch plan splits Step 3.3 (build plugin) into P3-001 (refactor) + P3-005 (A/B infrastructure) and adds P3-008 (final verification gate). This is acceptable decomposition — the total scope is preserved.

---

### C5: 7 Source Files Preservation (ADR-007) — **PASS**

**Question**: Does the plan modify ANY of these 7 files?

| File | In MODIFY List? | In READ-ONLY List? | Status |
|---|---|---|---|
| src/memory/read_pipeline.py | NO | YES (Section 7.3) | Preserved |
| src/memory/write_pipeline.py | NO | YES (Section 7.3) | Preserved |
| src/memory/embeddings.py | NO | YES (Section 7.3) | Preserved |
| src/memory/dnr.py | NO | YES (Section 7.3) | Preserved |
| src/memory/consolidation.py | NO | NOT LISTED | De facto preserved |
| src/memory/mood_classifier.py | NO | NOT LISTED | De facto preserved |
| src/memory/__init__.py | NO | NOT LISTED | De facto preserved |

**Answer**: NO — none of the 7 files are modified. None appear in the batch plan Section 7.2 "Files to MODIFY" table. All 7 files are preserved verbatim as required by ADR-007.

**Note**: Only 4 of 7 files are explicitly listed in Section 7.3 "Read-Only References." The remaining 3 (consolidation.py, mood_classifier.py, __init__.py) are de facto preserved since no step modifies them. The `phase-3-memory.md` canonical document lists its own set of preserved files (including `models.py` instead of `mood_classifier.py`). Recommendation: Align the read-only list in Section 7.3 to include all files mandated by ADR-007 for completeness.

---

### C6: Gap Resolution Coverage — **NEEDS REVIEW**

The batch plan claims to address 7 of 16 gaps from `07-MEMORY-BRIDGE-GAP.md`:

| Gap | Severity | Plan Assignment | Gap Doc Phase Assignment | Match? |
|---|---|---|---|---|
| G-B1 | CRITICAL | Pre-requisite (fix 9Router config) | Phase 1 | YES (pre-req acceptable) |
| G-B2 | HIGH | Pre-requisite (circuit breaker) | Phase 1 | YES (pre-req acceptable) |
| G-B3 | HIGH | P3-001 (sync_turn daemon) | Phase 1 | **MISMATCH** |
| G-B6 | MEDIUM | P3-001 (plugin lifecycle hook) | Phase 2 | **MISMATCH** |
| G-B7 | MEDIUM | P3-001 (safety delegation) | Phase 1 | **MISMATCH** |
| G-B9 | MEDIUM | P3-001 (dynamic classification) | Phase 2 | **MISMATCH** |
| G-B10 | LOW | P3-002 (compression engine) | Phase 2 | **MISMATCH** |

**Finding**: The `07-MEMORY-BRIDGE-GAP.md` Section 5 "Recommendation: Option C with Phased Rollout" assigns Phase 1 to fix critical gaps (G-B1, G-B2, G-B3, G-B7) and Phase 2 to bridge improvements (G-B5, G-B6, G-B8, G-B9, G-B10). But the batch plan assigns G-B3 (auto-store fails silently), G-B6 (mood hardcoded), G-B7 (hard_stop_handler not wired), and G-B9 (classification hardcoded) to Phase 3, not Phase 1 or Phase 2.

**Impact**: G-B3 and G-B7 are CRITICAL/HIGH severity operational gaps that the gap document recommends fixing in Phase 1 (immediate). Deferring them to Phase 3 creates risk of silent conversation loss (G-B3) and incomplete HARD STOP handling (G-B7) during Phases 1-2. However, since Phase 1 and Phase 2 may have already addressed these in their own implementations, this may not be a real conflict — it depends on execution state.

**Gaps NOT addressed in Phase 3** (correctly deferred):
- G-B4: No bridge abstraction (addressed by P3-001 — the plugin itself)
- G-B5: Double session creation (not in Phase 3 — Phase 2 concern)
- G-B8: Importance hardcoded (not in Phase 3)
- G-B11: No total context window management (not in Phase 3)
- G-B12: Double token budget pass (not in Phase 3)
- G-B13: No cross-episode dedup (not in Phase 3)
- G-B14: Memory format wastes tokens (not in Phase 3)
- G-B15: EmbeddingService not centralized (not in Phase 3)
- G-B16: No consent check on auto-store (addressed by P3-001 consent gate)

**Recommendation**: Verify whether G-B3 and G-B7 were already resolved in Phase 1 execution. If so, note this in the plan. If not, consider whether these gaps can remain open until Phase 3 or should be addressed earlier. The plan should explicitly state the rationale for the phase reassignment.

---

### C7: Safety Checkpoint Coverage — **PASS**

All 4 safety checkpoints from `phase-3-memory.md` Safety Checkpoint table are present:

| Checkpoint | Source | Batch Plan Location | Verdict |
|---|---|---|---|
| P3-T1: A/B recall quality unchanged | phase-3-memory.md row 1 | Safety Checkpoint section: P3-T1 | PASS |
| P3-T2: Zero DNR in Hermes recall | phase-3-memory.md row 2 | Safety Checkpoint section: P3-T2 | PASS |
| P3-T3: Zero PG modifications from Hermes | phase-3-memory.md row 3 | Safety Checkpoint section: P3-T3 | PASS |
| P3-T4: Mirror sync safe | phase-3-memory.md row 4 | Safety Checkpoint section: P3-T4 | PASS |

Each checkpoint maps to a specific verification command or scaffold criterion. All 4 are machine-verifiable.

---

### C8: ADR-Index Consistency — **PASS**

| Check | Evidence | Verdict |
|---|---|---|
| Plan references correct ADR number | "ADR Reference: ADR-035-hermes-migration.md" in header | PASS |
| ADR-Index has ADR-035 registered | ADR Index line: "Hermes NousResearch hybrid migration architecture | ADR-035 | Accepted | CRITICAL" | PASS |
| P3-008 includes ADR-Index update | P3-008 Section 7.2: "docs/10-governance/17-ADR_Index_v1.0.md — Add Phase 3 completion reference" | PASS |
| File path in plan matches actual | Plan references `docs/10-governance/17-ADR_Index_v1.0.md` — file exists at that path | PASS |

---

### C9: Rollback Alignment — **PASS**

| Scenario | phase-3-memory.md | Batch Plan | Match |
|---|---|---|---|
| Compression rollback | `hermes config set memory.compression.enabled false` | Same command, plus `hermes gateway restart` | YES |
| Session_search rollback | `hermes config set memory.session_search.enabled false` | Same command | YES |
| Mirror rollback | `hermes config set memory.mirrors.enabled false` | Same command (in rollback section) | YES |
| Plugin refactor rollback | `git checkout -- src/hermes/memory_bridge.py` | Same command | YES |
| Full rollback | All 3 features disabled + git checkout | All features disabled + restore skip_memory=True | YES |
| Target time | < 3 minutes | Per-scenario: P3-002 <1min, P3-003 <1min, P3-004 <3min, P3-007 <3min | YES |

All rollback triggers from the master plan are present. The batch plan adds per-step granularity (individual step rollbacks) without contradicting the canonical procedure.

---

### C10: Duration and Risk Alignment — **PASS**

| Dimension | Master Plan | Batch Plan | Match |
|---|---|---|---|
| Duration | 4-5 days | 4-5 days (header) | YES |
| Risk Level | MEDIUM | MEDIUM (header) | YES |
| Downtime | ~10s config reload | ~10s config reload (referenced) | YES |
| Step sum | — | 1d + 0.5d + 0.5d + 1d + 1d + 0.5d + 0.5d + 0.5d = 5.5d sequential | YES (parallel waves reduce to 4-5d) |

The per-step duration estimates sum to 5.5 days if run sequentially, but the plan correctly uses parallel execution waves (Wave 1: P3-001 + P3-004 + P3-005 in parallel) to fit within the 4-5 day estimate. This is sound scheduling.

---

## Findings Summary

| Criterion | Verdict | Severity |
|---|---|---|
| C1: ADR-035 Pillar Compliance | PASS | — |
| **C2: Step Coverage** | **NEEDS REVIEW** | **MEDIUM** |
| C3: Gate Criteria Alignment | PASS | — |
| C4: Master Plan Alignment | PASS | — |
| C5: File Preservation (ADR-007) | PASS (with note) | — |
| **C6: Gap Resolution Coverage** | **NEEDS REVIEW** | **LOW** |
| C7: Safety Checkpoint Coverage | PASS | — |
| C8: ADR-Index Consistency | PASS | — |
| C9: Rollback Alignment | PASS | — |
| C10: Duration and Risk Alignment | PASS | — |

---

## Required Fixes (Before Wave 1 Execution)

### Fix 1: Add Mirror Sync Implementation Step (C2)

**Problem**: Phase-3-memory.md Step 3.4 (Hermes mirror sync to MEMORY.md/USER.md) has no implementation step in the batch plan.

**Fix**: Add Hermes mirror sync configuration to P3-004 as a sub-step, or create a dedicated step. The configuration block from phase-3-memory.md is already defined:
- `memory.mirrors.enabled: true`
- `memory.mirrors.sync_interval_messages: 5`
- `memory.mirrors.memory_md_path` and `user_md_path`

Add verification to P3-004 scaffold: files created, no classified data in plaintext mirror, sync interval verified.

**Effort**: Quick (<1h) — planner gate edit only.

### Fix 2: Document Gap Phase Reassignment Rationale (C6)

**Problem**: G-B3 and G-B7 are assigned to Phase 1 in the gap analysis document but to Phase 3 in the batch plan. The rationale for this reassignment is not documented.

**Fix**: Add a note to Section 4.2 (Critical Gaps) stating: "G-B3 and G-B7 are assigned to Phase 3 (not Phase 1 as recommended by the gap analysis) because [reason]. If these were not resolved in Phase 1, add them to the Phase 3 pre-flight checklist."

**Effort**: Quick (<1h) — documentation edit only.

---

## What Is Working Well

The v1.1 plan shows significant improvement over v1.0:
1. **Safety architecture is robust**: Consent gate in P3-001, DNR ID cache in P3-003, RLS policies in P3-004, and classification enrichment are all well-specified with fail-closed patterns.
2. **Collision scan resolved**: Moving safety gates to a separate `safety_gates.py` module properly addresses the Wave 2 collision between P3-002 and P3-003.
3. **Scaffold quality is high**: All 8 per-step verification scaffolds are machine-checkable with concrete commands, forbidden patterns, and hard rejection criteria.
4. **Binding decisions are well-documented**: Each architectural choice (Hermes MemoryProvider ABC, streaming replication, scipy for A/B testing) has a clear rationale and rejected alternative.
5. **Rollback is comprehensive**: Per-step rollback with time estimates covers all failure scenarios.

---

## Footer

| Field | Value |
|---|---|
| Auditor | ADR-035 Compliance Auditor (Independent, Read-Only) |
| Report Path | docs/setup-evidence/phase-3/auditor-gate-P3-adr-compliance-v1.1.md |
| Date | 2026-06-05 |
| Sources Read | batch-plan-phase-3.md (726 lines), ADR-035-hermes-migration.md (2514 lines), phase-3-memory.md (487 lines), batch-plan-migration.md (lines 997-1126), 07-MEMORY-BRIDGE-GAP.md (full), 17-ADR_Index_v1.0.md (full) |
| Criteria Checked | C1 through C10 (10/10) |
| Verdict | NEEDS REVIEW — 2 findings (1 MEDIUM, 1 LOW) |
| Re-audit Required | YES — after fixes applied |