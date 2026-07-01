# P4 / Phase-4 Naming Collision Report

> **Researcher**: Guinevere (sub-agent)
> **Date**: 2026-06-25
> **Scope**: Two distinct "P4" entities sharing the same prefix, causing ambiguous references throughout the codebase.

---

## §1 Entity Definitions

| Entity | Canonical Path | Content | Step Prefix |
|--------|---------------|---------|-------------|
| **P4 Persona Engine** | `docs/setup-evidence/P4/` | Mood FSM, yandere protocol, punishment/reward, drift detection, safe-mode, rituals. Runtime code in `src/persona/`, tests in `tests/persona/`. | `P4-001` through `P4-023` (STEP-P4-NNN subdirs) |
| **Phase-4 ADR-035 Hermes MCP Tools Migration** | `docs/setup-evidence/phase-4/` | Hermes native MCP servers (web/filesystem/terminal/git/fetch), auth overlay plugin, budget enforcement, hybrid tool safety guards, FastMCP bridge. | `P4-001-verification.md` through `P4-008-verification.md` (flat verification files) |

---

## §2 File Listing: Side-by-Side

### Whole-directory comparison

| File | `docs/setup-evidence/P4/` | `docs/setup-evidence/phase-4/` |
|------|--------------------------|-------------------------------|
| Plan | `batch-plan-001-023.md` | `batch-plan-phase-4.md` |
| Top-level verification | — | `verification.md` |
| Auditor gate | — | `auditor-gate.md` |
| Compliance | `audit-report-p4-code-quality.md` | `AUDIT-adr035-compliance.md`, `AUDIT-adr035-compliance-v1.1.md` |
| Security | — | `AUDIT-security.md`, `AUDIT-security-v1.1.md` |
| Audit sub-reports | — | `audit-auth-overlay.md`, `audit-budget-guards.md`, `audit-config-fastmcp-e2e.md`, `audit-startup-audit.md` |
| Known issues | `KNOWN-ISSUES.md` | — |
| Patch verification | `patch-h02-h03-verification.md` | — |
| Planner gate | — | `planner-gate-phase-4-execution.md` |
| Step dirs/files | `STEP-P4-001/` through `STEP-P4-023/` (23 subdirs, each containing `verification.md`) | `P4-001-verification.md` through `P4-008-verification.md` (8 flat files) |

### Overlapping P4-NNN naming prefix — the critical collision

Both directories use `P4-NNN` as a step identifier **but for completely different work items**. The identical prefix creates a direct naming collision:

| Label | P4 Persona Engine | Phase-4 (ADR-035 Hermes MCP) |
|-------|------------------|-------------------------------|
| P4-001 | Mood FSM Engine (`docs/setup-evidence/P4/STEP-P4-001/verification.md`, line 1: *"Verification Report: P4-001 — Mood FSM Engine"*) | Hermes MCP Config Baseline (`docs/setup-evidence/phase-4/P4-001-verification.md`, line 1: *"P4-001 Verification — Hermes MCP Config Baseline"*) |
| P4-002 | Mood State Persistence (`docs/setup-evidence/P4/STEP-P4-002/verification.md`, line 1: *"Verification Report: P4-002 — Mood State Persistence"*) | Auth Overlay Plugin (`docs/setup-evidence/phase-4/P4-002-verification.md`, line 1: *"P4-002 Verification — Auth Overlay Plugin"*) |
| P4-003 | Transition Rules with Cooldowns (`docs/setup-evidence/P4/STEP-P4-003/verification.md`) | Budget Enforcement Hook (`docs/setup-evidence/phase-4/P4-003-verification.md`) |
| P4-004 | Yandere FSM (`docs/setup-evidence/P4/STEP-P4-004/verification.md`) | Hybrid Tool Safety Guards (`docs/setup-evidence/phase-4/P4-004-verification.md`) |
| P4-005 | Punishment Ladder L1-L5 (`docs/setup-evidence/P4/STEP-P4-005/verification.md`) | FastMCP Custom Bridge (`docs/setup-evidence/phase-4/P4-005-verification.md`, line 1: *"P4-005 Verification — FastMCP Custom Bridge"*) |
| P4-006 | Reward Tiers T1-T5 (`docs/setup-evidence/P4/STEP-P4-006/verification.md`) | Plugin Startup Gate (`docs/setup-evidence/phase-4/P4-006-verification.md`) |
| P4-007 | Streak Tracking (`docs/setup-evidence/P4/STEP-P4-007/verification.md`) | Security Audit Suite (`docs/setup-evidence/phase-4/P4-007-verification.md`) |
| P4-008 | Ritual Scheduler (`docs/setup-evidence/P4/STEP-P4-008/verification.md`) | E2E Integration Test Suite (`docs/setup-evidence/phase-4/P4-008-verification.md`, line 1: *"P4-008 Verification — E2E integration test suite for Phase 4 MCP Tools"*) |
| P4-009 | Morning Ritual — Persona engine only | — |
| P4-010 | Midday Ritual — Persona engine only | — |
| P4-011 | Afternoon Ritual — Persona engine only | — |
| P4-012 | Evening Ritual — Persona engine only | — |
| P4-013 | Midnight Self-evaluation — Persona engine only | — |
| P4-014 | Drift Detection — Persona engine only | — |
| P4-015 | Drift Correction — Persona engine only | — |
| P4-016 | Safe-mode Trigger — Persona engine only | — |
| P4-017 | HARD STOP Test — Persona engine only | — |
| P4-018 | D0-D4 Detection Test — Persona engine only | — |
| P4-019 | Yandere Cap Test — Persona engine only | — |
| P4-020 | Consent Revocation Test — Persona engine only | — |
| P4-021 | Punishment Overflow Test — Persona engine only | — |
| P4-022 | Distress Protocol D0-D4 Test — Persona engine only | — |
| P4-023 | Persona E2E Test — Persona engine only | — |

---

## §3 Plain-Text Header Evidence

### phase-4 files (ADR-035 Hermes MCP):

**`docs/setup-evidence/phase-4/batch-plan-phase-4.md` line 1:**
> `# Batch Plan — Phase 4: MCP + Tools Migration`
> `> **Scope**: ADR-035 Phase 4 (Pillar 4 — MCP + Tools)`

**`docs/setup-evidence/phase-4/AUDIT-adr035-compliance.md` line 1:**
> `# ADR-035 Compliance Audit — Phase 4 Batch Plan`
> `> **Audit Target**: docs/setup-evidence/phase-4/batch-plan-phase-4.md`
> `> **Source of Truth**: adr/ADR-035-hermes-migration.md v1.3 (Accepted)`

**`docs/setup-evidence/phase-4/verification.md` line 1:**
> `# Phase 4 Master Verification Status`
> `> **ADR-035 Phase 4 — MCP Tools Migration**`

**`docs/setup-evidence/phase-4/P4-001-verification.md` line 1:**
> `# P4-001 Verification — Hermes MCP Config Baseline`

**`docs/setup-evidence/phase-4/P4-005-verification.md` line 1:**
> `# P4-005 Verification — FastMCP Custom Bridge`

**`docs/setup-evidence/phase-4/P4-008-verification.md` line 1:**
> `# P4-008 Verification — E2E integration test suite for Phase 4 MCP Tools`

### P4 Persona Engine files:

**`docs/setup-evidence/P4/batch-plan-001-023.md` line 1:**
> `# Batch Plan: P4 Persona Engine (STEP-P4-001 to STEP-P4-023)`
> `> **Phase**: 4 — Persona Engine`

**`docs/setup-evidence/P4/STEP-P4-001/verification.md` line 1:**
> `# Verification Report: P4-001 — Mood FSM Engine`

**`docs/setup-evidence/P4/STEP-P4-002/verification.md` line 1:**
> `# Verification Report: P4-002 — Mood State Persistence`

**`docs/setup-evidence/P4/STEP-P4-023/verification.md` line 1:**
> `# Verification Report: P4-023 — Distress Protocol E2E Test`

**`docs/setup-evidence/P4/KNOWN-ISSUES.md` line 1:**
> `# P4 Persona Engine — Known Issues and Gap Registry`

---

## §4 Ambiguous "P4" References in Tracking Files

### CHECKLIST.md

| Line | Text | Refers to | Ambiguity Risk |
|------|------|-----------|----------------|
| 34 | `P4    | $1          | $18        | $12             |` | Persona Engine (cost table) | LOW — P4 in phase-summary table |
| 365 | `- [ ] No blockers for Phase 4` | P3 memory phase (inside Phase 3 checklist) | **MODERATE** — bare "Phase 4" after Phase 3 section; reader could associate with either entity. Context says it's blocking check for P4 Persona Engine (the next section). |
| 368 | `## 6. Phase 4: Persona Engine Verification` | Persona Engine | LOW — explicitly says "Persona Engine" |
| 385-407 | `P4-001` through `P4-023` checkboxes | Persona Engine | LOW — in explicit Persona Engine section |
| 448 | `audit-reports/P4/P4-FINAL-AUDIT/FINAL-SYNTHESIS.md` | Persona Engine | LOW — path resolves to Persona Engine audit |
| 475 | `P5-007: Phase 4 Execute` | **NEITHER** — refers to SDLC loop phase "Execute" which is part of P5 (Agent Loop), numbered differently | LOW — different numbering system |
| 1668 | `P1 + P4: LLM + Persona` | Persona Engine | LOW — explicit "Persona" |
| 1673 | `P2 + P4: Discord + Persona` | Persona Engine | LOW — explicit "Persona" |
| 1688 | `P4 + P7: Persona + Surveillance` | Persona Engine | LOW — explicit "Persona" |
| 1744-1751 | `P4-017/P4-019` etc. in AC-SAFE checks | Persona Engine | LOW — in safety criteria section, references explicit P4-NNN from Persona Engine |
| 1908 | `P4 resolved with 1449 tests` | Persona Engine | LOW — 1449 tests matches Persona Engine test count |

### PROGRESS.md

| Line | Text | Refers to | Ambiguity Risk |
|------|------|-----------|----------------|
| 32 | `P4 | Persona Engine | 23/23 | $1` | Persona Engine | LOW — explicit "Persona Engine" |
| 186-208 | `P4-001` through `P4-023` step list | Persona Engine | LOW — in P4 section header |
| 221 | `P5-007 Phase 4: Execute` | SDLC loop phase | LOW — different numbering |
| 1062 | `P4 Persona | $1 | $18` | Persona Engine | LOW — explicit "Persona" |
| 1091 | `P4 || P5` parallelism | Persona Engine | LOW — phase dependencies |
| 1093 | `P4 requires P3` | Persona Engine | LOW — matches dependency chain |
| 1113 | `P4 | 23 | 2-4 | 38 | 76` | Persona Engine | LOW — cost table |

### docs/setup-evidence/hermes-migration/ files (Hermes migration context)

| File:Line | Text | Refers to | Ambiguity Risk |
|-----------|------|-----------|----------------|
| `audit-consistency.md:178` | `P4=5-7d` | **Phase-4 ADR-035** | MODERATE — in Hermes migration context but bare "P4" appears in a duration table without "phase-4" qualifier |
| `audit-consistency.md:179` | `P4=3-4d` | **Phase-4 ADR-035** | Same |
| `audit-safety.md:99` | `Phase 4 | ~1199 | P4-T1..P4-T5` | **Phase-4 ADR-035** | LOW — in explicit Hermes security audit context, uses `P4-T*` prefix (persona engine uses `P4-NNN`) |
| `audit-completeness.md:109` | `4 | P4-T1..P4-T5` | **Phase-4 ADR-035** | LOW — audit completeness context |
| `batch-plan-migration.md:312` | `R-P4-OVER-01` | **Phase-4 ADR-035** | LOW — uses R-P4-OVER prefix unique to Hermes migration |
| `phase-4-mcp.md:295-299` | `P4-T1` through `P4-T5` test table | **Phase-4 ADR-035** | LOW — explicit MCP context |
| `phase-5-skills.md:1` | `# Phase 5: Skills + Persona` | **This refers to Hermes migration Phase 5**, which covers persona features **unrelated** to the P4 Persona Engine | **HIGH CONFUSION** — This is Hermes Phase 5 (migration of persona features to Hermes plugin) which is visually adjacent to "P4 = Persona Engine" but is actually a **different** Phase 5 in a different phase numbering system (ADR-035 Hermes phases vs. P0-P8 project phases). |

### docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md

| Line | Text | Refers to | Ambiguity Risk |
|------|------|-----------|----------------|
| 243 | `Phase 4 Surveillance & Financial MVP` | **NEITHER** — this is a *third* unrelated Phase 4: the Surveillance & Financial MVP phase in the post-restructure numbering. | **HIGH** — this creates a *third* entity called "Phase 4" that is neither P4 Persona Engine nor phase-4 ADR-035 MCP migration. It is actually the P7/P9 scope in the P0-P22 numbering. |

### docs/setup-evidence/p14-expansion/legacy/P14-013.md

| Line | Text | Refers to | Ambiguity Risk |
|------|------|-----------|----------------|
| 9 | `P4 (Persona Engine)` | Persona Engine | LOW — explicitly parenthesized |
| 58 | `P4 persona engine modules exist` | Persona Engine | LOW — explicit |
| 62 | `P4 YandereEngine importable` | Persona Engine | LOW — explicit |
| 747 | `YandereEngine (P4)` | Persona Engine | LOW — explicit |
| 749 | `P4 safe_mode module` | Persona Engine | LOW — explicit |

---

## §5 Cross-Bleed Analysis: Has One Entity's PASS Been Credited to the Other?

### Direct cross-bleed: NOT FOUND

After exhaustive grep of all relevant files:

- **P4 Persona Engine files** (`docs/setup-evidence/P4/`, `audit-reports/P4/`) contain zero references to "ADR-035", "Hermes MCP migration", "auth overlay", or "FastMCP" in their audit/synthesis documents. They correctly scope their PASS verdict to the Persona Engine domain.

- **Phase-4 ADR-035 files** (`docs/setup-evidence/phase-4/`, `docs/setup-evidence/hermes-migration/phase-4-mcp.md`) contain zero references to "Persona Engine", "mood FSM", "yandere FSM", or "punishment ladder". They correctly scope their PASS to the MCP Tools Migration domain.

- **CHECKLIST.md** section "## 6. Phase 4: Persona Engine Verification" (line 368) correctly disambiguates by appending "Persona Engine Verification". Its P4-NNN step checklist (lines 385-407) is unambiguously Persona Engine.

- **PROGRESS.md** row (line 32) explicitly says `P4 | Persona Engine | ✅ | 23/23`.

### No status-bleed confirmed

Neither entity claims the other's PASS as its own. The project's two primary tracking files (CHECKLIST.md, PROGRESS.md) consistently label P4 as "Persona Engine", keeping it distinct from the ADR-035 Hermes Migration phase numbering.

### Downstream docs reference P4 correctly

Hermes migration documents (`docs/setup-evidence/hermes-migration/phase-7*`, `audit-consistency.md`, `audit-safety.md`, `batch-plan-migration.md`) use `P4-T*` (with dash-T suffix) for their test IDs, which is visually distinguishable from the Persona Engine's `P4-NNN` format. No false attribution found.

---

## §6 Third Conflicting "Phase 4" Entity

The acceptance criteria catalog (`docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md`, line 243) defines a **third** Phase 4:

> **AC-PHASE-005** | Phase 4 Surveillance & Financial MVP must pass surveillance governance, Tasker/no-scraping finance, FinOps monthly report, USD 30 cap, and safety confrontation block criteria.

This corresponds to the *post-restructure* phase numbering (P0-P22) where Phase 1 = LLM, Phase 2 = Persona & Memory, Phase 3 = SDLC, Phase 4 = Surveillance & Financial — which differs from **both** the P0-P8 project phases (where P4 = Persona Engine) and the ADR-035 Hermes phases (where Phase 4 = MCP Tools).

This third entity is not actively used in tracking files but exists as a source of confusion for anyone reading the acceptance criteria catalog without context.

---

## §7 Collision Risk Assessment

| Risk | Severity | Details |
|------|----------|---------|
| Searching/finding wrong files | MODERATE | A search for "P4-001" returns hits from both `P4/STEP-P4-001/verification.md` (Mood FSM Engine) and `phase-4/P4-001-verification.md` (Hermes MCP Config Baseline). A reader must check file path or header to disambiguate. |
| Grep false positives | MODERATE | `grep -r "P4-001"` returns both Persona Engine and Hermes MCP results. Requires `-l` + manual inspection of paths. |
| PR/review confusion | MODERATE | A reviewer asked to check "P4-005 verification" needs to know which P4: "punishment ladder" or "FastMCP custom bridge"? The response depends on path. |
| Status-bleed | NONE | No evidence that any document credits one entity's PASS to the other. |
| Third entity "Phase 4 Surveillance & Financial" | LOW | Exists only in acceptance criteria catalog, not actively cross-referenced. |
| Hermes Phase 5 = Persona (via skills) | LOW CONFUSION | `hermes-migration/phase-5-skills.md` covers persona features but is explicitly in the Hermes migration phase numbering, not the P0-P8 numbering. A skimmer might conflate "Hermes Phase 5 persona" with "P4 Persona Engine." |

---

## §8 COLLISION SEVERITY: MODERATE

**Verdict: MODERATE** — The collision is real and creates concrete grep/review confusion, but has NOT caused any documented status-bleed (one phase's PASS credited to the other). Both entities are correctly scoped in their respective files. The primary risk is human error during cross-referencing and automated search results.

### Recommended mitigations

1. **Do not rename retroactively** — both directory trees are stable and referenced by CHECKLIST.md/PROGRESS.md. Renaming would create more stale-link risk than it solves.
2. **Always disambiguate in prose**: use "P4 Persona Engine" (not bare "P4") when the Persona Engine is meant, and "phase-4 ADR-035 MCP migration" (not bare "phase 4") when the Hermes migration is meant.
3. **Document this collision** in any master doc index or onboarding guide (this file serves that purpose).
4. **The P4 audit currently running** (new audit in `docs/setup-evidence/legacy-audit/P4/`) must be scoped to **P4 Persona Engine** only and disambiguated in all its reports.
