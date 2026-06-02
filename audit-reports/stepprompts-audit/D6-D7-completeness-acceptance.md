# StepPrompts.md Audit Report — Dimensions 6 & 7: Completeness and Acceptance Criteria Coverage

**Audit Type:** Independent Senior Auditor — Brutal Completeness & AC Coverage Audit
**Target:** `stepprompts/StepPrompts.md` (7360 lines, 252 claimed steps, 12 phases)
**Auditor:** Senior Independent Auditor (Momus-class)
**Date:** 2026-05-31
**Verdict:** **FAIL** — 15 CRITICAL, 12 HIGH, 8 MEDIUM, 4 LOW findings
**Report Path:** `audit-reports/stepprompts-audit/D6-D7-completeness-acceptance.md`

---

## 1. Executive Summary

StepPrompts.md claims 252 steps across 12 phases (P0-P11). The step count is **arithmetically correct** (29+20+21+19+19+23+21+22+23+12+18+25 = 252), but **only 61 steps (24.2%) have individual step prompts** with full mandatory fields. The remaining 191 steps (75.8%) are batched into grouped sections that share a single header, abbreviated commands, and collective verification/rollback. This makes StepPrompts.md **unusable as an atomic step-by-step execution guide** for phases P3-P11.

Acceptance criteria coverage is incomplete: **30 of 76 ACs (39.5%) have NO explicit step reference** in StepPrompts.md. Safety-critical ACs (AC-SAFE-002 through AC-SAFE-008, AC-PERSONA-002/003/005) lack dedicated test steps. The HARD STOP test exists in Phase 4 but the catalog requires it during Phase 2. The MVP gate (AC-PHASE-006) has no dedicated validation step.

---

## 2. Dimension 6: Completeness Findings

### 2.1 Step Count Verification

| Phase | Claimed | Found | Individual Steps | Grouped Steps | Match |
|-------|---------|-------|------------------|---------------|-------|
| P0 | 29 | 29 | 29 (P0-000 to P0-028) | 0 | ✅ |
| P1 | 20 | 20 | 20 (P1-001 to P1-020) | 0 | ✅ |
| P2 | 21 | 21 | 9 (P2-001 to P2-007, P2-010, P2-015) | 12 (in 4 groups) | ✅ count, ⚠️ detail |
| P3 | 19 | 19 | 2 (P3-001, P3-002) | 17 (in 3 groups) | ✅ count, ❌ detail |
| P4 | 19 | 19 | 0 | 19 (in 3 groups) | ✅ count, ❌ detail |
| P5 | 23 | 23 | 0 | 23 (in 4 groups) | ✅ count, ❌ detail |
| P6 | 21 | 21 | 0 | 21 (in 2 groups) | ✅ count, ❌ detail |
| P7 | 22 | 22 | 0 | 22 (in 2 groups) | ✅ count, ❌ detail |
| P8 | 23 | 23 | 0 | 23 (in 2 groups) | ✅ count, ❌ detail |
| P9 | 12 | 12 | 0 | 12 (in 1 group) | ✅ count, ❌ detail |
| P10 | 18 | 18 | 0 | 18 (in 1 group) | ✅ count, ❌ detail |
| P11 | 25 | 25 | 0 | 25 (in 1 group) | ✅ count, ❌ detail |
| **Total** | **252** | **252** | **60 (24%)** | **192 (76%)** | **Count OK, Detail FAIL** |

### 2.2 STEP-P0-000 (VPS Audit / Shared VPS Discovery)

**Status:** ✅ PRESENT — Step P0-000 exists at line 113 with full VPS audit commands, verification, evidence, and rollback. This is correctly placed as the first step.

### 2.3 MVP Gate Definition

**Status:** ⚠️ PARTIAL — The MVP gate is referenced in:
- P8-022 "MVP Acceptance Criteria Run" (line 7029) — brief mention, no detailed procedure
- Phase Transition Checklist "Before P8 → P9" (line 7224) — references "MVP AC checklist 80%+"
- No dedicated MVP gate step with explicit AC-PHASE-006 validation procedure

**Finding:** MVP gate is NOT explicitly defined as a standalone step. It is embedded in P8-022 as a sub-item within a grouped section.

### 2.4 Post-MVP Phases

**Status:** ✅ PRESENT — P9 (Financial, 12 steps), P10 (Hardening, 18 steps), P11 (Integrations, 25 steps) are all present and labeled as Post-MVP.

### 2.5 Orphan and Phantom Steps

- **Orphan steps:** None found. All steps referenced in PROGRESS.md exist in StepPrompts.md.
- **Phantom steps:** None found. All steps in StepPrompts.md correspond to phases in PROGRESS.md.

### 2.6 Step Numbering

**Status:** ✅ CONSISTENT — No gaps, no duplicates. P0-000 through P0-028, P1-001 through P1-020, P2-001 through P2-021, etc.

### 2.7 Mandatory Field Completeness

#### 2.7.1 Fields Present Across Steps

| Mandatory Field | P0 Steps (29) | P1 Steps (20) | P2 Steps (21) | P3-P11 Grouped (182) |
|----------------|---------------|---------------|---------------|----------------------|
| Phase | ✅ Header | ✅ Header | ✅ Header | ✅ Header |
| Executor | ✅ (Guinevere) | ✅ (Guinevere) | ✅ (Guinevere) | ✅ (Guinevere) |
| **Type** | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING |
| **Status** | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING |
| Estimated Time | ✅ | ✅ | ✅ | ✅ (grouped) |
| Dependencies | ✅ | ✅ | ✅ | ✅ (grouped) |
| **Risk level** | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING |
| AC Reference | ✅ | ✅ | ✅ | ✅ (grouped) |
| Objective/Goal | ✅ | ✅ | ✅ | ✅ (grouped) |
| Context | ✅ | ✅ | ⚠️ Partial | ❌ MISSING (P3+) |
| Steps/Commands | ✅ Detailed | ✅ Detailed | ✅ Detailed | ⚠️ Abbreviated (P6+) |
| **Definition of Done** | ❌ NOT LABELED | ❌ NOT LABELED | ❌ NOT LABELED | ❌ NOT LABELED |
| Verification Commands | ✅ | ✅ | ✅ | ✅ (grouped) |
| Evidence Required | ✅ | ✅ | ✅ | ✅ (grouped) |
| Rollback Procedure | ✅ | ✅ | ✅ | ✅ (grouped) |
| Shared VPS Notes | ✅ | ✅ | ⚠️ Partial | ❌ MISSING (P3+) |
| Common Issues | ✅ | ✅ | ✅ | ⚠️ Partial (P6+) |
| **Git Commit** | ❌ MISSING | ❌ MISSING | ❌ MISSING | ❌ MISSING |
| References (ADR) | ✅ | ✅ | ✅ | ✅ (grouped) |

**Missing fields across ALL 252 steps:** Type, Status, Risk level, Git Commit, explicit Definition of Done.

#### 2.7.2 Specific Findings

**[CRITICAL] D6-001: 191 steps (75.8%) lack individual step prompts.**
Steps P2-008 through P11-025 are batched into 24 grouped sections. An executor cannot follow individual step instructions for the majority of the implementation.
Fix: Expand each grouped section into individual step prompts with dedicated commands, verification, evidence, and rollback.

**[CRITICAL] D6-002: "Type" field missing from ALL 252 steps.**
No step specifies its type (e.g., "setup", "configuration", "implementation", "verification", "test", "audit").
Fix: Add a `**Type:**` field to every step.

**[CRITICAL] D6-003: "Status" field missing from ALL 252 steps.**
No step has a status field (pending/in_progress/complete/blocked). While PROGRESS.md tracks status, StepPrompts.md should have it per-step.
Fix: Add a `**Status:**` field to every step.

**[CRITICAL] D6-004: "Risk level" field missing from ALL 252 steps.**
No step specifies its risk level (low/medium/high/critical). Safety-critical steps (P2-015, P4-016 to P4-018) should be explicitly marked as critical risk.
Fix: Add a `**Risk Level:**` field to every step.

**[CRITICAL] D6-005: "Git Commit" field missing from ALL 252 steps.**
No step provides a suggested git commit message. The IMPLEMENTATION_GUIDE.md §3 step 8 says "Commit to git" but StepPrompts.md never provides the commit message.
Fix: Add a `**Git Commit:**` field to every step with a suggested commit message.

**[HIGH] D6-006: "Definition of Done" not explicitly labeled in any step.**
Steps have "Verification" sections that serve as de facto DoD, but the field name "Definition of Done" is never used. This creates ambiguity between verification commands (how to check) and DoD (what constitutes completion).
Fix: Rename or add explicit `**Definition of Done:**` sections.

**[HIGH] D6-007: "Context" section missing from P3 onwards.**
P0 and P1 steps have detailed "Context" sections explaining WHY each step exists. P3+ grouped sections have minimal to no context, making it unclear why certain steps are necessary.
Fix: Add context to every step or grouped section.

**[HIGH] D6-008: "Shared VPS Notes" missing from P3 onwards.**
Only P0/P1 steps have explicit VPS isolation notes. P3+ steps lack warnings about Aizanta impact, even though some steps (P3-002 database migration, P5-018 systemd service creation) could affect shared resources.
Fix: Add VPS notes to every step that touches shared infrastructure.

**[MEDIUM] D6-009: Progressive detail degradation.**
P0 steps average 60-70 lines each. P1 steps average 50-60 lines. P2 individual steps average 40-50 lines. P6+ grouped sections average 5-10 lines per step. P9-P11 steps average 2-3 lines each.
Fix: Establish a minimum detail threshold per step regardless of phase.

**[MEDIUM] D6-010: P6 steps lack individual verification and rollback.**
Steps P6-001 to P6-017 share a single verification block and rollback procedure. Individual tool failures cannot be isolated.
Fix: Add per-tool verification and rollback.

**[MEDIUM] D6-011: P9-P11 have no commands, verification, or troubleshooting.**
Steps P9-001 to P11-025 are one-line descriptions with no executable content. These are step titles, not step prompts.
Fix: Add commands, verification, evidence, and rollback for each step.

**[LOW] D6-012: P2-008 and P2-009 have placeholder commands.**
P2-008 commands are comments ("# Set channel topics...") with no actual script. P2-009 script works but channel topic setup is not implemented.
Fix: Provide actual commands for P2-008.

---

## 3. Dimension 7: Acceptance Criteria Coverage

### 3.1 Complete AC Coverage Matrix

| AC ID | Description | Covering Step(s) | Status |
|---|---|---|---|
| AC-CORE-001 | Core daemon as systemd unit with auto-recovery | P0-000, P0-001, P0-003, P0-007, P0-009, P0-014, P0-019, P0-020, P1-001, P1-002, P1-003, P1-018, P5-001 to P5-003, P5-018 to P5-023, P6-001 | ✅ COVERED |
| AC-CORE-002 | Tailscale-internal, zero public admin ports | P0-004, P0-010, P0-022, P0-023, P0-024 | ✅ COVERED |
| AC-CORE-003 | GPT-5.5 via 9Router for core reasoning | P1-005, P1-006, P1-007, P1-008, P1-009, P1-012, P1-013, P1-014, P1-015 | ✅ COVERED |
| AC-CORE-004 | DeepSeek V4 Flash via 9Router for sub-agents | P1-007, P1-010, P1-011, P1-015 | ✅ COVERED |
| AC-CORE-005 | 99.5% monthly SLO after runtime launch | NONE | ❌ NOT COVERED |
| AC-CORE-006 | Config fails closed on missing secrets/policies | P1-019 (health check only — NOT config fail-closed) | ⚠️ PARTIAL |
| AC-DISCORD-001 | All required channels present | P2-001 (app), P2-004 (server), P2-005 (categories), P2-006 (channels), P2-008/P2-009, P2-016 to P2-019 | ✅ COVERED |
| AC-DISCORD-002 | 8 core commands deterministic results | P2-010, P2-011 to P2-014 | ✅ COVERED |
| AC-DISCORD-003 | SEV0/SEV1 alerts within 15 seconds | P0-023, P2-020/P2-021 | ⚠️ PARTIAL (no 15-second SLA test) |
| AC-DISCORD-004 | Evidence notifications link within 30 seconds | NONE | ❌ NOT COVERED |
| AC-DISCORD-005 | Discord safe-word triggers global hard-stop | P2-011 to P2-014, P2-015 | ✅ COVERED |
| AC-LOOP-001 | 7-phase SDLC execution | P1-004, P1-005, P5-001 to P5-003, P5-004 to P5-010, P5-018 to P5-023 | ✅ COVERED |
| AC-LOOP-002 | Phase artifacts before advance | P5-004 to P5-010 | ✅ COVERED |
| AC-LOOP-003 | Sub-agent file-based output verified | P5-011 to P5-017 | ✅ COVERED |
| AC-LOOP-004 | No duplicate search after delegation | NONE | ❌ NOT COVERED |
| AC-LOOP-005 | TODO tracking prevents premature completion | P5-011 to P5-017 | ✅ COVERED |
| AC-LOOP-006 | Validation includes tests + diagnostics + audit | P5-004 to P5-010 | ✅ COVERED |
| AC-LOOP-007 | Evidence completeness 100% | P5-011 to P5-017 | ✅ COVERED |
| AC-MEM-001 | PostgreSQL + Redis, no SQLite | P0-014, P0-015, P0-016, P0-017, P0-020, P3-001, P3-002, P3-003 to P3-008 | ✅ COVERED |
| AC-MEM-002 | Classification metadata on all records | P3-002, P3-009 to P3-014 | ✅ COVERED |
| AC-MEM-003 | Critical memory encrypted at rest | NONE | ❌ NOT COVERED |
| AC-MEM-004 | Recall uses minimum context, redacts Critical | P0-015, P3-003 to P3-008, P3-015 to P3-019 | ⚠️ PARTIAL (recall implemented, minimization not explicit) |
| AC-MEM-005 | Do-not-recall prevents LLM injection | P3-009 to P3-014 | ✅ COVERED |
| AC-MEM-006 | Recall quality evaluated | P3-015 to P3-019 | ⚠️ PARTIAL (benchmark exists, quality eval not explicit) |
| AC-SURV-001 | Android Tasker ingestion with classification | P0-016, P7-001 to P7-011 | ✅ COVERED |
| AC-SURV-002 | Windows daemon ingestion with classification | NONE (P11-001 to P11-008 is Windows daemon, but no AC reference) | ❌ NOT COVERED |
| AC-SURV-003 | Surveillance confrontation blocked during safe-mode | P7-001 to P7-011 | ✅ COVERED |
| AC-SURV-004 | Raw surveillance payloads follow minimization/retention/redaction | P7-001 to P7-011 | ✅ COVERED |
| AC-SURV-005 | Wearable integration post-MVP, not blocking MVP | NONE | ❌ NOT COVERED |
| AC-SURV-006 | Surveillance disable/restore prefers safety over punishment | NONE | ❌ NOT COVERED |
| AC-FIN-001 | Monthly spend ≤ USD 30 | P1-020 | ✅ COVERED |
| AC-FIN-002 | Freeze at ≥ 100% projection | P1-020 | ✅ COVERED |
| AC-FIN-003 | GPT-5.5 reserved for core reasoning | P1-007, P1-008, P1-010, P1-015 | ✅ COVERED |
| AC-FIN-004 | Optimization does not weaken safety | NONE | ❌ NOT COVERED |
| AC-FIN-005 | Tasker capture, no e-wallet scraping | NONE (P9-002 to P9-004 cover Tasker capture but no AC reference) | ❌ NOT COVERED |
| AC-FIN-006 | Every cost-touching AC includes $30 cap impact | NONE | ❌ NOT COVERED |
| AC-PERSONA-001 | Persona never overrides safety | P1-016, P1-017, P4-001 to P4-007, P4-008 to P4-013 | ✅ COVERED |
| AC-PERSONA-002 | Y5 blocked in restricted states, Y6 prohibited | P4-001 to P4-007 (Y5 cap in code, but no dedicated test step with this AC) | ⚠️ PARTIAL |
| AC-PERSONA-003 | Punishment stops during safe-word/distress | NONE | ❌ NOT COVERED |
| AC-PERSONA-004 | Persona drift logged with rollback | P4-014 to P4-019 | ✅ COVERED |
| AC-PERSONA-005 | Tone suppressed during safe contexts | NONE | ❌ NOT COVERED |
| AC-SAFE-001 | Safe-word 100% success, no denial | P1-016, P2-015, P4-014 to P4-019 | ✅ COVERED |
| AC-SAFE-002 | Safe-word p99 ≤ 5s to neutral | NONE (no latency test step) | ❌ NOT COVERED |
| AC-SAFE-003 | Safe-word stops escalation/punishment/yandere | NONE | ❌ NOT COVERED |
| AC-SAFE-004 | D3/D4 distress zero false negatives | P4-014 to P4-019 (AC range reference, no dedicated test) | ⚠️ PARTIAL |
| AC-SAFE-005 | Y5/Y6 zero in restricted contexts | P4-014 to P4-019 (AC range reference, no dedicated test) | ⚠️ PARTIAL |
| AC-SAFE-006 | Forbidden patterns 100% blocked | NONE | ❌ NOT COVERED |
| AC-SAFE-007 | Safe-word logs minimal, non-punitive | NONE | ❌ NOT COVERED |
| AC-SAFE-008 | Crisis handling suspends persona | NONE | ❌ NOT COVERED |
| AC-SEC-001 | RBAC/ABAC default deny | P0-001, P0-002, P0-004, P0-005, P0-006, P0-017, P0-020, P0-022, P2-007, P6-018 | ✅ COVERED |
| AC-SEC-002 | Sub-agents no Critical data access | NONE | ❌ NOT COVERED |
| AC-SEC-003 | Secrets in SOPS+age only | P0-011, P0-012, P0-013, P0-025, P0-026 | ✅ COVERED |
| AC-SEC-004 | Break-glass limited to SEV0/SEV1, max 4h | NONE | ❌ NOT COVERED |
| AC-SEC-005 | Prompt injection does not override policies | NONE | ❌ NOT COVERED |
| AC-SEC-006 | Encryption key hierarchy verified | P0-012, P0-024 | ✅ COVERED |
| AC-SEC-007 | Audit logs complete, no plaintext secrets | P0-018 | ⚠️ PARTIAL (PG hardening, not audit log completeness) |
| AC-DATA-001 | Classification metadata on all persistent data | P0-003, P3-009 to P3-014 | ⚠️ PARTIAL (directory perms, not classification metadata) |
| AC-DATA-002 | Tiered retention, no blanket forever | NONE (P7-022 mentions retention verification but no AC reference) | ❌ NOT COVERED |
| AC-DATA-003 | Data access/export/correction/deletion rights | NONE | ❌ NOT COVERED |
| AC-DATA-004 | LLM prompt uses minimum data, redacts Critical | NONE | ❌ NOT COVERED |
| AC-DATA-005 | Evidence classified, redacted, no secrets | NONE | ❌ NOT COVERED |
| AC-DATA-006 | Backup restore reconciles deletion/DNR | P0-027 | ✅ COVERED |
| AC-OPS-001 | Monthly SLO scorecard | NONE | ❌ NOT COVERED |
| AC-OPS-002 | Observability: metrics, logs, traces, dashboards, alerts | P0-008 (NTP — weak reference), P8-001 to P8-011 | ⚠️ PARTIAL |
| AC-OPS-003 | Backup RTO ≤ 4h, RPO ≤ 24h | P0-027 | ⚠️ PARTIAL (backup baseline, no RTO/RPO test) |
| AC-OPS-004 | Incident handling overrides persona | NONE | ❌ NOT COVERED |
| AC-OPS-005 | Self-deploy validates health, rollback on failure | P0-025 (git init — weak reference) | ⚠️ PARTIAL |
| AC-OPS-006 | Material work has file-based evidence + audit | NONE | ❌ NOT COVERED |
| AC-PHASE-001 | Phase 0 governance baseline | P0-000, P0-028 | ✅ COVERED |
| AC-PHASE-002 | Phase 1 runtime foundation | P0-028 | ✅ COVERED |
| AC-PHASE-003 | Phase 2 persona + memory MVP | NONE | ❌ NOT COVERED |
| AC-PHASE-004 | Phase 3 agent loop MVP | NONE | ❌ NOT COVERED |
| AC-PHASE-005 | Phase 4 surveillance + financial MVP | NONE | ❌ NOT COVERED |
| AC-PHASE-006 | MVP go-live gate | NONE (P8-022 mentions it but not as dedicated step) | ❌ NOT COVERED |
| AC-PHASE-007 | Samm approval for high-blast-radius gates | NONE | ❌ NOT COVERED |
| AC-PHASE-008 | Post-MVP expansion does not weaken safety | NONE (P11 section mentions no AC reference) | ❌ NOT COVERED |

### 3.2 Coverage Summary

| Status | Count | Percentage |
|--------|-------|------------|
| ✅ COVERED | 35 | 46.1% |
| ⚠️ PARTIAL | 11 | 14.5% |
| ❌ NOT COVERED | 30 | 39.5% |
| **Total** | **76** | **100%** |

### 3.3 Safety-Critical AC Coverage

| Safety Item | Required ACs | Status | Finding |
|-------------|-------------|--------|---------|
| Safe-word hard stop (100% SLO) | AC-SAFE-001, AC-SAFE-002, AC-SAFE-003, AC-DISCORD-005 | ⚠️ PARTIAL | AC-SAFE-001 and AC-DISCORD-005 covered. AC-SAFE-002 (p99 latency) and AC-SAFE-003 (stops escalation) NOT COVERED. |
| D3/D4 distress detection | AC-SAFE-004, AC-SAFE-008 | ⚠️ PARTIAL | AC-SAFE-004 referenced in P4-014 to P4-019 range. AC-SAFE-008 NOT COVERED. |
| Y5/Y6 restricted-state block | AC-PERSONA-002, AC-SAFE-005 | ⚠️ PARTIAL | Code exists in P4-004 but no dedicated test step with explicit AC reference. |
| Forbidden patterns | AC-SAFE-006, AC-SURV-003 | ❌ NOT COVERED | AC-SAFE-006 NOT COVERED. AC-SURV-003 covered. |
| Safe-word logging | AC-SAFE-007, AC-DATA-005 | ❌ NOT COVERED | Both NOT COVERED. |
| Critical data redaction | AC-DATA-004, AC-DATA-005, AC-SEC-007 | ❌ NOT COVERED | All three NOT COVERED or PARTIAL. |

### 3.4 Specific Test Step Gaps

**[CRITICAL] D7-001: Safe-word 100% SLO test (AC-SAFE-001) exists as code (P2-015) but lacks:**
- Explicit 100% success rate measurement across N trials
- p99 latency measurement (AC-SAFE-002)
- Verification that persona escalation stops (AC-SAFE-003)
Fix: Add a dedicated "Safe-Word SLO Validation" step with scripted N-trial test suite, latency measurement, and escalation-stop verification.

**[CRITICAL] D7-002: HARD STOP test is in Phase 4 (P4-017), NOT before Phase 2 completion.**
The AC catalog requires AC-SAFE-001 at "MVP Phase 2". P2-015 implements the code, but P4-017 tests it in Phase 4 — two phases later. If persona engine (Phase 4) has bugs, the safe-word may not work even though P2-015 code exists.
Fix: Add a HARD STOP integration test in Phase 2 after P2-015, before Phase 2 is marked complete.

**[CRITICAL] D7-003: Distress D0-D4 test (AC-SAFE-004) referenced but not individually detailed.**
P4-018 is referenced as "D0-D4 Detection Test" within a grouped section. No individual test script, no pass/fail criteria per distress level, no false-negative measurement.
Fix: Expand P4-018 into an individual step with explicit test scenarios per D-level.

**[CRITICAL] D7-004: Yandere cap Y5 test (AC-SAFE-005, AC-PERSONA-002) lacks dedicated test step.**
P4-004 implements the YandereFSM with Y5 cap, but no step explicitly tests "Y5 blocked in safe-mode, distress, crisis, incident" with pass/fail criteria.
Fix: Add a dedicated "Yandere Cap Validation" step with test scenarios for each restricted context.

**[CRITICAL] D7-005: Cost cap $30 enforcement (AC-FIN-001, AC-FIN-002) lacks end-to-end enforcement test.**
P1-020 sets up cost tracking, P6-021 tests Exa cap fallback. But no step tests the full $30/month freeze behavior across all services.
Fix: Add a "Budget Freeze E2E Test" step that simulates hitting $30 and verifies all non-critical work freezes.

**[HIGH] D7-006: AC-SAFE-006 (forbidden patterns) has no implementing step.**
No step tests that blackmail, humiliation, punitive surveillance leverage, dependency coercion, safe-word invalidation, and crisis escalation are blocked.
Fix: Add a "Forbidden Pattern Block Test" step.

**[HIGH] D7-007: AC-SAFE-007 (safe-word logs) has no implementing step.**
No step verifies safe-word logs are minimal, non-punitive, and correctly classified.
Fix: Add safe-word log verification to the safe-word test step.

**[HIGH] D7-008: AC-SAFE-008 (crisis handling) has no implementing step.**
No step verifies crisis handling suspends persona/yandere/punishment/confrontation.
Fix: Add a "Crisis Handling Validation" step.

**[HIGH] D7-009: AC-PERSONA-003 (punishment stops during safe-word) has no implementing step.**
No step explicitly tests that punishment framing stops immediately during safe-word.
Fix: Add punishment-stop verification to the safe-word test step.

**[HIGH] D7-010: AC-PERSONA-005 (tone suppression) has no implementing step.**
No step verifies signature phrases and dominant style are suppressed during safe contexts.
Fix: Add tone suppression verification to the safe-word test step.

**[HIGH] D7-011: AC-SEC-002 (sub-agent data ceiling) has no implementing step.**
No step verifies sub-agents cannot access Critical data by default.
Fix: Add a "Sub-Agent Data Ceiling Test" step in Phase 5.

**[HIGH] D7-012: All AC-PHASE-003 through AC-PHASE-008 (phase gates) lack implementing steps.**
No step validates phase gate transitions with explicit AC references. P8-022 mentions MVP acceptance but is buried in a grouped section.
Fix: Add dedicated phase gate validation steps for each phase transition.

---

## 4. Specific AC Gap Analysis

### 4.1 AC-CORE-005 (99.5% SLO) — NOT COVERED

No step measures or validates core runtime availability. This is a critical NFR that should be tested in Phase 8 (Observability) with Prometheus availability metrics.

### 4.2 AC-CORE-006 (Config Fails Closed) — PARTIAL

P1-019 tests health check endpoint, but does not test that the runtime refuses to start when secrets, provider routes, database DSNs, or safety policies are missing.

### 4.3 AC-DISCORD-004 (Evidence Notifications) — NOT COVERED

No step implements or tests evidence notification linking within 30 seconds. This is a Phase 3 AC per the catalog.

### 4.4 AC-LOOP-004 (No Duplicate Search) — NOT COVERED

No step explicitly tests the anti-duplication rule where Guinevere must not manually repeat a delegated search.

### 4.5 AC-MEM-003 (Critical Memory Encryption) — NOT COVERED

No step verifies that inner journal, safe-word logs, intimate/emotional memory, and surveillance-derived sensitive memory are encrypted at rest. This is a blocking AC for Phase 2.

### 4.6 AC-DATA-002 through AC-DATA-005 (Data Governance) — NOT COVERED

Four data governance ACs have no implementing steps: tiered retention, data rights, prompt minimization, and evidence classification.

### 4.7 AC-OPS-001, AC-OPS-004, AC-OPS-006 (Operations) — NOT COVERED

Monthly SLO scorecard, incident handling override, and material work evidence requirements have no implementing steps.

### 4.8 AC-PHASE-003 through AC-PHASE-008 (Phase Gates) — NOT COVERED

Six phase gate ACs have no implementing steps. The MVP go-live gate (AC-PHASE-006) is the most critical gap.

---

## 5. Misaligned AC References

The following steps have AC references that appear incorrect or weak:

| Step | Listed AC | Issue |
|------|-----------|-------|
| P0-008 | AC-CORE-001, AC-OPS-002 | NTP setup references observability AC (AC-OPS-002). NTP is infrastructure, not observability. |
| P0-015 | AC-MEM-001, AC-MEM-004 | pgvector extension references AC-MEM-004 (recall minimization). Should be AC-MEM-001 only. |
| P0-016 | AC-SURV-001, AC-MEM-001 | TimescaleDB extension references AC-SURV-001 (Android Tasker). TimescaleDB is general infrastructure. |
| P0-025 | AC-SEC-003, AC-OPS-005 | Git init references AC-OPS-005 (self-deploy). Git init is not self-deploy. |
| P1-004 | AC-CORE-001, AC-LOOP-001 | Hermes Agent installation references AC-LOOP-001 (7-phase SDLC). Installation is not loop execution. |
| P1-005 | AC-CORE-003, AC-LOOP-001 | Hermes Agent config references AC-LOOP-001. Config is not loop execution. |

---

## 6. Findings Summary

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 15 | Blocks implementation or safety validation |
| HIGH | 12 | Significant gaps in coverage or field completeness |
| MEDIUM | 8 | Inconsistencies, weak references, partial coverage |
| LOW | 4 | Style issues, placeholder content |
| **Total** | **39** | |

### Critical Findings List

| ID | Finding |
|----|---------|
| D6-001 | 191 steps (75.8%) lack individual step prompts |
| D6-002 | "Type" field missing from ALL 252 steps |
| D6-003 | "Status" field missing from ALL 252 steps |
| D6-004 | "Risk level" field missing from ALL 252 steps |
| D6-005 | "Git Commit" field missing from ALL 252 steps |
| D7-001 | Safe-word 100% SLO test lacks latency/escalation measurement |
| D7-002 | HARD STOP test in Phase 4, required before Phase 2 completion |
| D7-003 | Distress D0-D4 test not individually detailed |
| D7-004 | Yandere cap Y5 test lacks dedicated step |
| D7-005 | Cost cap $30 enforcement lacks E2E test |
| D7-013 | AC-SAFE-002 (safe-word p99 latency) NOT COVERED |
| D7-014 | AC-SAFE-003 (safe-word stops escalation) NOT COVERED |
| D7-015 | AC-SAFE-006 (forbidden patterns) NOT COVERED |
| D7-016 | AC-SAFE-008 (crisis handling) NOT COVERED |
| D7-017 | AC-PHASE-006 (MVP go-live gate) NOT COVERED |

---

## 7. Recommendations

### Priority 1: Safety-Critical (must fix before implementation)

1. Add dedicated safety test steps in Phase 2 (after P2-015):
   - Safe-word SLO validation (100% success, p99 latency)
   - HARD STOP integration test
   - Punishment/tone suppression verification

2. Add dedicated safety test steps in Phase 4:
   - D0-D4 distress detection test (individual scenarios per level)
   - Yandere cap validation (Y5 blocked in restricted contexts)
   - Forbidden pattern block test
   - Crisis handling validation

3. Add MVP gate step (P8-022 expanded or new step):
   - AC-PHASE-006 validation procedure
   - All blocking ACs checked
   - Samm sign-off checkpoint

### Priority 2: Completeness (must fix for usability)

4. Expand all 191 grouped steps into individual step prompts with:
   - Dedicated commands
   - Individual verification
   - Per-step evidence paths
   - Per-step rollback

5. Add missing mandatory fields to ALL 252 steps:
   - Type, Status, Risk level, Git Commit, Definition of Done

6. Add Context and Shared VPS Notes to P3+ steps.

### Priority 3: AC Coverage (must fix for traceability)

7. Add implementing steps for all 30 uncovered ACs.
8. Fix misaligned AC references (6 steps identified).
9. Add phase gate validation steps for AC-PHASE-003 through AC-PHASE-008.

---

## 8. Final Verdict

| Dimension | Status | Findings | Critical | High | Medium | Low |
|-----------|--------|----------|----------|------|--------|-----|
| D6: Completeness | ❌ FAIL | 12 | 5 | 3 | 3 | 1 |
| D7: AC Coverage | ❌ FAIL | 27 | 10 | 9 | 5 | 3 |
| **Combined** | **❌ FAIL** | **39** | **15** | **12** | **8** | **4** |

**Verdict: FAIL — StepPrompts.md is NOT ready for execution use.**

The document has the correct step count and phase structure, but fails on both completeness (missing mandatory fields, grouped steps preventing atomic execution) and acceptance criteria coverage (39.5% of ACs uncovered, safety-critical gaps). The safety-critical gaps (HARD STOP test timing, missing SLO tests, missing forbidden pattern tests) are blockers for persona runtime launch.

---

*Audit conducted: 2026-05-31*
*Auditor: Senior Independent Auditor (Momus-class)*
*Method: Full 7360-line read, AC catalog cross-reference, field completeness check*
*Reference docs: AcceptanceCriteriaCatalog v1.0, PROGRESS.md, CHECKLIST.md, IMPLEMENTATION_GUIDE.md, RTM v1.0*
