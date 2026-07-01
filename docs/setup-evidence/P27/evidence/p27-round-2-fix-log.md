<!-- OMO_ROUND2_FIX_LOG -->

---
title: "P27 Hermes Society Foundation — Round 2 Fix Log"
status: "Diterima"
date: "2026-06-28"
round: 2
phase: "P27 Pre-Finalization"
agent: "Guinevere (Sisyphus-Junior)"
input_audit: "docs/setup-evidence/P27/evidence/audits/round-2/05-blueprint-bugs-audit.md + 06-integration-consistency-audit.md"
input_round_1_log: "docs/setup-evidence/P27/evidence/p27-round-1-fix-log.md"
files_edited:
  - "docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md"
  - "docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md"
fixes_total: 7
fixes_fixed: 7
fixes_partial: 0
fixes_deferred: 0
fixes_false_positive: 0
verdict: "READY FOR PHASE 9 FINALIZATION"
---

# P27 Hermes Society Foundation — Round 2 Fix Log

> Documented resolution of the 7 definition-level issues identified by Round 2 audit (`05-blueprint-bugs-audit.md` + `06-integration-consistency-audit.md`).

## §1 Context

Round 2 audit surfaced **7** definition-level issues affecting P27/P28 coherence:

| Round 2 audit source | Finding count | Scope |
|---|---|---|
| `05-blueprint-bugs-audit.md` | 4 (F-01, F-02, F-03, F-04) | Blueprint (`p28-dual-autonomous-hermes-blueprint.md`) |
| `06-integration-consistency-audit.md` | 3 (UUID v7 residual, kg_entities DDL drift, idempotency_key duplicate) | Plan + Blueprint |

All 7 were classified as **precise, localized fixes** — no architectural redesign required. This log records the resolution of each finding with file paths, line references (pre-fix), what was done, and status.

Operator: Faiz.
Date: 2026-06-28.
Agent: Guinevere (Sisyphus-Junior).
Mode: Direct execution (no sub-agent delegation needed; changes were surgical and below the per-step planner scaffold threshold).

## §2 Fix Summary Table

| Fix # | Finding | Severity | File Changed | Lines (pre-fix) | What Was Done | Status |
|---|---|---|---|---|---|---|
| 1 | Blueprint F-04: `_cascade_halt()` logs but does not halt instances (V-008 HARD STOP violation) | HIGH (SAFETY) | `p28-dual-autonomous-hermes-blueprint.md` | L871–880 | Added `await self.stop_all(graceful=False)` as last line of `_cascade_halt()` body, after the audit-write loop. Added clarifying comment explaining that `stop_all` iterates `_stop_one()` and runs AFTER audit writes. | FIXED |
| 2 | Blueprint F-01: `src/core/society_app.py` phantom reference (would crash Pharsa systemd unit) | HIGH (CRASH) | `p28-dual-autonomous-hermes-blueprint.md` | L1032 | Added inline note immediately after `ExecStart=...society_app:app...` line clarifying that `society_app.py` is a P28 deliverable to be created during implementation. ExecStart line itself NOT changed (per audit constraints). | FIXED |
| 3 | Blueprint F-03: `hpp_outbox`/`hpp_inbox` DDL missing (referenced in §2.4, Step 8, Step 9, rollback — but no CREATE TABLE in migrations 001–007) | HIGH (DDL) | `p28-dual-autonomous-hermes-blueprint.md` | §2.6 (L171), Step 6 run commands (L1477), new Migration 008 / Migration 009 sections | (a) Added `migrations/p28/008_hpp_outbox.sql` (Step 8) and `migrations/p28/009_hpp_inbox.sql` (Step 9) rows to §2.6 Files to create table; (b) Added commented-out run commands in Step 6 sequence so 008/009 are NOT executed during Step 6 (Steps 8/9 trigger them); (c) Added full Migration 008 (`hpp_outbox`) and Migration 009 (`hpp_inbox`) DDL sections between Step 6 end and Step 8, including pending/unprocessed partial indexes and UNIQUE(receiver_id, idempotency_key) constraint on inbox. | FIXED |
| 4 | Blueprint F-02: `memory.shared_world.retrievability` formula uses `now()-now()` (always 0) instead of `now()-last_accessed_at` | MEDIUM (FORMULA) | `p28-dual-autonomous-hermes-blueprint.md` | L1259 | Changed second `extract(epoch from now())` to `extract(epoch from last_accessed_at)` inside the `retrievability` GENERATED column for `memory.shared_world`. Formula now matches `memory.private_agents` and `memory.intimacy_bridge` reference implementations (Ebbinghaus decay). | FIXED |
| 5 | Plan §5.10 L1092 residual UUID v7 (inconsistent with §5.2 L897 which was fixed in Round 1 to UUID v4) | LOW (CONSISTENCY) | `p27-hermes-society-foundation-plan.md` | L1092 | Changed `id (UUID v7, dedup key)` → `id (UUID v4, dedup key)` in §5.10 Replay Attack Defense table. Note: `society_id` references (L361, L3221) are NOT message envelope `id`; they are a separate `society_id` field using slug+hash convention in practice — confirmed not part of this fix. | FIXED |
| 6 | `kg_entities.created_by_agent` DDL drift — blueprint missing NOT NULL and missing `'system'` in CHECK (plan already correctly had these from Round 1 Fix 3) | MEDIUM (DDL DRIFT) | `p28-dual-autonomous-hermes-blueprint.md` | L1351–1352 | Added backfill `UPDATE memory.kg_entities SET created_by_agent = 'system' WHERE created_by_agent IS NULL;` before the ALTER (preserves provenance of pre-existing ADR-050 rows). Changed `created_by_agent TEXT` → `created_by_agent TEXT NOT NULL DEFAULT 'system'` and added `'system'` to CHECK constraint: `CHECK (created_by_agent IN ('guinevere', 'pharsa', 'system'))`. Blueprint now matches plan §6.2.6. | FIXED |
| 7 | Blueprint §5.1 envelope schema has `idempotency_key` defined twice (top-level L2109 + provenance section L2147) | LOW (DUPLICATION) | `p28-dual-autonomous-hermes-blueprint.md` | L2147 | Removed duplicate `idempotency_key: "<uuid v4>"` line in the provenance/audit section. Top-level placement (now at L2177, single occurrence) preserved — matches plan §5.2 canonical schema. | FIXED |

**Tally:** 7 / 7 fixed (100%). 0 partial. 0 deferred. 0 false positives.

## §3 Per-File Change Summary

### 3.1 `p28-dual-autonomous-hermes-blueprint.md` (6 fixes)

| Fix | Approx. Region | Net line delta | Notes |
|---|---|---|---|
| Fix 1 | §4.x `_cascade_halt` body (now L873–885) | +3 lines | Added trailing `await self.stop_all(graceful=False)` + 2-line comment. |
| Fix 2 | Step 5 systemd `pharsa-core.service` config (now L1038) | +1 line | Inline note inserted after ExecStart line. |
| Fix 3 | §2.6 table + Step 6 run commands + new Migration 008 / 009 sections | +75 lines (approx) | Two new rows in files-to-create, two commented psql commands, two full DDL blocks. |
| Fix 4 | Migration 003 `memory.shared_world.retrievability` (now L1265) | 0 net | Single SQL token replacement. |
| Fix 6 | Migration 005 `kg_entities` ALTER block (now L1354–1360) | +3 lines | Added backfill UPDATE + NOT NULL DEFAULT + 'system' in CHECK. |
| Fix 7 | §5.1 envelope JSONC schema (line shifted to L2177 after line additions) | -1 line | Removed duplicate `idempotency_key` line in provenance section. |

**Total net delta for blueprint:** ≈ +81 lines (2921 → ~2999 lines, post-fix).

### 3.2 `p27-hermes-society-foundation-plan.md` (1 fix)

| Fix | Approx. Region | Net line delta | Notes |
|---|---|---|---|
| Fix 5 | §5.10 Replay Attack Defense table (L1092) | 0 net | Single token: `UUID v7` → `UUID v4`. |

**Total net delta for plan:** 0 structural lines (4784 unchanged), 2 characters changed.

## §4 Round 2 Findings Confirmed vs False Positive

All 7 findings reproduced in current docs (pre-fix state) and resolved. **Zero findings reclassified as false positives.** Every finding was an actual definition-level defect with concrete implementation impact:

| Finding | Would have caused | Confirmed? |
|---|---|---|
| F-04 cascade_halt | HARD STOP leaves instances running (V-008 violation, persona drift risk) | YES |
| F-01 society_app | `pharsa-core.service` exits with `ModuleNotFoundError` (impossible to deploy) | YES |
| F-03 hpp_* DDL | Steps 8/9 reference tables that never get created — runtime crash on first peer message | YES |
| F-02 retrievability | `exp(0) * importance_score = importance_score` — decay sweep never evicts stale shared facts; silent memory bloat | YES |
| UUID v7 residual | Implementer reads §5.10 → tries to use UUID v7 library, contradicts §5.2 (subtle drift) | YES |
| kg_entities DDL drift | Pre-existing null provenance rows; not-NULL constraint failure if added later | YES |
| idempotency_key duplicate | JSON validator strictness differs across Pydantic versions — risk of silent double-load | YES |

## §5 Cross-Reference Verification

After applying all fixes, the following cross-references are now consistent:

| Cross-reference | Before Round 2 | After Round 2 |
|---|---|---|
| Plan §5.10 L1092 vs Plan §5.2 L897 UUID version | Conflict (v7 vs v4) | ✅ Both v4 |
| Blueprint Migration 005 `kg_entities` vs Plan §6.2.6 `kg_entities` | Conflict (NULL vs NOT NULL; missing 'system') | ✅ Both NOT NULL + 'system' in CHECK |
| Blueprint envelope §5.1 `idempotency_key` count | 2 occurrences (L2109 + L2147) | ✅ 1 occurrence (top-level only) |
| Blueprint Retrievability formula shared vs private | shared: `now()-now()`; private: correct | ✅ Both use `now()-last_accessed_at` |
| Blueprint §2.4 table vs migrations 001-007 vs Step 8/9 DDL | References `hpp_outbox/inbox` but no DDL | ✅ DDL via Migration 008/009 |
| Blueprint Step 5 ExecStart reference | Phantom module | ✅ Documented as P28 deliverable |
| Blueprint V-008 HARD STOP behavior | Listener exits but instances keep running | ✅ Cascade halts both watcher AND instances |

## §6 Architectural Integrity Preserved

- **No scope creep.** Each fix touches only the surface the auditor flagged. No surrounding sections rewritten.
- **No new dependencies.** Migration 008/009 use existing Postgres primitives (`BIGSERIAL`, partial indexes, JSONB) — no extension requirements beyond what's already in the project's migration baseline.
- **No break of backward compatibility.** Existing audit trail, dedup pattern, envelope schema semantics all preserved. The `idempotency_key` removal is from provenance JSONC example, NOT from the runtime envelope contract — the canonical placement (top-level) is the one used by Pydantic `Envelope` model.
- **Safety boundary preserved.** Fix 1 (cascade halt) is implemented as a defensive tail-call AFTER audit writes — so even if `stop_all` raises, the audit trail exists. Audit BEFORE halt, per `05-blueprint-bugs-audit.md` audit note (L110) "ensures audit trail is written BEFORE instances are torn down".

## §7 What Was NOT Done (Deferred to Implementation)

These items appear in the audit reports but are correctly classified as implementation-phase tasks, NOT definition-phase edits. They are out of scope for Round 2:

- 008/009 migrations are documented and structurally complete, but actual `psql -f` execution happens in Steps 8/9 (operator runs them with the rest of the migration sequence at that point).
- The `_cascade_halt` change requires a corresponding test update in `tests/life_kernel/test_hard_stop_cascade.py` (still audit-only flagged as future work; no test file exists at this point because P28 is not yet implemented).
- The `society_app.py` skeleton is documented but not authored yet — that is a Step 3 deliverable. The blueprint footers/self-tasks are now clear that the file WILL be created (audit's "Option A" recommended fix).

## §8 Open Adjacent Issues (Not in Round 2 Scope)

These were either escalated from Round 1 or noticed during synthesis. They are explicitly **NOT** Round 2 fixes and are NOT blocking Phase 9 finalization:

1. **kg_edges vs kg_entities CHECK constraint asymmetry.** Plan §6.2.6 L1389–1390: `kg_edges.created_by_agent CHECK IN ('guinevere','pharsa')` does NOT include `'system'`, while `kg_entities.created_by_agent` (post-fix) DOES include `'system'`. This may be intentional (edges always have specific owner) or oversight. Documented as FUTURE clarification; not blocking. Source: `06-integration-consistency-audit.md` Secondary Finding.
2. **§5.10 Replay Attack Defense table** lists only `sender.seq` + `id` + `hash_chain` + `created_at` — does NOT explicitly name `idempotency_key` as a row. The dual-defense pattern IS correctly named in §5.8 (L1063) and blueprint config (`pharsa.yaml` `inbox_dedup_by`). Documented as FUTURE completeness improvement; not blocking.
3. **society_id convention** ("UUID v7 or {slug}-v{epoch}-{short_hash}") at plan L361, L3221 references a society identity field — different from message `id`. NOT changed in Round 2 because it's a separate convention. Audit confirmed not a regression.

## §9 Verification

All 7 edits were applied via the `edit` tool with exact string match and verified by re-reading post-edit content + grep-driven cross-reference count:

| Fix | Verification command | Result |
|---|---|---|
| 1 | `grep "await self.stop_all(graceful=False)" p28...md` | Present in `_cascade_halt` body (L885) ✅ |
| 2 | `grep "society_app.py is a P28 file" p28...md` | Present (L1038) ✅ |
| 3 | `grep "Migration 008\|Migration 009\|008_hpp_outbox\|009_hpp_inbox" p28...md` | 8 matches (file table ×2, run commands ×2, section headers ×2, DDL filename ×2) ✅ |
| 4 | Visual diff L1259 vs L1203 — both should use `last_accessed_at` | ✅ Match confirmed |
| 5 | Visual re-read plan L1092 | Now "UUID v4" ✅ |
| 6 | Visual re-read blueprint L1356-1360 — has NOT NULL + 'system' in CHECK | ✅ Matches plan §6.2.6 |
| 7 | `grep "\"idempotency_key\"" p28...md` | 1 match (down from 2) ✅ |

## §10 Verdict

**READY FOR PHASE 9 FINALIZATION.**

All 7 Round 2 findings resolved. Plan + Blueprint now fully consistent. No new dependencies introduced. Safety boundary (V-008 HARD STOP) defensively enforced by Fix 1. No architectural decisions changed. Evidence + audit reports unchanged (they remain as Round 2 inputs for this log; Round 3 will run as part of Phase 9 finalization gate if Faiz requests, per AGENTS.md §2.3 planner gate discipline).

### Operator Handoff

- **Files modified in this round:** 2 (blueprint + plan).
- **Files added:** 1 (this fix log).
- **Total characters/line delta:** ~+81 lines blueprint, 0 lines plan (2 character changes).
- **Next decision point for Faiz:** approve Phase 9 finalization, or request additional Round 3 audit scope.
- **Open adjacent items (§8):** 3 non-blocking — defer or fold into Round 3 if Faiz wants them tight before Phase 9 lock-in.

---

## §11 Footer

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (Sisyphus-Junior) on behalf of Faiz | Initial round 2 fix log recording resolution of all 7 audit findings. |

### Maintenance

Update if additional rounds require side-by-side comparison. Future fix logs should reference this one's prefix `p27-round-2-` to follow the `p27-round-N-fix-log.md` convention.

### Operator Sign-Off

Auto-approved via `lanjut ... full autonomous sampai selesai atau benar-benar blocked` pattern; produced by Guinevere for Faiz review as part of Phase 8 → Phase 9 pre-finalization cleanup. No secrets, no destructive ops, no out-of-scope edits.

> Selesai. Definitions are consistent. Blueprint and plan match. HARD STOP now actually halts.
