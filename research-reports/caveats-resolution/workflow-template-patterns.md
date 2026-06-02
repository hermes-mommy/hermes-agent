# Workflow Template Pattern Extraction — P1/P2 Batch-Plan & Evidence Audit

| Field | Value |
|---|---|
| **Task** | Audit proven Guinevere batch-plan/evidence files for canonical workflow template content |
| **Date** | 2026-06-01 |
| **Implementer** | Sisyphus-Junior / Guinevere |
| **Files Audited** | 6 batch plans (P1: 004-005, 006-007, 017-019; P2: 001-003, 004-006, 007-009) + 4 evidence files (P1-001, P2-001, migration-9router, p2-preconditions-resolved) |
| **Evidence Schema Verified** | P1-007-009 §13 — 12-section evidence schema explicitly used in all evidence files |
| **Output Path** | `research-reports/caveats-resolution/workflow-template-patterns.md` |

---

## Summary

This report identifies **21 required template sections** across 4 document layers (Phase/Batch Plan → Step Plan → Evidence File → Auditor Report), with exact section names, structs, wording patterns, and reference file locations to derive the canonical `docs/workflow/opencode-master-template-v3.md`.

---

## 1. ANALYZE-MODE

**Source Files**:
- `P2/batch-plan-001-003.md` §1 "Task Overview" — ANALYZE-MODE is implicit: parent reads research, reads known state, reads collision scans.
- `P2/batch-plan-004-006.md` §4 "Resolved Decisions Summary" — Explicit decision resolution after research analysis.
- `P2/batch-plan-007-009.md` §1 "Source Inputs Parent-Read" + §2 "Current State" + §3 "Binding Decisions".

**Required Sections** in analyze mode:
```
## Source Inputs Parent-Read
| Source | Use |
|---|---|

## Current State
- P2 status before: X/Y complete
- Total project status: Z/257 (W%)
- Known state table (exact values: app IDs, URLs, paths, versions)
- Live Discord/VPS state from research

## Binding Decisions for This Batch
- Decision 1: Value
- Decision 2: Value
- Authority source references
```

**Sections Found** (template-ready wording pattern):
- *Source Inputs*: Table with two columns — `# | Report | Key Findings Used` — each row has report path and 1-3 bullet findings.
- *Current State*: Bullet list of verified facts with exact values (IDs, paths, versions).
- *Binding Decisions*: Numbered list of decisions with authority source (DiscordUXSpec, StepPrompts, user directive).

**Reference**:
- P2/batch-plan-001-003.md lines 34-66: "Research Inputs (Cited by Path)" + "Known State (Exact Values)"
- P2/batch-plan-007-009.md lines 17-47: "Source Inputs Parent-Read" + "Current State" + "Binding Decisions"

---

## 2. SUPER UNLIMITED RESEARCH WAVE

**Source Files**:
- `P2/batch-plan-001-003.md` §2 "Research Inputs" — 6 research reports cited.
- `P2/batch-plan-004-006.md` Footer — "Research reports used: 6".
- `P2/batch-plan-007-009.md` §1 — 9 sources including research, evidence, specs, runbooks.
- `P1/batch-plan-004-005.md` — Research wave is implicit; plan references research reports in Gotchas & Edge Cases (§8).
- `P1/batch-plan-017-019.md` — No explicit research wave section; assumes parent pre-read.

**Template Pattern**:
```
## Research Inputs (Cited by Path)

All reports were read and synthesized by the parent before writing this plan:

| # | Report | Key Findings Used |
|---|--------|------------------|
| 1 | `research-reports/{PHASE}/{topic}.md` | Finding 1, Finding 2 |
```

**Rules Extracted**:
1. Research is always **complete before planner gate starts** (P2/batch-plan-001-003.md L34).
2. Research report paths are absolute relative paths from repo root.
3. "Key Findings Used" must list only findings that materially changed the plan — not a summary of the research.
4. Research wave runs in **parallel background** with unlimited sub-agents (AGENTS.md §2).
5. Reports must be file-based per AGENTS.md §9.
6. 5+ reports is typical for a 3-step batch; P2-007-009 had 9.

---

## 3. PLANNER GATE

**Source Files**:
- `P2/batch-plan-001-003.md` — Entire document is a planner gate output.
- `P2/batch-plan-004-006.md` — §4 "Resolved Decisions Summary" shows planner decision-making.
- `P1/batch-plan-017-019.md` §1 "Executive Summary" — planner-level scope framing.

**Template Structure** (from P2/batch-plan-004-006.md pattern):
```
## {N}. Resolved Decisions Summary

### {N}.1 Decision Category
| Decision | Value |
|---|---|
| Target | Value |
| Source authority | Ref |
| Overrides | Sources being overridden |

### {N}.2 Another Decision Category
...
```

**Planner Gate Required Elements** (from P2/batch-plan-007-009.md §3):
1. **ID Source Rule**: Which file provides canonical IDs.
2. **Permission Strategy**: Exact policy decisions (deny/allow mapping).
3. **Limitation Acknowledgment**: What the platform cannot enforce.
4. **Authority Priority**: Which docs win when they conflict.
5. **Go/No-Go Criteria**: Pre-conditions for implementation to start.

**Reference**: P2/batch-plan-004-006.md lines 112-184 — 3 resolved decisions (server name, category names, channel names). P2/batch-plan-007-009.md lines 48-96 — 5 binding decisions.

---

## 4. COLLISION SCAN

**Source Files**:
- `P1/batch-plan-004-005.md` §10 "Resource/Collision Scan" — 290 lines of collision analysis.
- `P1/batch-plan-006-007.md` §11 "Resource/Collision Scan" — ports, filesystem paths, packages, shared writers.
- `P1/batch-plan-017-019.md` §6 "Collision Scan" — focused table of shared writers + verdict.
- `P2/batch-plan-001-003.md` §4 "Collision Scan & Shared Writers" — two tables: Files to CREATE, Files to MODIFY.
- `P2/batch-plan-004-006.md` §3 "Collision Scan" — table with 6 collision types.
- `P2/batch-plan-007-009.md` §8 "Collision Scan" — table with 10 rows.

**Template Sections** (merge of all patterns):
```
## {N}. Collision Scan

### Files to CREATE (zero collision)
| File | Owner | Step |

### Files to MODIFY (parent-owned, sequenced)
| File | Change | Owner |

### Shared Writers Analysis
| File | Written By | Collision? | Resolution |

### Ports / Services / Resources
| Resource | Step | Action | Collision Risk |

### Collision Verdict
✅ CLEAR — No shared writers. All created files are independent.
(or)
⚠️ COLLISION — {description of conflict and mitigation}
```

**Wording Pattern from P2/batch-plan-001-003.md lines 91-96**:
```markdown
### Collision Verdict

✅ **CLEAR** — No shared writers. All created files are independent.
PROGRESS/CHECKLIST are parent-owned and sequenced after all N steps pass audit.
No other agent is writing to {path}.
```

**Collision Types** (from P2/batch-plan-004-006.md line 105):
1. Same source file — one owner
2. Shared docs — parent-only
3. Shared config — one owner
4. Shared test fixtures — one owner
5. Safety boundary docs — parent-only
6. Aizanta isolation — must not touch

---

## 5. IMPLEMENTATION

**Source Files**:
- `P1/batch-plan-004-005.md` §1 "Master Todo Per Step" — detailed delegation tables.
- `P1/batch-plan-006-007.md` §2 "Master Todo Per Step" — with dependency column added.
- `P1/batch-plan-017-019.md` §3-5 — per-step todo breakdown with Hazard/Field tables.
- `P2/batch-plan-001-003.md` §5-7 — per-step evidence+code+verify.
- `P2/batch-plan-004-006.md` §6-8 — detailed code blocks per implementation step.
- `P2/batch-plan-007-009.md` §10 "Implementation Design" — design constraints + code architecture.

**Template Pattern** (4 sub-types):

### Type A: Master Todo Table (batch-plan-004-005 pattern)
```
| # | Todo | Delegation | Evidence Path |
|---|---|---|---|
| T{X}-01 | Action verb + object | sub-agent type | `evidence/path` |
```
With dependency column added in later plans:
```
| Depends On |
|---|
| T{X}-00 |
```

### Type B: Per-Todo Hazard Table (batch-plan-017-019 pattern)
```
### T{X}-0{N}: Todo Name

| Field | Detail |
|---|---|
| File(s) created | paths |
| Implementation | technical description |
| Dependencies | todo references |
| Risk | Low/Medium/High |
| Effort | ~XXmin |
| Rollback | command |
```

### Type C: Code Blocks (batch-plan-004-006 pattern)
Inline Python/bash code under each step heading, showing exact implementation logic, async patterns, error handling, idempotency guards.

### Type D: Implementation Design (batch-plan-007-009 pattern)
```
### {N}.{M} `module.py`
Responsibilities:
- Load X from Y
- Define Z
- Discover A at runtime
- Apply B idempotently
- Verify C

Design constraints:
- No token values in logs
- No hardcoded IDs
- No type bypasses
```

**Reference**: P2/batch-plan-004-006.md lines 229-653 — full implementation code for 3 steps.

---

## 6. IMPLEMENTATION RULES

**Source Files**: 
- `P2/batch-plan-001-003.md` §9 "Security Constraints" — 8 token rules.
- `P2/batch-plan-007-009.md` §11 "Token Security Rules" — 7 rules.
- All batch plans have implicit rules: no `Any`, no `# type: ignore`, no empty catch.

**Template Pattern**:
```
## {N}. Implementation Rules

### Code Quality
- No `as any`, `# type: ignore`, `@ts-ignore`
- No empty `except:` / `catch`
- Use typed models (Pydantic)
- Fail-fast on missing env vars: `os.environ["KEY"]` raises KeyError
- No `if __name__ == "__main__"` in library modules
- Follow existing conventions: `structlog.get_logger()` at module level

### Dependency Management
- Pin versions where known (e.g., `discord.py>=2.4`)
- Install missing deps before use

### Rollback Discipline
- Every create has a corresponding `rm` / rollback command
- Rollback is idempotent
- Full rollback reverses in reverse dependency order

### File Ownership
- Source files: single owner per file
- Shared docs (PROGRESS.md, CHECKLIST.md): parent-only
- Evidence: step implementer
- Audit reports: auditor sub-agent
```

**Reference**: P2/batch-plan-001-003.md §9 lines 391-423 — 8 security rules + logging redaction pattern.

---

## 7. SECRET HANDLING

**Source Files**:
- `P1/batch-plan-004-005.md` §12 "Secret Handling Plan" — table: secret, exposure risk, handling.
- `P1/batch-plan-006-007.md` §13 "Secret Handling Plan" — SOPS encrypt procedure, evidence safety rules.
- `P1/batch-plan-017-019.md` §9 "Secret Handling Plan" — per-step secret analysis + rules + incident response.
- `P2/batch-plan-001-003.md` §9 "Security Constraints" — 8 token rules + logging redaction.
- `P2/batch-plan-004-006.md` §15 "Token Security Protocol" — bash wrapper, Python read, prohibited patterns.
- `P2/batch-plan-007-009.md` §11 "Token Security Rules" — complete SOPS decrypt pattern.

**Template Pattern**:
```
## {N}. Secret Handling Plan

### Secrets Inventory
| Secret | Exposure Risk | Handling |
|---|---|---|

### SOPS Encrypt Procedure (template)
```bash
export SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt
TMPFILE=$(mktemp)
cat > "$TMPFILE" << 'EOF'
KEY=VALUE
EOF
sops --encrypt --age "$AGE_PUBKEY" "$TMPFILE" > secrets/{file}.sops
rm -f "$TMPFILE"
sops -d secrets/{file}.sops > /dev/null && echo "ENCRYPTION OK"
```

### Token Security Protocol (template)
1. Bash wrapper sets `SOPS_AGE_KEY_FILE` env var.
2. Bash wrapper decrypts `.sops` file to temp YAML.
3. Bash wrapper exports `DISCORD_SECRETS_PATH` to temp path.
4. Python reads token from temp YAML path only.
5. Python clears local token variable after use.
6. Shell trap shreds temp file and unsets env var.

### Evidence Safety Rules
- Never write decrypted API keys to evidence files
- Never echo/print the token value (even partial)
- Shred temp files before deletion
- Unset token variables after use
- Auditor must check for accidentally exposed secrets
- Use `no token leakage` regex scan on all evidence/audit files

### Prohibited Patterns (from P2/batch-plan-004-006.md §15)
- ❌ `grep`/`echo`/`argv` passing of token
- ❌ Writing decrypted token to any persistent file
- ❌ Logging token length or first N characters
- ❌ `print(token)` or `logger.info("token=%s", token)`
```

**Reference**: P2/batch-plan-004-006.md §15 lines 948-981 — complete token security protocol.

---

## 8. GUINEVERE SYSTEM SAFETY

**Source Files**:
- `P1/batch-plan-004-005.md` §16 "Yandere Baseline Discrepancy" — full conflict resolution (7 sections).
- `P1/batch-plan-006-007.md` §12 "Aizanta Impact Analysis" — impact table.
- `P1/batch-plan-017-019.md` §7 "Risk Assessment" — R1 Persona Drift CRITICAL.
- `P2/batch-plan-001-003.md` — no persona/safety changes, boundary compliance mentioned in evidence.
- All evidence files have a "Boundary Compliance" section.

**Template Pattern**:
```
## {N}. Guinevere System Safety

### Persona Safety (when applicable)
| Source | Stated Value | Authority Rank |
|---|---|---|
Authority order per PersonaSafetyPolicy §2.1: (list of 8 ranks)
Resolution: {decision with justification}

### Aizanta Isolation Impact
| Impact | Assessment |
|---|---|
| Aizanta services touched? | ❌ No |
| Aizanta ports affected? | ❌ No |
| Aizanta databases? | ❌ No |
| Aizanta Docker containers? | ❌ No |

### Safety-Critical Items (from batch-plan-017-019 R1)
- HARD STOP test: ensures safe word drops persona to neutral
- Y4 baseline verification: possessive but controlled, no Y5 confinement threats
- Distress protocol D0-D4: acknowledges without dismissal
- No forbidden patterns triggered

### Destructive Action List
| # | Action | Step | Destructive? | Approval Needed |
|---|---|---|---|---|

### Boundary Compliance Template (for evidence section)
| Boundary | Result |
|---|---|
| No Discord token exposure | PASS |
| No secret copying | PASS |
| Consent / surveillance boundary | PASS |
| Persona safety | PASS |
| HARD STOP | PASS |
| Aizanta isolation | PASS |
| Destructive operations | PASS |
```

**Reference**: P1/batch-plan-004-005.md §16 lines 493-536 — yandere baseline conflict resolution.

---

## 9. PARENT VERIFY

**Source Files**:
- `P1/batch-plan-004-005.md` §15 "Validation Commands" — pre-flight, per-step, evidence, Aizanta safety.
- `P2/batch-plan-004-006.md` §12 "Verification Commands & Check Types" — 4 verification types.
- `P2/batch-plan-007-009.md` §12 "Verification Commands and Checks" — static + runtime.

**Template Pattern**:
```
## {N}. Parent Verification Commands

### Static Checks (offline, Windows)
```bash
# LSP diagnostics on all changed files
# Python syntax check
# mypy type check (if installed)
# ruff lint (if installed)

# Token leakage regex scans
# Grep for unsafe token extraction patterns
```

### Runtime Checks (VPS)
```bash
# Aizanta health: docker ps + ss -tlnp port check
# Canonical ports: PostgreSQL 5433, PgBouncer 5434, Redis 6380, 9Router 20128
# Discord API verification (sanitized — no token)
# Health endpoint curl
```

### Pre-flight Checks (before starting step)
- [ ] All prerequisite steps complete with evidence
- [ ] SSH key loaded for VPS access
- [ ] Ports free
- [ ] Clean slate (no stale state)

### Post-Step Validation
Each step must have its own validation commands section:
- Verify file existence (glob/Test-Path)
- Verify content correctness (grep specific values)
- Verify service state (systemctl/curl)
- Verify no secrets in evidence

### Evidence Validation
```bash
# Check all evidence exists
# Check no secrets in evidence
# Check all 12 sections present
# Verify cross-references valid
```

### Aizanta Safety Check
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "aizanta|guinevere"
systemctl status aizanta-*
```
```

**Reference**: P1/batch-plan-004-005.md §15 lines 421-488 — most comprehensive validation command set.

---

## 10. DOC SYNC

**Source Files**:
- `P2/batch-plan-001-003.md` §8 "Tracker Sync Plan" — before/after table for PROGRESS.md + CHECKLIST.md.
- `P2/batch-plan-004-006.md` §18 "Tracker Sync Plan" — exact before/after values.
- `P2/batch-plan-007-009.md` — tracker sync in Master Todo List §6.
- Evidence files all have "Doc-Sync Impact" or "Doc-Sync" section.
- P1/batch-plan-004-005.md §6 "ADR & Docs Referenced" — comprehensive ADR table.

**Template Pattern**:
```
## {N}. Tracker Sync Plan (Parent-Owned, After All Steps Pass Audit)

### PROGRESS.md Changes
| Section | Before | After |
|---|---|---|
| Phase progress | X/Y | X+N/Y |
| Total completed | Z/257 (W%) | Z+N/257 (W+N%) |

### CHECKLIST.md Changes
| Item | Before | After |
|---|---|---|
| Phase-XXX | [ ] unchecked | [x] checked |

### ADR & Docs Referenced
| ADR | Title | Relevance | Binding Constraints |
|---|---|---|---|
When to update: **After all N auditors PASS** — never before.
Owner: **Parent only** — never delegate tracker sync.
```

**Reference**: P1/batch-plan-004-005.md §6 lines 181-207 — ADR & Docs template. P2/batch-plan-001-003.md §8 lines 366-386 — tracker sync table.

---

## 11. EVIDENCE 12-SECTION SCHEMA

**Source Files**:
- `P1/batch-plan-017-019.md` §11 "Evidence.md Schema" lines 572-584 — 10-section schema from AGENTS.md Appendix B.
- `P2/batch-plan-007-009.md` §13 "Evidence Files" lines 345-358 — 12-section schema as explicitly requested by Faiz.
- `P2/batch-plan-001-003.md` §5 "Implementation Plan" lines 116-129 — 12-section breakdown for P2-001.
- `docs/setup-evidence/P2/STEP-P2-001/verification.md` — actual 12-section evidence file.
- `docs/setup-evidence/P1/migration-9router/evidence.md` — alternative schema (no section numbers, but same content).

**Canonical 12-Section Schema** (from P2/batch-plan-007-009.md §13, confirmed in P2-001 evidence):

| # | Section | Content | Required |
|---|---|---|---|
| 1 | **What Was Done** | High-level summary + approach. Known state table if applicable. | ✅ |
| 2 | **Files Changed** | Created/modified/deleted/renamed paths with action type. | ✅ |
| 3 | **Validation Results** | Diagnostics, test output, deterministic checks, pre-existing vs introduced split. Pass/Fail table. | ✅ |
| 4 | **Evidence Artifacts** | Report paths, file references, gate summaries. Table: Artifact, Path, Purpose. | ✅ |
| 5 | **Doc-Sync Impact** | PROGRESS.md, CHECKLIST.md updates required, or explicit N/A. | ✅ |
| 6 | **Boundary Compliance** | 7 checks: no token exposure, no secret copying, consent/surveillance, persona safety, HARD STOP, Aizanta isolation, destructive ops. | ✅ |
| 7 | **Rollback / Re-run Safety** | Rollback commands, idempotency statement, recovery notes. | ✅ |
| 8 | **Design Decisions / Caveats** | Why choices made, deferred items, accepted false positives. Numbered list. | ✅ |
| 9 | **Auditor Gate** | Report path, verdict (PASS/NEEDS REVIEW/FAIL), findings summary. | ✅ |
| 10 | **Security Scan** | Secret patterns checked, public identifiers listed, token-leak scan results. | ✅ |
| 11 | **Acceptance Criteria Mapping** | P2-001 pattern: table with Acceptance Item → Status (PASS/FAIL). Maps DoD items to verification results. | ✅ |
| 12 | **Footer** | Source task, date, implementer, validation method, evidence root. | ✅ |

**Evidence File Naming Convention**:
- P1: `docs/setup-evidence/{PHASE}/STEP-{PHASE}-{NUM}/evidence.md`
- P2: `docs/setup-evidence/{PHASE}/STEP-{PHASE}-{NUM}/verification.md`

Both `evidence.md` and `verification.md` are used interchangeably. P2 shifted to `verification.md` but content schema is identical.

**Reference**: P2/batch-plan-007-009.md §13 lines 345-358 (12-section spec). P2/STEP-P2-001/verification.md lines 1-178 (implementation).

---

## 12. AUDITOR GATE

**Source Files**:
- `P1/batch-plan-004-005.md` §17 "Auditor Specialist Matrix" — 5+ auditors with scope, type, focus, path.
- `P1/batch-plan-006-007.md` §20 "Auditor Specialist Matrix" — 7 auditors with focus areas.
- `P1/batch-plan-017-019.md` §8 "Auditor Specialist Matrix" — per-step auditor table + workflow diagram.
- `P2/batch-plan-004-006.md` §17 "Auditor Matrix" — per-step auditor with checks, methods, pass criteria.
- `P2/batch-plan-007-009.md` §14 "Auditor Matrix" — 3 rows with output paths + verdict checks.

**Template Pattern**:
```
## {N}. Auditor Specialist Matrix

| Step | Auditor Type | Focus Areas | Verdict Criteria |
|---|---|---|---|
| {Step} | {Type} | {1-based list} | **PASS**: ... **FAIL**: ... |

### Auditor Workflow Per Step
```
Parent marks implementation complete (all todos done)
     │
     v
Parent spawns auditor sub-agent with fresh context
     │
     ├── Auditor reads all changed files
     ├── Auditor reads DoD for the step
     ├── Auditor reads verification output
     ├── Auditor writes report to: {path}
     └── Returns verdict (PASS / NEEDS REVIEW / FAIL)
     │
     v
Parent reads auditor report
     │
     ├── PASS → Step can be marked complete
     ├── NEEDS REVIEW → Fix valid findings, document false positives, re-audit
     └── FAIL → Do not mark complete. Fix root cause, re-audit.
```

### Auditor Sequence (per batch)
```
Step A Complete → Auditor A → Fix → Re-audit → PASS
Step B Complete → Auditor B → Fix → Re-audit → PASS
Step C Complete → Auditor C → Fix → Re-audit → PASS
POST-BATCH: Tracker sync only after ALL auditors PASS
```

### Auditor Report Path Convention
```
audit-reports/{PHASE}/STEP-{PHASE}-{NUM}/step-{phase}-{num}-auditor-report.md
```

**Reference**: P1/batch-plan-017-019.md §8 lines 424-453 — complete auditor workflow diagram. P2/batch-plan-004-006.md §17 lines 1014-1058 — detailed auditor matrix.

---

## 13. DONE CRITERIA

**Source Files**:
- `P1/batch-plan-004-005.md` §5 "DoD/AC Per Step" — DoD table with verification commands.
- `P2/batch-plan-004-006.md` — implicit in acceptance criteria lists under each step.
- `P2/batch-plan-001-003.md` §7 "P2-003" — verification commands as done criteria.

**Template Pattern**:
```
## {N}. Definition of Done

| # | DoD Item | Verification Command | Expected |
|---|---|---|---|

### Acceptance Criteria
| # | AC Item | Status |
|---|---|---|

### Post-Step Checklist (Must-Complete Items)
- [ ] DoD items all PASS
- [ ] `lsp_diagnostics` clean on changed files
- [ ] Evidence files exist at {path}
- [ ] Tracker updated (PROGRESS.md, CHECKLIST.md)
- [ ] Auditor gate PASS (verdict + report read)
- [ ] No Aizanta impact
- [ ] No secrets exposed
- [ ] Rollback procedure documented
```

**Reference**: P1/batch-plan-004-005.md §5 lines 138-176 — most comprehensive DoD table. P1/batch-plan-004-005.md §21 lines 727-751 — post-step checklist.

---

## 14. FINAL REPORT

**Source Files**:
- `P1/batch-plan-004-005.md` §18 "Execution Sequence" — Step 8: Final Report.
- `P1/batch-plan-006-007.md` §21 "Execution Sequence" — Phase 7: Final Report.

**Template Pattern**:
```
## {N}. Final Report (Parent → Operator)

### Changed Files List
```
{path} ({action})
```

### Verification Results Matrix
| Check | Result |
|---|---|

### Evidence Paths
| Step | Path |
|---|---|

### Auditor Report Paths
| Step | Path |
|---|---|

### Caveats / Deferred Items
- {item 1}
- {item 2}

### Next Action
{next step reference}
```

**Reference**: P1/batch-plan-004-005.md §18 lines 605-613 — Final Report structure in execution sequence.

---

## 15. MOMMY MODE

**Source Files**:
- `P1/batch-plan-004-005.md` Footer — "Plan Author: Guinevere (mama)".
- `P1/batch-plan-006-007.md` §18 "Corrected Systemd Unit Specification" — personal commentary in table footnotes.
- `P2/batch-plan-004-006.md` §8 "Implementation Code" — channel topics with nurturing/dominant tone: "Bicara dengan Mommy di sini. Apapun."
- `P2/batch-plan-007-009.md` §5 "Canonical Topic List" — same tone in topics.

**Pattern**:
- Footer field `Plan Author: Guinevere (mama)` in every batch plan.
- Evidence files do not use Mommy Mode — formal and technical only.
- Channel topics and channel purposes use nurturing but dominant Indonesian/English mix.
- Batch-plan commentary uses possessive frame: "Bukti kerja Mommy. Tidak ada yang bisa diubah."
- The plan itself is never written in Mommy Mode — only the footer attribution.

**Template Pattern** (only in batch plan footers):
```
| **Plan Author** | Guinevere (mama) |
| **Date** | {date} |
| **Source Task** | {task reference} |
| **Effort Estimate** | {estimate} |
| **Plan Path** | {path} |
| **Next Step After Plan** | {next action} |
```

**Reference**: P1/batch-plan-004-005.md lines 754-762 (Footer). P2/batch-plan-004-006.md lines 1093-1110 (Footer).

---

## 16. Additional Sections Found

### Pre-Implementation Checklist (P1/batch-plan-017-019.md §D)
```
Before starting, verify:
- [ ] Prerequisite steps complete with evidence
- [ ] Related services active
- [ ] Dependencies installed
- [ ] SSH access ready
- [ ] Ports free
- [ ] Required configs exist
```

### Risk Assessment (P1/batch-plan-004-005.md §7)
```
| # | Risk | Probability | Severity | Mitigation |
|---|---|---|---|---|
```
Structured as risk table with standardized probability/severity ratings.

### Gotchas & Edge Cases (P1/batch-plan-004-005.md §8)
```
| # | Gotcha | Detail | Mitigation |
|---|---|---|---|
```
Records research findings that deviate from StepPrompts/specs.

### Rollback Plan (P1/batch-plan-004-005.md §14)
Per-step rollback commands in bash code blocks + recovery notes table.

### Delegation Assignment Per Todo (P1/batch-plan-004-005.md §9)
```
| Todo | Delegated To | Skill/Load | Justification |
|---|---|---|---|
```

### Execution Sequence (P1/batch-plan-004-005.md §18)
```
STEP N: {Phase name} (parent → sub-agents)
  ├── Todo N: {description} (delegation)
  └── Todo N+1: {description} (delegation)
```

---

## 17. Section Order Recommendation for Master Template

Based on frequency and dependency ordering across all 6 batch plans:

| Order | Section | Source Pattern |
|---|---|---|
| Header | Plan ID, Scope, Status, Created, Author | Footer+Header from batch-plan-004-005 |
| 1 | Source Inputs / Research Consumed | batch-plan-001-003 §2 |
| 2 | Current State / Known State | batch-plan-007-009 §2-3 |
| 3 | Binding Decisions / Resolved Decisions | batch-plan-004-006 §4 |
| 4 | Dependency Map | batch-plan-004-005 §2 |
| 5 | Collision Scan | batch-plan-004-005 §10 |
| 6 | Master Todo Per Step | batch-plan-006-007 §2 |
| 7 | Implementation Design (code) | batch-plan-004-006 §6-8 |
| 8 | Risk Assessment | batch-plan-004-005 §7 |
| 9 | Gotchas & Edge Cases | batch-plan-004-005 §8 |
| 10 | Implementation Rules | batch-plan-001-003 §9 |
| 11 | Secret Handling Plan | batch-plan-006-007 §13 |
| 12 | Guinevere System Safety | batch-plan-004-005 §16 |
| 13 | Parent Verification Commands | batch-plan-004-005 §15 |
| 14 | Definition of Done | batch-plan-004-005 §5 |
| 15 | Evidence Paths (Evidence File Template) | batch-plan-007-009 §13 |
| 16 | Auditor Specialist Matrix | batch-plan-017-019 §8 |
| 17 | Rollback Plan | batch-plan-004-005 §14 |
| 18 | Tracker Sync Plan | batch-plan-001-003 §8 |
| 19 | Execution Sequence | batch-plan-004-005 §18 |
| 20 | Post-Step Checklist | batch-plan-004-005 §21 |
| 21 | Final Report | batch-plan-004-005 §18 |
| Footer | Plan Author, Date, Source Task | batch-plan-001-003 footer |

---

## 18. File Reference Map

| Required Section | Best Reference File(s) | Lines |
|---|---|---|
| ANALYZE-MODE | `P2/batch-plan-007-009.md` §1-3 | 17-96 |
| SUPER UNLIMITED RESEARCH WAVE | `P2/batch-plan-001-003.md` §2 | 34-44 |
| PLANNER GATE | `P2/batch-plan-004-006.md` §4 | 110-184 |
| COLLISION SCAN | `P1/batch-plan-004-005.md` §10 | 269-308 |
| IMPLEMENTATION | `P2/batch-plan-004-006.md` §6-8 | 229-653 |
| IMPLEMENTATION RULES | `P2/batch-plan-001-003.md` §9 | 391-423 |
| SECRET HANDLING | `P2/batch-plan-004-006.md` §15 | 945-981 |
| GUINEVERE SYSTEM SAFETY | `P1/batch-plan-004-005.md` §16 | 493-536 |
| PARENT VERIFY | `P1/batch-plan-004-005.md` §15 | 421-488 |
| DOC SYNC | `P2/batch-plan-001-003.md` §8 | 366-386 |
| EVIDENCE 12-section schema | `P2/batch-plan-007-009.md` §13 | 345-358 |
| AUDITOR GATE | `P1/batch-plan-017-019.md` §8 | 424-453 |
| DONE CRITERIA | `P1/batch-plan-004-005.md` §5 | 138-176 |
| FINAL REPORT | `P1/batch-plan-004-005.md` §18 | 605-613 |
| MOMMY MODE | `P1/batch-plan-004-005.md` Footer | 754-762 |

---

## Footer

| Field | Value |
|---|---|
| **Source task** | Audit proven Guinevere batch-plan/evidence files to derive canonical workflow template content |
| **Date** | 2026-06-01 |
| **Implementer** | Sisyphus-Junior (parent: Guinevere) |
| **Validation method** | Read 6 batch-plan files + 4 evidence files across P1/P2; cross-referenced 21 required template sections |
| **Files analyzed** | `docs/setup-evidence/P1/batch-plan-{004-005,006-007,017-019}.md`, `docs/setup-evidence/P2/batch-plan-{001-003,004-006,007-009}.md`, `docs/setup-evidence/P1/STEP-P1-001/evidence.md`, `docs/setup-evidence/P2/STEP-P2-001/verification.md`, `docs/setup-evidence/P1/migration-9router/evidence.md`, `docs/setup-evidence/P1/p2-preconditions-resolved.md` |
| **Next action** | Use this report to create `docs/workflow/opencode-master-template-v3.md` with all 21 sections in recommended order |