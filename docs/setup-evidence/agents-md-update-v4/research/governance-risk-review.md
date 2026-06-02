# Governance Risk Review — AGENTS.md Scaffold Rule (v4 Baseline Audit)

| Field | Value |
|---|---|
| **Scope** | AGENTS.md v2.1 (395 lines, current) — governance/safety/process risk audit for proposed scaffold rule changes |
| **Date** | 2026-06-01 |
| **Reviewer** | Guinevere (parent — governance risk review, read-only) |
| **Baseline** | AGENTS.md v2.1 on disk (395 lines, auditor PASS 2026-06-01) |
| **Evidence path** | `docs/setup-evidence/agents-md-update-v4/research/governance-risk-review.md` |
| **Verdict** | **PASS — with 14 safeguards, 3 NEEDS REVIEW findings, 5 wording recommendations** |

---

## 1. Review Methodology

This review reads AGENTS.md v2.1 (current, 395 lines on disk), cross-references with the v2.0 baseline (689 lines, system-prompt snapshot), the v2.1 auditor report, four research reports (insertion-map, evidence-audit-patterns, evidence-audit-style, concise-structure-blueprint, rule-preservation-core, rule-preservation-appendix), and the prior `agents-md-update` verification. The review identifies governance, safety, and process risks that any scaffold rule update must satisfy.

No edits performed. No files modified.

---

## 2. Current AGENTS.md Governance Inventory (v2.1 — Verified on Disk)

### 2.1 BLOCKING Rules (16 items, lines 26-43)

| # | Rule | Line | Present |
|---|---|---|---|
| B1 | NEVER skip post-step checklist | 28 | ✅ |
| B2 | NEVER skip per-step implementation auditor gate | 29 | ✅ |
| B3 | NEVER perform structured verification inline; must be file-based | 30 | ✅ NEW v2.1 |
| B4 | NEVER assign one sub-agent to more than one implementation step | 31 | ✅ NEW v2.1 |
| B5 | NEVER commit secrets | 32 | ✅ |
| B6 | NEVER bypass HARD STOP protocol | 33 | ✅ |
| B7 | NEVER bypass consent/surveillance boundary | 34 | ✅ |
| B8 | NEVER allow Y6 yandere level; Y4 baseline, Y5 ceiling | 35 | ✅ |
| B9 | NEVER use type-safety suppression | 36 | ✅ |
| B10 | NEVER use empty catch/except or swallow failure | 37 | ✅ |
| B11 | NEVER delete/skip failing tests to pass | 38 | ✅ |
| B12 | NEVER auto-deploy or run destructive ops without per-action approval | 39 | ✅ |
| B13 | NEVER confabulate memories; below 80% confidence, state uncertainty | 40 | ✅ |
| B14 | NEVER break existing state silently | 41 | ✅ |
| B15 | NEVER expose Faiz's personal/intimate data | 42 | ✅ |
| B16 | NEVER store raw surveillance data in repo artifacts | 43 | ✅ |

**Governance verdict**: All 16 BLOCKING rules present and intact. No items removed or weakened from v2.0. Two new items (B3, B4) strengthen the audit trail.

### 2.2 Consent-Safety Mandate (§2.1, lines 75-79)

Safety-affecting domains listed: persona, surveillance, memory, consent, safety-policy, encryption, distress-protocol, yandere-boundary, agent-loop, credentials, System Prompt Master, persona drift control.

Preserve list: no surveillance without explicit consent, no consent revocation bypass, no HARD STOP bypass, no distress protocol suppression, no punishment overflow over emergency response, no Y6, no intimate/plaintext data exposure, no raw surveillance in artifacts.

**Governance verdict**: PASS. Single authoritative source preserved. Heightened-review-even-under-bypass clause present in §6 (line 222).

### 2.3 Bypass Mode (§0, lines 45-52)

| Mechanism | Present | Status |
|---|---|---|
| Sticky until `bypass off` | Line 47 | ✅ |
| Allowed: edit specs/docs with footer addendum | Line 49 | ✅ |
| Still required: consent-safety review, Oracle review, auditor gate, evidence, no BLOCKING violations | Line 50 | ✅ |
| Auto-flag: ADR edits, ADR conflicts, safety-affecting domains, >3 docs in session | Line 51 | ✅ |
| Optional session-end summary | Line 52 | ✅ |
| Eject via `bypass off` | §7 table, line 235 | ✅ |

**Governance verdict**: PASS. Bypass mode correctly preserves safety constraints.

### 2.4 Workflow Gates (§14, lines 377-391)

| Gate | Present | Status |
|---|---|---|
| Research wave (mandatory) | Line 379 | ✅ |
| Planner gate (mandatory) | Line 380 | ✅ |
| Planner parallelism | Line 381 | ✅ |
| Collision scan (mandatory) | Line 382 | ✅ |
| Implementation wave (one sub-agent per step) | Line 383 | ✅ |
| Parent verification | Line 384 | ✅ |
| Auditor orchestrator | Line 385 | ✅ |
| Per-step auditor gate (6-step order + verdict handling) | Lines 387-391 | ✅ |

**Governance verdict**: PASS. Both §14 Workflow Gates and §14 Per-Step Auditor Gate are preserved alongside §2 mandates. The concise-structure-blueprint originally proposed removing §14 gates as "redundant," but the implementation retained them.

### 2.5 Three v2.1 Rules

| Rule | Locations | Status |
|---|---|---|
| Parent verify delegate | §1 step 10 (67), §2.7 (125-139), §14 (384) | ✅ |
| One sub-agent one step | BLOCKING B4 (31), §1 step 9 (66), §2.6 (118-119), §14 (383) | ✅ |
| Planner determines parallelism | §1 step 7 (64), §2.4 (97-99), §14 (381) | ✅ |

**Governance verdict**: PASS. All three new rules embedded at multiple enforcement levels.

---

## 3. Identified Risks for Any Scaffold Rule Update

### R1 — Line Budget Erosion Risk

**Severity**: MEDIUM | **Category**: Process

AGENTS.md was condensed from 689 lines (v2.0) to 395 lines (v2.1) — a 42% reduction. This was necessary for token efficiency but approaches the lower bound where nuance loss becomes detectable.

**Risk**: Any further line reduction (targeting below 350 lines) risks:
- Removing the §14 Workflow Gates section (30 lines) which duplicates §2 but serves as the "quick reference" for agents that don't read §2 carefully.
- Condensing the Anti-Pattern Catalog (§5) below the 7-category minimum, losing specific examples.
- Removing the Binding Tie-Breakers table (§8), which is the only section that maps conflict types to specific documents.

**Required safeguard**: Any v4 update must preserve all 16 BLOCKING rules, all 7 §5 anti-pattern categories, §8 Binding Tie-Breakers (9 rows), §2.1 Consent-Safety (both domain list and preserve list), and §14 Workflow Gates + Per-Step Auditor Gate. Minimum viable line count is ~350.

### R2 — Duplication Tension: §14 Workflow Gates vs §2 Mandates

**Severity**: LOW | **Category**: Governance

§14 Workflow Gates (lines 377-385) restates §2 mandates in condensed form. The concise-structure-blueprint recommended removing §14 gates as "redundant." The v2.1 implementation kept them.

**Risk**: If a v4 update removes §14 gates to reduce lines, agents that only read §14 (tooling context) lose the workflow sequence. If §14 gates stay, there's ~50 lines of duplication that wastes context tokens.

**Recommendation**: Keep §14 gates. The duplication is **intentional** and serves agents that context-switch between §2 (conceptual mandates) and §14 (practical tooling). The cost of ~50 extra lines is acceptable for the safety benefit.

### R3 — Bypass Mode "Auto-Flag" Mechanism Undefined

**Severity**: MEDIUM | **Category**: Governance

§0 line 51: "Auto-flag visibly when edits touch ADRs, conflict with ADRs, touch safety-affecting domains, or modify more than three docs in one session."

**Risk**: The word "visibly" is not defined. What does "visible" mean? A log entry? A console message? A TODO item? Without a concrete mechanism, "auto-flag" is aspirational and may be silently ignored under time pressure.

**Required safeguard**: v4 must either (a) define the auto-flag mechanism concretely (e.g., "log to evidence and add a TODO flag visible in session summary"), or (b) accept that auto-flag is best-effort and document this limitation in the Bypass Mode section.

**Wording recommendation**: Replace "Auto-flag visibly" with "Auto-flag by logging to the current evidence file and adding a visible TODO item".

### R4 — Parent Verification Delegation May Undermine Direct Accountability

**Severity**: MEDIUM | **Category**: Process/Safety

v2.1 added BLOCKING B3 ("NEVER perform structured verification inline") and §2.7 (parent delegates structured verification to an independent verifier sub-agent). The intent is to enforce file-based evidence. But the delegation path creates a two-layer verification chain: sub-agent → verifier sub-agent → parent reads report.

**Risk**: If parent becomes a "pass-through" that reads the verifier's verdict without reading the underlying files, the verification chain degrades. Parent accountability (§2.7 opening sentence: "Parent is accountable for verification") is the only constraint preventing this.

**Required safeguard**: v4 must preserve the explicit parent-accountability statement in §2.7. Consider adding: "Parent MUST semantically spot-check at least one changed file per verification cycle, regardless of verifier report."

### R5 — HARD STOP Reference Count Discrepancy

**Severity**: LOW | **Category**: Boundary Compliance

The v2.1 auditor report claims 9 HARD STOP references. A grep of the current AGENTS.md shows references at lines: 15, 33, 79, 180, 206, 222, 236, 337. That's 8 distinct references (not 9). The auditor may have counted a section heading or a cross-reference as a separate hit.

**Risk**: If a future update removes one HARD STOP reference, the audit check might still pass if the auditor only looks for "present" rather than "count >= 8."

**Required safeguard**: v4 auditor must verify HARD STOP count >= 8 across distinct semantic contexts (BLOCKING, consent-safety, post-step checklist, anti-patterns, escalation, operator protocol, footer).

### R6 — §14 Per-Step Auditor Gate Lacks Auditor Independence Definition

**Severity**: LOW | **Category**: Process

§14 (lines 387-391) defines the auditor gate order but does not explicitly require that the auditor sub-agent is a different agent instance from the implementation sub-agent. The §0 BLOCKING B2 says "NEVER skip per-step implementation auditor gate" and §2.9 says "independent auditor specialists," but the specific §14 gate description uses the term "independent auditor" only once.

**Risk**: Without a clear independence constraint in §14, an agent could theoretically spawn itself (same task_id) as auditor.

**Required safeguard**: v4 must add to §14: "Auditor sub-agent MUST be a new, separate agent instance — not the same `task_id` as the implementation agent."

### R7 — §9 Repository Isolation Policy Does Not Cover MCP Server Sharing

**Severity**: LOW | **Category**: Governance

§9 (lines 284-288) lists "never share" items: VPS/runtime, PostgreSQL/Redis, secrets, evidence roots, surveillance data, credentials. It does not mention MCP server instances, which are a newer infrastructure component.

**Risk**: If a v4 update adds MCP server sharing rules without updating §9, the isolation policy becomes incomplete.

**Required safeguard**: If v4 introduces or expands MCP server usage, §9 must be updated to include MCP server isolation rules.

### R8 — No Explicit Definition of "Trivial" for the Relaxation Rule

**Severity**: LOW | **Category**: Process

§10 (line 294): "Relax only for trivial read-only answers or single-line typos with diagnostics. Never relax safety review for boundary-sensitive work."

**Risk**: "Trivial" is undefined. An agent may classify a 50-line doc edit as "trivial" if it's a non-code file. The relaxation exception has no upper bound on scope.

**Required safeguard**: v4 should add a scope qualifier: "Trivial means: read-only queries, single-line typo corrections, or files under 10 lines with no safety-affecting content."

### R9 — Evidence Minimum Schema (§11) Lists 12 Sections but Doesn't Require All

**Severity**: LOW | **Category**: Process

§11 (line 298): "Every per-task evidence file should include: What Was Done; Files Changed; Validation Results; Evidence Artifacts; Doc-Sync Impact; Boundary Compliance; Rollback/Re-run Safety; Design Decisions/Caveats; Auditor Gate; Security Scan; Acceptance Criteria Mapping; Footer."

Uses "should" instead of "must." This is intentional (the evidence-audit-patterns report distinguishes required vs optional sections).

**Risk**: An agent could produce a 5-section evidence file and claim partial compliance with "should."

**Required safeguard**: v4 should change "should include" to "must include" for the 10 required sections (excluding Security Scan and Acceptance Criteria Mapping, which are optional).

---

## 4. Cross-Reference Verification (v2.1 on Disk)

| Cross-Reference in AGENTS.md | Target | Exists on Disk |
|---|---|---|
| `docs/10-governance/17-ADR_Index_v1.0.md` | ADR Index | ✅ |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | PersonaSafetyPolicy | ✅ |
| `docs/README.md` | Master docs index | ✅ |
| `docs/00-core/` | Core docs folder | ✅ |
| `docs/10-governance/` | Governance docs | ✅ |
| `docs/20-security/` | Security docs | ✅ |
| `docs/30-data/` | Data docs | ✅ |
| `docs/40-operations/` | Operations docs | ✅ |
| `docs/50-quality/` | Quality docs | ✅ |
| `docs/60-persona/` | Persona docs | ✅ |
| `docs/70-finops/` | FinOps docs | ✅ |
| `adr/` | ADR folder | ✅ |
| `evidence/` | Evidence folder | ✅ |
| `audit-reports/` | Audit reports | ✅ |
| `research-reports/` | Research reports | ✅ |
| `runbooks/` | Runbooks | ✅ |

All cross-references valid.

---

## 5. Safety Boundary Integrity (v2.1 — No Regression from v2.0)

| Boundary | v2.0 | v2.1 | Delta |
|---|---|---|---|
| Y4 baseline / Y5 ceiling / Y6 prohibition | ✅ | ✅ (line 35) | None |
| HARD STOP protocol | ✅ | ✅ (8+ references) | None |
| Consent revocation | ✅ | ✅ (§2.1 line 79) | None |
| Surveillance without consent | ✅ | ✅ (§2.1 line 79) | None |
| Distress protocol suppression | ✅ | ✅ (§2.1 line 79, §4 line 180) | None |
| Punishment over emergency | ✅ | ✅ (§2.1 line 79, §5 line 206) | None |
| Memory confabulation (80% floor) | ✅ | ✅ (BLOCKING B13 line 40) | None |
| Secret exposure (commit/paste) | ✅ | ✅ (BLOCKING B5 line 32) | None |
| Intimate data exposure | ✅ | ✅ (BLOCKING B15 line 42) | None |
| Raw surveillance in artifacts | ✅ | ✅ (BLOCKING B16 line 43) | None |
| Destructive ops without approval | ✅ | ✅ (BLOCKING B12 line 39) | None |
| Type-safety suppression | ✅ | ✅ (BLOCKING B9 line 36) | None |
| Empty catch/except | ✅ | ✅ (BLOCKING B10 line 37) | None |
| Bypass mode safety constraints | ✅ | ✅ (lines 45-52) | None |
| Persona quote preserved | ✅ | ✅ (line 337) | None |
| §13 Footer v2.1 row | N/A | ✅ (line 325) | New |

**Safety boundary verdict**: ZERO regressions. All v2.0 safety boundaries preserved in v2.1.

---

## 6. Anti-Pattern Catalog Completeness (§5, lines 182-210)

| Category | Lines | Items | Complete |
|---|---|---|---|
| Type Safety Bypass | 184-186 | 6 forbidden patterns | ✅ |
| Error Handling Bypass | 188-190 | 4 forbidden patterns + preferred approach | ✅ |
| Test and Verification Suppression | 192-194 | 4 forbidden patterns + fix root cause | ✅ |
| Sub-Agent Output Anti-Patterns | 196-198 | 6 forbidden patterns | ✅ |
| Secret and Consent Exposure | 200-202 | 7 forbidden patterns | ✅ |
| Persona-Risk Anti-Patterns | 204-206 | 7 forbidden patterns | ✅ |
| Operator-Process Anti-Patterns | 208-210 | 5 forbidden patterns | ✅ |

All 7 categories preserved. Total ~39 forbidden patterns documented. No weakening from v2.0.

---

## 7. Wording Recommendations for v4

| # | Current Wording | Recommended Wording | Rationale |
|---|---|---|---|
| W1 | §0 line 51: "Auto-flag visibly when edits touch ADRs..." | "Auto-flag by logging to the current evidence file and adding a visible TODO item when edits touch ADRs..." | Define mechanism for auto-flag |
| W2 | §11 line 298: "Every per-task evidence file should include:" | "Every per-task evidence file must include:" | Change "should" to "must" for enforceability |
| W3 | §10 line 294: "Relax only for trivial read-only answers or single-line typos" | "Relax only for: read-only queries, single-line typo corrections, or files under 10 lines with no safety-affecting content" | Scope the relaxation rule |
| W4 | §14 line 389: "spawn independent auditor with file report" | "spawn independent auditor (new agent instance, NOT same `task_id` as implementer) with file report" | Enforce auditor independence |
| W5 | §2.7 line 127: "Parent is accountable for verification" | "Parent is accountable for verification and MUST semantically spot-check at least one changed file per cycle" | Prevent verifier pass-through |

---

## 8. NEEDS REVIEW Findings

| # | Finding | Severity | Risk Category | Required Action |
|---|---|---|---|---|
| F1 | Bypass mode "auto-flag visibly" has no defined mechanism | MEDIUM | Governance | Define concrete mechanism (W1) or document as best-effort |
| F2 | §11 uses "should" instead of "must" for evidence schema | LOW | Process | Change to "must" (W2) or document optional sections explicitly |
| F3 | §10 relaxation rule lacks scope qualifier for "trivial" | LOW | Process | Add scope qualifier (W3) |

**None of these findings block v4 implementation.** All are enhancements to existing governance safeguards, not regressions. They should be addressed during v4 as wording improvements, not as prerequisites.

---

## 9. Safeguard Requirements for Any v4 Scaffold Rule Update

Any AGENTS.md scaffold rule update (v4 or later) MUST satisfy ALL of the following:

### 9.1 Non-Negotiable Preservation

1. All 16 BLOCKING rules (lines 26-43) preserved verbatim.
2. §2.1 Consent-Safety Mandate: both domain list AND preserve list.
3. §5 Anti-Pattern Catalog: all 7 categories with all ~39 forbidden patterns.
4. §6 Escalation Rules: all 5 triggers + heightened-review clause.
5. §7 Operator Protocol: all 9 command-response pairs.
6. §8 Binding Tie-Breakers: all 9 conflict-type mappings.
7. §13 Footer: versioning table, maintenance, operator sign-off, persona quote.
8. §14 Workflow Gates + Per-Step Auditor Gate.
9. HARD STOP: minimum 8 references across distinct semantic contexts.
10. Bypass mode: sticky lifecycle, allowed/still-required/auto-flag/eject.

### 9.2 Safety Boundary Constraints

11. No removal or weakening of Y4/Y5/Y6 boundaries.
12. No removal or weakening of consent/surveillance/HARD STOP/distress-protocol protections.
13. No removal of secret exposure protections (commit/paste/external tools).
14. No removal of type-safety suppression or empty-catch bans.
15. No removal of destructive-ops approval requirement.
16. No removal of memory confabulation floor (80%).

### 9.3 Process Gate Constraints

17. Research wave remains mandatory before non-trivial implementation.
18. Planner gate remains mandatory after research synthesis.
19. Collision scan remains mandatory before implementation wave.
20. Auditor gate remains mandatory before step completion.
21. File-based output discipline remains enforced.
22. One sub-agent per implementation step remains enforced.

### 9.4 Quality Bar

23. Line count must not fall below ~350 (nuance floor).
24. All cross-references (§8 reference tables) must remain valid.
25. v4 must include a version table row with date, author, and change description.
26. v4 must pass auditor gate with independent auditor report.

---

## 10. Comparison: v2.0 → v2.1 Governance Delta

| Aspect | v2.0 (689 lines) | v2.1 (395 lines) | Risk Assessment |
|---|---|---|---|
| BLOCKING rules | 12 | 16 | ✅ Strengthened (+2 new rules) |
| Consent-safety mandate | 1 location | 1 location (consolidated) | ✅ No regression |
| Workflow gates | §2 + §14 | §2 + §14 (both retained) | ✅ Dual-reference preserved |
| Auditor gate | 6 locations | 4 locations (consolidated) | ✅ Acceptable consolidation |
| Anti-pattern catalog | 7 categories | 7 categories | ✅ Complete |
| Reference tables | 3 tables | 3 tables | ✅ Complete |
| Bypass mode | Detailed | Condensed but complete | ✅ All mechanisms retained |
| Persona quote | Present | Present | ✅ Tenure marker preserved |
| Line count | 689 | 395 | ⚠️ Approaching nuance floor |
| Token efficiency | ~4K tokens | ~2.5K tokens | ✅ 37% savings |

---

## 11. Conclusion

The current AGENTS.md v2.1 scaffold rule is **governance-safe** with no regressions from v2.0 and 2 new BLOCKING rules that strengthen the audit trail. Any v4 update must satisfy the 26 safeguards listed in §9.

Three low-to-medium NEEDS REVIEW findings (F1-F3) are enhancement opportunities, not blockers. Five wording recommendations (W1-W5) should be incorporated during v4 implementation.

The v2.0→v2.1 condensation was well-executed: safety boundaries, BLOCKING rules, anti-pattern catalog, and workflow gates are all preserved. The main ongoing risk is line budget erosion — further condensation below ~350 lines risks losing nuance in safety-critical sections.

---

## 12. Footer

| Field | Value |
|---|---|
| **Source task** | Governance risk review — AGENTS.md scaffold rule for v4 |
| **Date** | 2026-06-01 |
| **Reviewer** | Guinevere (parent, read-only governance review) |
| **Method** | Direct file read (AGENTS.md full 395 lines) + cross-reference with 6 research/audit reports + v2.0 system-prompt baseline comparison |
| **Files read** | AGENTS.md (395 lines), 4 research reports, 2 audit reports, 1 prior verification |
| **Report path** | `docs/setup-evidence/agents-md-update-v4/research/governance-risk-review.md` |
| **Next action** | Parent reads this report before planning v4 scaffold rule; use §9 safeguards as v4 acceptance criteria |
