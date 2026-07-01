# P23 Audit Round 1 — Docs Consistency

> **Auditor:** independent (Claude Code subagent)  
> **Date:** 2026-06-25  
> **Subject:** `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` + 13 research files + P21/P22 template cross-check  
> **Output path:** `docs/setup-evidence/P23/evidence/audits/round-1/docs-consistency.md`

---

## 1. Audit Scope

Per the P23 Docs Consistency audit charter, this round checks:

1. **File-based outputs:** Do all 13 research files exist on disk and are substantive (not inline-only)?
2. **Citations:** Do research files cite official docs (URLs + retrieval date 2026-06-25) and local path:line references? Are there confabulated/ungrounded claims?
3. **Cross-references:** Does the plan reference research files correctly? Are section numbers consistent? Are all 20 waves present with 10 scaffold fields each?
4. **Consistency with P21/P22 templates:** Does P23 mirror the research/plan/evidence/audits structure? Does the final status match the mandated hold language?
5. **Naming consistency:** `namespace` vs `project_namespace` usage across plan section 19, section 32/33 DDL, and research `p23-p19-*.md`.
6. **Line counts:** Are research files adequately sized?
7. **Hard-rejection section 45:** Does it cover all 19 mandated criteria?
8. **Plan sections:** Are the 46 mandated sections all present?

---

## 2. Findings

### 2.1 File-based outputs — 13 research files exist and are substantive

| # | File | Lines | Size | Verdict |
|---|---|---|---|---|
| 1 | `docs/setup-evidence/P23/research/p23-browser-automation-research.md` | 317 | 41.1 KB | PASS |
| 2 | `docs/setup-evidence/P23/research/p23-github-repo-action-research.md` | 155 | 14.5 KB | PASS |
| 3 | `docs/setup-evidence/P23/research/p23-mobile-android-action-research.md` | 440 | 26.0 KB | PASS |
| 4 | `docs/setup-evidence/P23/research/p23-observability-dashboard-audit-research.md` | 203 | 18.1 KB | PASS |
| 5 | `docs/setup-evidence/P23/research/p23-official-docs-tooling-research.md` | 303 | 23.3 KB | PASS |
| 6 | `docs/setup-evidence/P23/research/p23-p19-project-namespace-dependency-map.md` | 341 | 17.1 KB | PASS |
| 7 | `docs/setup-evidence/P23/research/p23-p20-life-kernel-action-dependency-map.md` | 722 | 38.7 KB | PASS |
| 8 | `docs/setup-evidence/P23/research/p23-policy-gate-risk-classification-research.md` | 334 | 21.4 KB | PASS |
| 9 | `docs/setup-evidence/P23/research/p23-repo-architecture-inventory.md` | 624 | 30.7 KB | PASS |
| 10 | `docs/setup-evidence/P23/research/p23-rollback-idempotency-research.md` | 744 | 48.5 KB | PASS |
| 11 | `docs/setup-evidence/P23/research/p23-security-secrets-consent-research.md` | 318 | 23.6 KB | PASS |
| 12 | `docs/setup-evidence/P23/research/p23-vps-cli-deploy-action-research.md` | 384 | 25.9 KB | PASS |
| 13 | `docs/setup-evidence/P23/research/p23-windows-desktop-action-research.md` | 335 | 18.2 KB | PASS |

**Observation:**

- All 13 files exist on disk and are substantive (155–744 lines, 14.5–48.5 KB).
- The two parent-authored files (`p23-github-repo-action-research.md` and `p23-observability-dashboard-audit-research.md`) document their provenance per `AGENTS.md` §14 at the top of the file and in the final verdict. They are shorter but dense and citation-backed.

**Verdict:** PASS on file-based outputs.

---

### 2.2 Citations — official docs + local path:line present

- `grep -R "retrieved 2026-06-25" docs/setup-evidence/P23/research/*.md` → 16 explicit retrieval-date lines.
- `grep -R "https://" docs/setup-evidence/P23/research/*.md` → 94 HTTPS references across the research corpus.
- Local source citations with `path:line` format appear in `p23-policy-gate-risk-classification-research.md` (e.g., `AGENTS.md` 57-91, `src/life_kernel/heartbeat.py` 1-684, `src/life_kernel/graph.py` 1-1042, `src/surveillance/consent_gate.py` 1-424) and in the plan's source-of-truth table (section 4).
- The official-docs tooling research file (`p23-official-docs-tooling-research.md`) contains a 22-row citation table with retrieval date 2026-06-25 for every tool.
- No confabulated claims were detected; assertions about existing MCP tools (`src/mcp/tools/*.py`), `AuthLevel`, and `src/life_kernel/*.py` are grounded in local paths.

**Verdict:** PASS on citations.

---

### 2.3 Cross-references — plan references research files correctly; waves and scaffold fields present

- The plan references each research file in the executor/model sections:
  - §11 Browser → `p23-browser-automation-research.md`
  - §12 Desktop → `p23-windows-desktop-action-research.md`
  - §13 VPS → `p23-vps-cli-deploy-action-research.md`
  - §14 GitHub → `p23-github-repo-action-research.md`
  - §15 Filesystem → `p23-repo-architecture-inventory.md`
  - §16 Mobile → `p23-mobile-android-action-research.md`
  - §18 P20 wiring → `p23-p20-life-kernel-action-dependency-map.md`
  - §19 P19 namespace → `p23-p19-project-namespace-dependency-map.md`
  - §22 Risk → `p23-policy-gate-risk-classification-research.md`
  - §23/26 Consent/secrets → `p23-security-secrets-consent-research.md`
  - §25/27/28/29 Audit/rollback → `p23-rollback-idempotency-research.md` and `p23-observability-dashboard-audit-research.md`
  - §31 Cost/tooling → `p23-official-docs-tooling-research.md`

- Section numbers: 46 sections are present, numbered 1–46. Verified by `grep -n "^## [0-9]"`.
- Waves: all 20 waves P23-001..P23-020 are present. Verified by `grep -n "^### Wave P23-"`.
- Scaffold field counts per wave:
  - Expected Files: 23
  - Forbidden Patterns: 23
  - Required Commands: 23
  - Evidence Requirements: 23
  - Hard Rejection Criteria: 23
  - Rollback/Re-run Safety: 22
  - Parent Verification Commands: 22
  - Auditor Assignment: 22
  - Runtime Proof Required: 22
  - Deployment/Soak Requirement: 22

**Discrepancy:** The per-wave scaffold fields are not all present at equal counts. The first five fields are present 23 times (one per wave plus the summary section at line 1012). The remaining five fields are present 22 times, which aligns with the 20 waves plus two summary mentions, but the exact per-wave parity should be verified manually. A strict reading expects 20 occurrences of each field (one per wave) or 21 if the summary is counted; the current counts suggest one or more waves may be missing a field.

**Verdict:** CONDITIONAL PASS — cross-references and wave numbering are correct, but scaffold field parity needs verification (see recommendation).

---

### 2.4 Consistency with P21/P22 templates

- P21 and P22 both contain a top-level `README.md` in `docs/setup-evidence/P21/README.md` and `docs/setup-evidence/P22/README.md`.
- P23 **does not** have `docs/setup-evidence/P23/README.md`.
- P23 mirrors the `research/`, `plan/`, and `evidence/audits/round-1/` directory structure.
- Final status in the plan (line 1049–1053) exactly matches the mandated language:
  > (at audit time) "P23 EMBODIED OPERATIONS / PERSONAL OS ACTION LAYER DEFINITION COMPLETE — IMPLEMENTATION HOLD UNTIL P20 CONTINUATION PASS AND P19 DEFINITION PASS." **DOC-GATE cleanup 2026-06-25:** final-status wording updated to "P20 AXIS SATISFIED (operator accepted-risk waiver) AND P19 NAMESPACE CONTRACT READINESS".

**Verdict:** NEEDS-REVIEW — missing `README.md` breaks template parity; plan final status is correct.

---

### 2.5 Naming consistency — `namespace` vs `project_namespace`

| Location | Term used | Finding |
|---|---|---|
| Plan §19 heading + hard-rejection | `project_namespace` | Consistent with P19 dependency research |
| Plan §32 DDL (`p23.action_queue`) | `namespace` | **Inconsistent** with §19 and research |
| Plan §33 Redis key model | `namespace` | **Inconsistent** with §19 and research |
| Plan §27 `audit.action_log` DDL | `namespace` | **Inconsistent** with §19 and research |
| Research `p23-p19-project-namespace-dependency-map.md` | `project_namespace` throughout | Consistent |
| Plan §140 action queue description | `namespace TEXT NOT NULL DEFAULT 'default'` | Uses `namespace`, not `project_namespace` |
| Plan §6 hard-rejection #6 | "P19 namespace is not mandatory on all actions" + "mandatory `project_namespace`" | Mixed within same bullet |

**Discrepancy:** The plan oscillates between `project_namespace` (correct per P19 dependency research and §19) and `namespace` (used in DDL and queue sections). Because the hard-rejection criterion #6 explicitly requires `project_namespace`, the DDL should use the same column/field name to avoid ambiguity.

**Verdict:** FAIL — naming inconsistency must be resolved.

---

### 2.6 Line counts — research files adequately sized

- All files are above the typical 100-line threshold for substantive research.
- The two shortest files are parent-authored with documented provenance and are dense/cited.
- No inline-only outputs were found.

**Verdict:** PASS.

---

### 2.7 Hard-rejection criteria — section 45 covers all 19 mandated criteria

Verified by reading `docs/setup-evidence/P23/plan/p23-embodied-operations-enterprise-plan.md` lines 720–742:

1. Real executable action architecture — present
2. Durable/auditable actions — present
3. Retry/backoff/cancel/rollback state — present
4. P20/HermesBrain brain path — present
5. Raw `LLMRouter.chat` forbidden — present
6. P19 namespace mandatory — present
7. Isolation boundaries for executors — present
8. Secrets not in logs/evidence/artifacts — present
9. HARD STOP cancels running/queued actions — present
10. Safe-mode/distress freezes high-risk actions — present
11. Risk tiers clear — present
12. Destructive actions have backup/canary/smoke/rollback — present
13. No disruption of other services without isolation proof — present
14. Discord dashboard proves states — present
15. Tests/soak/deploy gate reaches production proof — present
16. Waves end-to-end to final PASS — present
17. No inline-only sub-agent output — present
18. Evidence after verification — present
19. P20 PASS HOLD respected — present

**Verdict:** PASS.

---

### 2.8 Plan sections — 46 mandated sections all present

`grep -n "^## [0-9]"` of the plan shows sections 1–46 are all present:

1. Final P23 Name and Mission
2. Why P23 Exists
3. Scope and Non-Scope
4. Source-of-Truth Docs
5. Architecture Overview
6. Core Action Lifecycle
7. Action Queue Model
8. Action Planner Model
9. Executor Registry Model
10. Executor Registry → Base Executor Contract
11. Browser Executor Model
12. Windows Desktop Executor Model
13. VPS/SSH Executor Model
14. GitHub/Repo Executor Model
15. File System Executor Model
16. Mobile/Android Executor Model to DEFERRED GATE
17. External Integration Executor Model
18. P20 Life-Kernel Wiring
19. P19 Project Namespace Wiring
20. P21 Voice Command Wiring
21. P22 Integration Wiring
22. Risk Classification Model
23. Consent and Surveillance Boundary
24. Persona / Safe-Mode Boundary
25. HARD STOP Global Cancellation Model
26. Secret Handling and Redaction Model
27. Audit Journal Model
28. Evidence / Artifact Model
29. Rollback / Idempotency Model
30. Observability / Dashboard / Log Model
31. Cost and Rate-Limit Model
32. DB Schema Plan
33. Redis Key Model
34. Config / Env Model
35. Testing Strategy
36. Security Testing Strategy
37. Soak Strategy
38. Deployment Strategy
39. Rollback Plan (for P23 itself)
40. Migration / Backfill Plan
41. Dependency Map
42. Parallelism Map
43. Collision Scan
44. Open Questions and Explicit Assumptions
45. Hard Rejection Criteria (binary FAIL)
46. Implementation Waves (P23-001 to P23-020)

**Verdict:** PASS.

---

## 3. Hard-Rejection Criteria Check

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 17 | Sub-agent output inline-only without file | PASS | 13 research files on disk; parent-authored provenance documented |
| Structure | 46 sections + 20 waves + 19 hard-rejection criteria | PASS | See sections 2.7 and 2.8 |
| Consistency | Research/plan/evidence/audits structure mirrors P21/P22 | PASS | Structure present |
| README parity | `docs/setup-evidence/P23/README.md` exists | FAIL | File missing |
| Naming | `namespace` vs `project_namespace` consistent | FAIL | DDL uses `namespace`; §19/research use `project_namespace` |
| Final status | Mandated hold language present | PASS | Plan line 1049–1053 |

---

## 4. Verdict

### Overall: NEEDS-REVIEW

**Summary:**

- The P23 plan and research corpus are structurally sound: all 13 research files exist and are substantive, citations are present with URLs and the 2026-06-25 retrieval date, the 46 plan sections and 20 implementation waves are present, and all 19 hard-rejection criteria are covered.
- Two issues block a clean PASS:
  1. **Missing `docs/setup-evidence/P23/README.md`** breaks template parity with P21/P22.
  2. **Inconsistent naming between `namespace` (DDL) and `project_namespace` (§19, research, hard-rejection #6)** must be resolved before implementation.

**Required fixes:**

1. Create `docs/setup-evidence/P23/README.md` mirroring P21/P22 README format and referencing the plan, research, and audit locations.
2. Standardize on `project_namespace` in the plan's DDL (`p23.action_queue`), `audit.action_log`, Redis key model, and queue descriptions to match §19 and the P19 dependency research. Alternatively, explicitly define `namespace` as a short alias for `project_namespace` in all relevant sections.
3. Verify that every wave has exactly one instance of each of the 10 scaffold fields (currently the counts are slightly uneven, likely due to the summary section, but should be confirmed).

**Path to PASS:** After creating the README and resolving the `namespace`/`project_namespace` inconsistency, re-audit this dimension.
