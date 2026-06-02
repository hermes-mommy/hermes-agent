# Research: Auditor Report Patterns (for P1 Replication)

| Field | Value |
|-------|-------|
| **Research Agent** | Explore |
| **Date** | 2026-05-31 |
| **Sources** | audit-reports/P0/STEP-P0-{000..028}/ |
| **Verdict** | 15-section canonical schema; P0-006 best template |

---

## Auditor Report Path Convention

```
audit-reports/P{N}/STEP-P{N}-{XXX}/step-p{N}-{XXX}-auditor-report.md
```

## Canonical 15-Section Schema (P0-006 reference)

1. **Header** — Step, Auditor, Date, Type, Mode, Verdict
2. **Scope & Method** — Files read + verification methods
3. **DoD Verification Matrix** — Every DoD item in PASS/FAIL table
4. **Evidence File Inventory** — All expected evidence: existence + content validity
5. **Live VPS State Verification** → **P1: replace with Local Environment Verification** (LSP, glob, cross-ref)
6. **Tracker Sync Verification** — PROGRESS.md, CHECKLIST.md, StepPrompts.md
7. **Acceptance Criteria Cross-Check** — AC items from StepPrompts.md
8. **ADR Compliance** — Referenced ADRs in PASS/FAIL table
9. **Secrets & Safety Scan** — grep patterns for tokens/keys/passwords
10. **Boundary Compliance** — Persona/Surveillance/Memory/Consent/HARD STOP/Yandere
11. **Introduced vs Pre-Existing Issues** — Type/Description/Severity table
12. **Findings** — Blocking vs Non-Blocking
13. **Rollback Safety** — Reversible procedure documented
14. **Verdict** — Visual box: PASS(✅) / NEEDS REVIEW(⚠️) / FAIL(❌)
15. **Footer** — Source task, date, auditor, method, evidence root, report path

## Verdict Format

| Verdict | Symbol | When |
|---------|--------|------|
| PASS | ✅ | All DoD satisfied, no blocking findings |
| PASS (non-blocking) | ✅ + notes | All DoD pass, minor findings documented |
| PASS (re-audit) | ✅ after ⚠️ | Initial NEEDS REVIEW, issues fixed, re-verified |
| NEEDS REVIEW | ⚠️ | Findings exist that should be resolved |
| FAIL | ❌ | Step cannot be marked complete |

## Research Wave Specialists (Pre-Implementation)

- `internal-context-report.md` — Internal docs, ADRs, trackers analysis
- `external-<topic>-report.md` — Librarian research on external tools
- `evidence-pattern-report.md` — Prior evidence pattern analysis

## P1-Specific Adaptations

- **No VPS live SSH** → LSP diagnostics + file glob + cross-reference verification
- **No Aizanta co-location** section (P1 = software layer)
- **Evidence paths**: `docs/setup-evidence/P1/STEP-P1-{XXX}/`
- **DoD source**: StepPrompts.md lines 3221-3418

## Best Template: P0-006

Use `audit-reports/P0/STEP-P0-006/step-p0-006-auditor-report.md` (476 lines) as structural template. Most comprehensive example with all 15 sections.

| Field | Value |
|-------|-------|
| **Source** | bg_6ee5cf22 — Auditor report patterns |
| **File** | research-reports/P1/auditor-report-patterns.md |