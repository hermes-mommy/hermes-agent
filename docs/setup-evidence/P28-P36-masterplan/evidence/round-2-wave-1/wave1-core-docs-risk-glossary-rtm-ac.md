---
title: "Wave 1 — Risk Register, Glossary, RTM, Acceptance Criteria — ADR-062/066/067 Disclaimers"
status: "Complete"
date: "2026-06-28"
agent: "Agent-3 (risk-register + glossary + RTM + acceptance-criteria)"
scope: "FIX 1-4 on 4 files only; no touch on BRD/PRD/FSD/prompt-pack/architecture/plans/adr-drafts"
---

# Wave 1 Evidence — Risk Register, Glossary, RTM, Acceptance Criteria

## What Was Done

Applied ADR-062/066/067 disclaimers and P32 reference updates to 4 P28-P36 masterplan docs:

1. `docs/risk-register.md`
2. `docs/glossary.md`
3. `docs/rtm-requirements-traceability-matrix.md`
4. `docs/acceptance-criteria.md`

---

## Files Changed

| # | File | Changes |
|---|---|---|
| 1 | `docs/risk-register.md` | FIX 1: ADR-062 disclaimer after R-005 entry. FIX 2: Consent dev-workflow footnote after R-006 entry. FIX 3: ADR-067 Y-level cap disclaimer in §9.4 critical notes. FIX 4: P32 references renamed in R-001 entry. |
| 2 | `docs/glossary.md` | FIX 1: ADR-062 disclaimer appended to HARD STOP glossary entry (§75) and cross-reference table (§148). FIX 2: Consent dev-workflow note appended to Consent Revocation entry (§68). |
| 3 | `docs/rtm-requirements-traceability-matrix.md` | FIX 1: ADR-062 disclaimer in RTM-018 description cell + boundary table row. FIX 2: Consent dev-workflow note in RTM-019 description cell + boundary table row. FIX 4: P32 references renamed in phase table, trace chains, acceptance checklist, coverage matrix, boundary table. |
| 4 | `docs/acceptance-criteria.md` | FIX 1: ADR-062 blockquote after AC-CC-001 and AC-P31-004 entries. FIX 2: Consent dev-workflow footnote after AC-CC-002 entry. FIX 3: ADR-067 blockquote after AC-CC-005 entry and §5.3 critical notes. FIX 4: P32 references renamed in phase table and §2.5 section header. |

---

## Fix 1 — HARD STOP ADR-062 Annotations

### Locations Annotated

| File | Entry | Annotation |
|---|---|---|
| risk-register.md | R-005 (line ~205) | `> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.` |
| glossary.md | §75 HARD STOP definition | Appended to description cell: `**ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.` + source `ADR-062` added |
| glossary.md | §148 Cross-reference | Appended: `— ADR-062 disclaimer applies (dev-workflow only)` |
| rtm-requirements-traceability-matrix.md | RTM-018 (line ~108) | Appended to description: `(**ADR-062 Disclaimer**: applies to dev-workflow agent ONLY; Hermes runtime can bypass per ADR-062)` |
| rtm-requirements-traceability-matrix.md | Boundary table (line ~272) | Appended: `— **ADR-062 Disclaimer**: dev-workflow agent ONLY; Hermes runtime can bypass per ADR-062` |
| acceptance-criteria.md | AC-CC-001 (line ~539) | Blockquote after entry: `> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.` |
| acceptance-criteria.md | AC-P31-004 (line ~282) | Blockquote after entry: `> **ADR-062 Disclaimer**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime (P24 fork) can bypass per ADR-062.` |

---

## Fix 2 — Consent Revocation Annotations

### Locations Annotated

| File | Entry | Annotation |
|---|---|---|
| risk-register.md | R-006 (line ~222) | `> Consent revocation applies to dev-workflow events only. Hermes runtime exempt per ADR-062/066.` |
| glossary.md | §68 Consent Revocation definition | Appended: `(dev workflow only) > Consent revocation applies to dev-workflow events only. Hermes runtime exempt per ADR-062/066.` + source `ADR-062/066` added |
| rtm-requirements-traceability-matrix.md | RTM-019 (line ~109) | Appended: `(dev workflow only; Hermes runtime exempt per ADR-062/066)` |
| rtm-requirements-traceability-matrix.md | Boundary table (line ~273) | Appended: `— dev workflow only; Hermes runtime exempt per ADR-062/066` |
| acceptance-criteria.md | AC-CC-002 (line ~552) | Blockquote after entry: `> Consent revocation applies to dev-workflow events only. Hermes runtime exempt per ADR-062/066.` |

---

## Fix 3 — Y-Level Cap ADR-067 Annotations

### Locations Annotated

| File | Entry | Annotation |
|---|---|---|
| risk-register.md | §9.4 Critical Notes #5 (line ~540) | `> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.` |
| acceptance-criteria.md | AC-CC-005 (line ~591) | Blockquote after entry: `> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.` |
| acceptance-criteria.md | §5.3 Critical Notes #5 (line ~656) | `> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.` |

---

## Fix 4 — P32 Reference Updates

### Changes Made

| File | Location | Old Text | New Text |
|---|---|---|---|
| risk-register.md | R-001 Description (line ~134) | `P24 Fork Integration` | `External Presence & Tools` |
| risk-register.md | R-001 Likelihood (line ~135) | `fork-agnostic` | `P24 native fork` |
| rtm-requirements-traceability-matrix.md | Phase table (line ~64) | `P24 Fork Integration Boundary` | `External Presence & Tools` |
| rtm-requirements-traceability-matrix.md | Note (line ~70) | `fork-agnostic` | `P24 native fork` |
| rtm-requirements-traceability-matrix.md | Trace chain (line ~190) | `P24 fork-agnostic` | `P24 native fork` |
| rtm-requirements-traceability-matrix.md | Acceptance checklist (line ~245) | `fork-agnostic` | `P24 native fork` |
| rtm-requirements-traceability-matrix.md | Coverage matrix (line ~258) | `P32 P24 Fork Integr.` | `P32 External Presence` |
| rtm-requirements-traceability-matrix.md | Boundary table (line ~279) | `Fork-agnostic` | `P24 native fork` |
| acceptance-criteria.md | Phase table (line ~37) | `P24 Fork Integration` | `External Presence & Tools` |
| acceptance-criteria.md | §2.5 header (line ~286) | `P32 — P24 Fork Integration` | `P32 — External Presence & Tools` |
| acceptance-criteria.md | AC-P32-001 Notes (line ~301) | `fork-agnostic` | `P24 native fork` |

---

## Validation

- All 4 files: grep confirms zero remaining `fork-agnostic` or `P24 Fork Integration` references
- All 4 files: ADR-062 disclaimers present on HARD STOP entries
- All 4 files: Consent dev-workflow annotations present on consent entries
- risk-register + acceptance-criteria: ADR-067 Y-level annotations present
- No files outside scope (BRD/PRD/FSD/prompt-pack/architecture/plans/adr-drafts) were touched

---

## Design Decisions / Caveats

1. **R-005 already had extensive ADR-062 narrative** (Round-2 fix-log). Added canonical blockquote format for consistency with other docs.
2. **R-006 already had extensive ADR-062/066 narrative**. Added canonical footnote format for consistency.
3. **Table entries** (glossary, RTM): annotation appended to description cell since blockquotes between rows break markdown tables.
4. **Non-table entries** (risk-register R-005/R-006, acceptance-criteria AC-CC-001/AC-P31-004/AC-CC-002/AC-CC-005): canonical blockquote added immediately after entry.
5. **P32 rename**: `"P24 Fork Integration" → "External Presence & Tools"` and `"fork-agnostic" → "P24 native fork"` applied consistently across all 4 files.
6. **RTM-026 description kept "fork-integration"** in its cell (opt-in deferral text) but appended `(P24 native fork)` annotation per FIX 4 pattern.

---

## Acceptance Criteria

| Criterion | Status |
|---|---|
| All 4 files annotated with ADR-062 disclaimer on HARD STOP entries | PASS |
| Consent revocation entries annotated "(dev workflow only)" | PASS |
| Y-level cap entries annotated with ADR-067 | PASS |
| P32 references renamed | PASS |
| No files outside 4-file scope touched | PASS |

---

> **STRICTLY PRIVATE & CONFIDENTIAL** — Project Guinevere. This evidence file is part of the P28-P36 masterplan wave-1 execution evidence.
