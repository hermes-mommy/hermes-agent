# STEP: AGENTS.md v2.2 — Planner Verification Scaffold

## 1. What Was Done

Updated `AGENTS.md` from v2.1 (395 lines) to v2.2 (427 lines) by adding a mandatory planner verification scaffold rule. Eight precise insertions applied:

1. **§0 BLOCKING Rules**: Added 3 new `- NEVER` items (lines 44-46) requiring per-step scaffold, scaffold verification before accepting "done", and transparent violation recording.
2. **§1 Step 6**: Enhanced parent planner-read step with "verifies per-step scaffold compliance" (line 66).
3. **§2.5 NEW SECTION**: "Planner Verification Scaffold — Mandatory" with scaffold fields table (Expected Files, Forbidden Patterns, Required Commands, Evidence Requirements, Hard Rejection Criteria) and 7 enforcement rules (lines 104-127).
4. **§2.X Renumbering**: Cascade of 6 sections renumbered (§2.5→§2.6 through §2.10→§2.11).
5. **§3 Step 9**: Enhanced with "verify scaffold compliance" (line 194).
6. **§5 Anti-Pattern**: New "Planner Scaffold Violation" category (lines 239-241).
7. **§13 Version Table**: v2.2 row added (line 356).
8. **§14 Workflow Gates**: Planner gate bullet updated with scaffold language (line 412).

## 2. Files Changed

| File | Lines Before | Lines After | Action |
|---|---|---|---|
| `AGENTS.md` | 395 | 427 | Modified — 8 insertions |

No other files modified. No files created or deleted.

## 3. Validation Results

| Check | Command | Result |
|---|---|---|
| Diagnostics | `lsp_diagnostics AGENTS.md` | 0 errors, 0 warnings |
| BLOCKING rules count | grep `- NEVER` | 19 (was 16; +3) |
| Anti-pattern categories | grep `### ` in §5 | 8 (was 7; +1) |
| §2.X sequence | grep `### 2.` | 2.1–2.11 sequential, no gaps |
| Version table | grep `| 2.` | 4 rows (v2.2, v2.1, v2.0, v1.0) |
| Total lines | file read | 427 |

## 4. Evidence Artifacts

| Artifact | Path | Status |
|---|---|---|
| This verification | `docs/setup-evidence/agents-md-update-v4/verification.md` | COMPLETE |
| Auditor gate | `docs/setup-evidence/agents-md-update-v4/auditor-gate.md` | PASS |
| Research: evidence patterns | `docs/setup-evidence/agents-md-update-v4/research/evidence-scaffold-patterns.md` | COMPLETE (inline) |
| Research: external scaffold | `docs/setup-evidence/agents-md-update-v4/research/external-scaffold-quality-gates.md` | COMPLETE (28,676 bytes) |
| Research: insertion points | `docs/setup-evidence/agents-md-update-v4/research/agents-md-insertion-points.md` | COMPLETE (inline) |
| Research: governance risk | `docs/setup-evidence/agents-md-update-v4/research/governance-risk-review.md` | COMPLETE (21,501 bytes) |

## 5. Doc-Sync Impact

| Document | Impact | Status |
|---|---|---|
| `PROGRESS.md` | No update needed (AGENTS.md is governance, not phase progress) | N/A |
| `CHECKLIST.md` | No update needed | N/A |
| `docs/README.md` | No update needed | N/A |
| `adr/` | No ADR conflict — process rule, not architecture decision | N/A |

## 6. Boundary Compliance

| Boundary | Status |
|---|---|
| Persona drift | NONE — §0 identity/ persona wording untouched |
| Consent/safety | NONE — §2.1 Consent-Safety Mandate untouched |
| HARD STOP protocol | NONE — no HARD STOP wording modified |
| Surveillance boundary | NONE — §9 isolation untouched |
| Yandere ceiling | NONE — Y4/Y5/Y6 rules untouched |
| Safety-affecting domains | NONE — new rule is process/workflow only |

## 7. Rollback / Re-run Safety

- **Rollback**: Revert to v2.1 by removing the 8 insertions and restoring original §2.5–§2.10 numbering. No stateful changes.
- **Re-run**: Edit is idempotent; re-applying same insertions on v2.1 produces identical v2.2.
- **No DB, service, credential, or migration impact**.

## 8. Design Decisions / Caveats

| Decision | Rationale |
|---|---|
| §2.5 placement after §2.4 | Groups all planner-related rules sequentially (§2.3 Gate, §2.4 Parallelism, §2.5 Scaffold) |
| 6-section renumbering cascade | Clean sequential numbering; no cross-refs break (confirmed: zero `§2.\d` internal refs) |
| 3 BLOCKING items, not 2 or 4 | Matches user spec: scaffold required, verify done-claim, record violations |
| Anti-pattern in §5 after Operator-Process | Minimizes disruption to existing 7 categories |
| §1/§3 step enhancements inline | Avoids step renumbering across §1, §3, §10 |
| No scaffold.md files created | This rule defines the requirement; actual scaffold files are created per-step during implementation batches |

### Caveats

1. The scaffold rule is process-enforcement only — it does not define what constitutes "non-trivial". Parent judgment still applies.
2. The `scaffold.md` artifact type is new to the repo; existing batch plans (e.g., `batch-plan-011-015.md`) did not include per-step scaffolds. Future batches must comply.
3. Governance review identified 3 non-blocking NEEDS REVIEW findings (bypass auto-flag mechanism undefined, §11 "should" vs "must", §10 "trivial" scope undefined) — these are pre-existing v2.1 issues, not introduced by v2.2.

## 9. Auditor Gate

| Field | Value |
|---|---|
| Status | PASS |
| Auditor path | `docs/setup-evidence/agents-md-update-v4/auditor-gate.md` |
| Result | 22/22 checks PASS, 0 FAIL, 0 NEEDS REVIEW |

## 10. Security Scan

| Check | Result |
|---|---|
| Secrets in diff | NONE — no credentials, tokens, or keys |
| Type suppressions | NONE — no `as any`, `@ts-ignore`, `# type: ignore` |
| Empty catches | NONE |
| Raw memory/surveillance | NONE |
| Destructive operations | NONE |

## 11. Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| Scaffold format with 5 fields | PASS | §2.5 table at lines 110-116 |
| 7 enforcement rules | PASS | §2.5 numbered list at lines 120-126 |
| 3 new BLOCKING items | PASS | Lines 44-46 |
| §5 anti-pattern added | PASS | Lines 239-241 |
| Version bump v2.2 | PASS | Line 356 |
| No safety content weakened | PASS | Parent-verified all §0/§2.1/§9 wording intact |
| Renumbering correct | PASS | §2.1–§2.11 sequential |
| §1/§3/§14 enhancements | PASS | Lines 66, 194, 412 |

## 12. Footer

| Field | Value |
|---|---|
| Step | AGENTS.md v2.2 — Planner Verification Scaffold |
| Status | COMPLETE — parent verified, auditor PASS |
| Auditor gate | PASS |
| Changed files | 1 (`AGENTS.md`) |
| Lines | 395 → 427 (+32) |
| Diagnostics | 0 errors |
| Next action | Session complete |
