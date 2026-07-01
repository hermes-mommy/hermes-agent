# P4 Implementation Audit Plan

**Date:** 2026-06-25
**Phase:** Plan (post-research synthesis)
**Status:** EXECUTING
**Audit Mode:** READ-ONLY ONLY

## Research Synthesis

6 research reports produced (see `docs/setup-evidence/legacy-audit/P4/research/`):

| File | Lines | Key Finding |
|------|-------|-------------|
| `p4-repo-evidence-inventory.md` | 470 | 23 STEP dirs, only verification.md each, zero evidence/ subfolders, zero auditor-gate.md files. Contradictory test counts (1449 vs 1460). D04-tests-batch2.md empty (0 bytes). |
| `p4-persona-source-map.md` | 420 | **CRITICAL**: P4-020 consent revocation has NO source-level integration. P4-002 table name wrong (`mood_states` vs `persona_state`). P4-008-013 all DEPRECATED Phase 5→Phase 7 (removal never happened). P4-015 "rollback" is record-keeping only. Y6 truly impossible (5 guards). HARD STOP→Y0 verified. |
| `p4-runtime-readiness-readonly.md` | 255 | **CRITICAL**: Only 4/14 persona modules wired live. 10 modules dead code. PersonaPlugin NOT registered. MoodRepository not called. 1160 persona tests collected. |
| `p4-known-issues-reconciliation.md` | 330 | 4/17 resolved, 10 open, 3 stale. R-03 factually incorrect. 7 new findings not tracked. PR-01 bridge callback wired but not full SafetyCoordinator. |
| `p4-phase4-naming-collision.md` | 231 | MODERATE. No status-bleed. 3rd "Phase 4" entity exists in acceptance criteria catalog. |
| `p4-downstream-impact-p19-p24.md` | 367 | **Split architecture**: src/persona/ (logic) + src/hermes/plugins/ (runtime). P19/20/22/23/24 compatible. Stale import in wearable/alert_router.py. WhatsApp/Gmail hardcode mood="Content". Two SafeModeController instances. |

## Severity Classification

| Severity | Count | Top items |
|----------|-------|-----------|
| **CRITICAL** | 2 | P4-020 consent revocation not in source; PersonaPlugin not registered (9/14 modules dead) |
| **HIGH** | 4 | P4-015 drift rollback log-only; Stale SOUL_BASELINE_HASH; 10 unwired modules; R-03 claim false |
| **MEDIUM** | 8 | P4-002 wrong table name; P4-008-013 deprecated but not noted; milestone_engine unowned; 7 KNOWN-ISSUES findings untracked; 23/23 steps lack evidence/ subfolders; 23/23 steps lack auditor-gate.md; 2 SafeModeController instances; WhatsApp/Gmail hardcode mood |
| **LOW** | 5 | P4-001 linear chain label; A01-A04 advisories; D04-tests-batch2 empty; stale wearable import; 3rd Phase 4 entity |

## Wave-1 Audit Dimensions (7 parallel)

Each writes to `docs/setup-evidence/legacy-audit/P4/audits/round-1/`.

### 1. Architecture & Implementation Completeness
**File:** `architecture-implementation.md`
**Scope:** Verify every P4-001→P4-023 module exists, compiles, and implements what it claims. Cross-reference source map against STEP evidence. Flag dead code, half-implemented features, missing wiring. Assess split architecture (src/persona vs hermes/plugins vs discord).
**Must check:**
- Each module's actual implementation vs P4 checklist claim
- Deprecation markers vs checklist completeness claims
- milestone_engine.py ownership
- PersonaPlugin registration status
- 6 unwired modules (mood_persistence, drift_corrector, punishment_engine, reward_engine, streak_tracker, transition_rules)

### 2. Evidence & Documentation Consistency
**File:** `evidence-docs-consistency.md`
**Scope:** Audit CHECKLIST.md, PROGRESS.md, P4 verification reports, batch-plan, audit reports — do they agree with each other and with source? Flag contradictory test counts, stale claims, missing evidence.
**Must check:**
- 1449 vs 1460 test count contradiction
- P4-002 table name discrepancy (mood_states vs persona_state)
- Every STEP-P4-### verification report vs actual source
- 23/23 steps lack evidence/ subfolders → flag as DOC GAP
- 23/23 steps lack auditor-gate.md → flag as DOC GAP
- D04-tests-batch2.md empty (0 bytes)
- A02 missing from NEW-AUDIT-2026
- D10 missing from P4-FINAL-AUDIT
- AC-PERSONA references missing from PROGRESS.md

### 3. Persona Safety, HARD STOP, & Consent
**File:** `persona-safety-hardstop-consent.md`
**Scope:** EXHAUSTIVE audit of every safety claim. This is the highest-stakes dimension.
**Must check:**
- Y6 truly impossible (5 guards verified, all code paths)
- HARD STOP → Y0 neutral (all code paths, including unwired instances)
- Consent revocation halts escalation (CLAIMED vs SOURCE REALITY — critical finding already known)
- P4-020 consent source-level gap — verify breadth
- Punishment suppressed during emergency (priority ordering)
- Distress D0-D4 detection completeness
- False negative risk assessment for distress patterns
- HARD STOP bypass risk across all layers (Hermes, life_kernel, Discord, wearable)
- SafeModeController dual-instance risk
- P20 autonomy HARD STOP bypass check
- PunishmentEngine HARD STOP guard conditionality (if handler is None → silently skipped)

### 4. Mood, Punishment, & Reward Runtime
**File:** `mood-punishment-reward-runtime.md`
**Scope:** Verify the mood FSM, punishment ladder, reward tiers, and streak tracking are correctly implemented AND wired into the runtime.
**Must check:**
- Mood FSM transition accuracy (Content→Disappointed skip, Silent→Content skip)
- PUNISHMENT_CONFIG L1-L5 accuracy vs SOUL.md and PersonaDoc
- L6 deferred/forbidden enforcement
- Reward tiers T1-T5 thresholds
- Streak tracking persistence
- MoodPersistence not called at runtime → gap
- PunishmentEngine not called at runtime → gap
- RewardEngine not called at runtime → gap
- All 6 unwired modules: what is the actual runtime behavior without them?

### 5. Ritual, Scheduler, & Drift Correction
**File:** `ritual-scheduler-drift-correction.md`
**Scope:** Verify ritual scheduler deprecation status, drift detection/correction correctness, and actual runtime behavior.
**Must check:**
- 5 ritual modules all deprecated Phase 5 → not removed by Phase 7 → stale
- RitualScheduler not instantiated live → Hermes cron replaces it
- DriftDetector SOUL_BASELINE_HASH staleness
- DriftCorrector "rollback" is log-only, not real prompt reload
- Drift detection actually wired in safety_plugin hooks
- Drift correction not wired at runtime (DriftCorrector has no caller)
- Hermes cron ritual jobs actual existence in config

### 6. Tests & Runtime Readiness
**File:** `tests-runtime-readiness.md`
**Scope:** Audit test suite completeness, collection errors, test quality, and runtime readiness assessment.
**Must check:**
- 1160 persona tests collected (clean)
- 5434 whole-repo tests collected (11 WhatsApp errors unrelated)
- 1449 vs 1460 test count contradiction resolution
- test_hard_stop_model.py: 14 tests collected clean → errors are runtime, not import
- Missing test categories (consent revocation integration, drift rollback, ritual wiring, mood persistence integration)
- Mock vs real test analysis
- Test coverage gaps for unwired modules
- NEEDS RUNTIME VERIFICATION items (systemctl, journalctl, live DB)

### 7. Downstream P19-P24 Compatibility
**File:** `downstream-p19-p24-compatibility.md`
**Scope:** Verify P4 persona engine compatibility with the P19→P24 roadmap.
**Must check:**
- P19 multi-project: global persona state intentional → compatible
- P20 autonomy: no bypass found → compatible
- P21 voice: definition-only, no conflict
- P22 raw access: AuthLevel and persona at different layers → compatible
- P23 action layer: definition-compatible, hook points exist
- P24 fork convergence: split architecture, consolidation recommended
- Stale wearable import fix needed
- Two SafeModeController instances → consolidation needed
- External channels hardcode mood → integration gap

## Wave-2: Adversarial Verification

After wave-1 completes, each CRITICAL and HIGH finding gets adversarial verification:
- N independent skeptics try to refute each finding
- If ≥majority cannot refute → CONFIRMED
- If refuted → RECLASSIFIED with evidence
- Each verifier writes to `docs/setup-evidence/legacy-audit/P4/audits/round-2/`

## Final Outputs

After wave-2, synthesize into:
- `evidence/bug-register-all-severity.md` — every confirmed bug, C/H/M/L/Cosmetic
- `evidence/missing-docs-register.md` — every missing/incomplete doc
- `evidence/implementation-gap-register.md` — every unwired/dead/half-implemented feature
- `evidence/superseded-transition-register.md` — every deprecated/superseded/split module
- `evidence/final-p4-implementation-audit-report.md` — master synthesis with binding verdict

## Binding Status Candidates

Based on research findings, the most likely final status:
- **PARTIALLY IMPLEMENTED** (4/14 modules wired, 10 dead, consent gap, deprecated rituals)
- **PARTIALLY SUPERSEDED BY HERMES/P20** (rituals replaced by Hermes cron, safety split across plugins)
- **IMPLEMENTED WITH BUGS** (if we ignore the unwired/dead modules as future-phase)

Wave-1 and wave-2 will determine the final binding verdict.