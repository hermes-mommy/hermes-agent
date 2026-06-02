# Governance & Core Phase References — Exhaustive Catalog

**Generated:** 2026-06-02
**Agent:** explore (governance-phases)
**Total:** ~606 phase-related matches across 15 files in docs/10-governance/ and docs/00-core/

## CRITICAL DISTINCTION — Three Types of "Phase" References

1. **PROJECT DELIVERY PHASES** (Phase 0-5, MVP, Post-MVP) — **These are what Faiz is restructuring**
2. **SDLC LOOP PHASES** (Phase 1-7 of the 7-phase agent loop) — **Different concept, internal to coding agent**
3. **PRIORITY LEVELS** (P0=P5) — **NOT phases at all, just priority labels**

## Summary Statistics

| Directory | Files Scanned | Total Matches | Delivery Phase Refs | SDLC Loop Phase Refs | Priority (P0-P5) Refs | Generic "phase" Refs |
|---|---|---|---|---|---|---|
| docs/10-governance/ | 9 | ~510 | ~120 | ~80 | ~200 | ~110 |
| docs/00-core/ | 7 | ~96 | ~15 | ~45 | ~12 | ~24 |
| **TOTAL** | **16** | **~606** | **~135** | **~125** | **~212** | **~134** |

## CONFLICT: Delivery Phase Naming Between Docs

| Doc | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|---|---|---|---|---|---|---|
| **Charter** | Governance Baseline | MVP Runtime Foundation | Persona & Memory MVP | Autonomous SDLC MVP | Surveillance & Financial MVP | Expansion & Hardening |
| **BRD** | Infrastructure Setup | Core Persona & Memory | Surveillance Stack | Autonomous Coding Agent | Monitoring & Financial | Self-Improvement & Hardening |
| **AcceptanceCriteria** | Governance Baseline | Runtime Foundation | Persona & Memory MVP | Autonomous SDLC MVP | Surveillance & Financial MVP | Expansion & Hardening |
| **Persona** | — | Android Tasker (MVP) | Windows daemon | Wearable (Post-MVP) | — | — |

**Charter and AcceptanceCriteria are aligned. BRD uses DIFFERENT phase names.** Persona has its own surveillance rollout phasing.

## SECTION A: docs/10-governance/ — File-by-File

### A1. 10-ProjectCharter_v1.0.md (41 matches)
Key delivery phase refs:
- §17 Definition of Done by Phase: Phase 0-5 names (L228-235)
- Milestones M0-M9 mapped to phases (L271-282)
- §10 Full Scope and Phased Expansion (L134-136)
- Phase gate checklist appendix (L376-408)
- BG-006 Phase-by-phase implementation backlog (L374)

### A2. 11-FeasibilityStudy_v1.0.md (14 matches)
Mostly SDLC loop 7-phase refs. One delivery Phase 1 reference at L1156.

### A3. 12-SRS_v1.0.md (214 matches)
MASSIVE: ~120 are P0-P3 priority levels in requirement tables, NOT phases.
Delivery phase refs: phased delivery (L28), Phase 0-5 traceability.
SDLC loop refs: 7-phase loop, Phase 1-7 artifacts (L116), PHASE_7 state enum (L128).

### A4. 13-FSD_v1.0.md (29 matches)
Defines SDLC FSD-CODE-001 through 007 (Phase 1-7 loop). Delivery phase refs minimal.

### A5. 14-TDD_Guide_v1.0.md (87 matches)
Mixed: P0-P5 priority levels (test categories), SDLC Phase 1-7 (loop tests), deployment Phase 1-4 (L1739-1758 — infrastructure deployment, THIRD meaning).

### A6. 15-RTM_v1.0.md (38 matches)
Delivery Phase column maps requirements to Phase 2-4, MVP, Post-MVP.
Phase gate impact column. SDLC loop 7-phase refs.

### A7. 16-AcceptanceCriteriaCatalog_v1.0.md (86 matches — MOST PHASE-DENSE)
AC-PHASE-001 through AC-PHASE-008 define phase gate criteria.
AC-CORE, AC-DISCORD, AC-LOOP, AC-MEM, AC-SURV, AC-FIN, AC-PERSONA, AC-SAFE, AC-SEC, AC-DATA, AC-OPS all have Phase column mapping to delivery phases.
Phase Gate Checklist §12 with Phase 0-5 definitions.

### A8. 17-ADR_Index_v1.0.md (3 matches)
ADR-011 SDLC loop phase specification. 7-phase execution model.

## SECTION B: docs/00-core/ — File-by-File

### B1. 00-BRD_v2.0.md (8 matches)
Phase 0-5 delivery phases with DIFFERENT names than Charter.
Phase 0: Infrastructure Setup, Phase 1: Core Persona & Memory, Phase 2: Surveillance Stack, Phase 3: Autonomous Coding Agent, Phase 4: Monitoring & Financial, Phase 5: Self-Improvement & Hardening.

### B2. 01-PRD_v2.2.md (14 matches)
P0/P1 priority labels for persona traits. SDLC 7-phase loop refs.

### B3. 02-TechnicalArchitecture_v2.0.md (14 matches)
SDLC Phase 1-7 file tree (L220-232). Delivery Phase 0, 3, 5 tooling references.

### B4. 03-AgentLoopSpec_v2.0.md (35 matches)
Canonical SDLC loop Phase 1-7 specification. All about the coding agent loop, NOT delivery phases.

### B5. 04-MemorySchema_v2.0.md (1 match)
Only canonical boilerplate "7 phases".

### B6. 05-APIIntegration_v2.0.md (8 matches)
P0/P1 priority labels. One loop.phase log reference.

### B7. 06-Persona_Document_v3.0.md (13 matches)
Surveillance phased rollout Phase 1-3 (DIFFERENT from delivery phases — surveillance-specific rollout). SDLC 7-phase refs.

## SECTION C: Authoritative Phase Definition Chain

For restructuring, these are the files that DEFINE delivery phases (in authority order):
1. **16-AcceptanceCriteriaCatalog** — AC-PHASE-001 through AC-PHASE-008 (most authoritative)
2. **10-ProjectCharter** §17 + Appendix A (co-authoritative with AcceptanceCriteria)
3. **15-RTM** — Phase column traces requirements to phases
4. **00-BRD** — Phase 0-5 names (outlier, needs reconciliation)
5. **PROGRESS.md / CHECKLIST.md / StepPrompts.md** — Implementation tracking

## SECTION D: Impact Assessment for Restructuring

### HIGH IMPACT (delivery phase definitions)
- AcceptanceCriteria §5.12 + §12 Phase Gate Checklist
- Project Charter §17 + Milestones + Appendix A
- RTM Phase column
- BRD Phase 0-5 sections (needs name reconciliation)

### MEDIUM IMPACT (SDLC loop phase disambiguation)
- TDD deployment diagram Phase 1-4 (L1739-1758) — add "deployment phase" qualifier
- FSD FSD-CODE-001 through 007 — no change needed (SDLC loop)
- AgentLoopSpec — no change needed (SDLC loop)

### LOW IMPACT (priority levels, generic usage)
- SRS P0-P3 priority columns — no change
- PRD P0/P1 persona priorities — no change
- APIIntegration P0/P1 event priorities — no change
