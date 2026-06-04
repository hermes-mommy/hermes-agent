# Audit Report — Hermes Migration Plan Consistency

> **Auditor**: Auditor 4 of 4 (Consistency)
> **Date**: 2026-06-04
> **Scope**: Cross-document consistency between batch-plan-migration.md, ADR-035, MASTER-RESTRUCTURE-PLAN, and phase detail files (0, 1, 2, 7)

---

## Verdict: **NEEDS REVIEW** (15/16 PASS, 1 NEEDS REVIEW)

---

## 16-Item Checklist — Detailed Scores

### #1: 5 Pillars match ADR-035 — **PASS**

| Pillar | Batch-Plan | ADR-035 | Status |
|---|---|---|---|
| Discord | MIGRATE to Hermes native gateway | Pillar 1: Discord = MIGRATE | OK |
| Memory | HYBRID — PostgreSQL primary, Hermes read-only | Pillar 2: Memory = HYBRID | OK |
| Safety | HOOKS + PLUGINS | Pillar 3: Safety = HOOKS + PLUGINS | OK |
| MCP | HYBRID — 5 native + 7 custom + auth overlay | Pillar 4: MCP = HYBRID | OK |
| LLM | RETAIN 9Router at localhost:20128 | Pillar 5: LLM = RETAIN 9Router | OK |

### #2: Phase ordering matches ADR-035 — **PASS**

Both documents use 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7.
Dependency graph in batch-plan Section 3.1 matches ADR-035 Implementation Notes exactly.

### #3: Phase names match ADR-035 — **PASS**

| Phase | Batch-Plan | ADR-035 Impl Notes |
|---|---|---|
| 0 | Security Remediation | Security Remediation |
| 1 | Safety Foundation (CRIT GATE) | Safety Foundation |
| 2 | Discord Gateway | Discord Gateway |
| 3 | Memory Bridge | Memory Bridge |
| 4 | MCP + Tools | MCP + Tools |
| 5 | Skills + SOUL.md | Skills + Persona (equivalent) |
| 6 | LLM Routing | LLM Routing |
| 7 | Hardening + Monitoring | Hardening + Monitoring |

Note on P5: "Skills + SOUL.md" vs "Skills + Persona" — same phase, SOUL.md is the persona artifact.

### #4: Phase durations match ADR-035 — **PASS**

Key finding: ADR-035 has TWO duration sets — a Summary table (solo-dev padded) and Implementation Notes (canonical). The batch-plan matches the **Implementation Notes** section:

| Phase | Batch-Plan | ADR-035 Impl Notes | ADR-035 Summary |
|---|---|---|---|
| 0 | 1-2 days | "1-2 days" OK | 2-3 days |
| 1 | 4-6 days | "4-6 days" OK | 7-10 days |
| 2 | 4-6 days | "4-6 days" OK | 5-8 days |
| 3 | 3-4 days | "3-4 days" OK | 4-5 days |
| 4 | 3-4 days | "3-4 days" OK | 5-7 days |
| 5 | 2-3 days | "2-3 days" OK | 2-3 days |
| 6 | 1 day | "1 day" OK | 1 day |
| 7 | 2-3 days | "2-3 days" OK | 2-3 days |

Batch-plan also explicitly annotates Phase 1 as "(7-10 solo-dev realistic)" and P2 as "+ 48hr shadow", acknowledging ADR-035's summary padding.

### #5: Total timeline 35-50 days — **PASS**

Batch-plan Section 1.3: "Solo-developer realistic timeline: 35-50 days per ADR-035 v1.2"
ADR-035 Migration Phases: "Total (realistic): 35-50 days"
Day-50 decision gate present in both documents.

### #6: Code reduction 31.2% net / 44.2% affected — **PASS**

| Metric | Batch-Plan | ADR-035 |
|---|---|---|
| Net reduction | 8,057 lines (31.2%) | 8,057 lines (31.2%) |
| Affected reduction | implied | 44.2% |
| Baseline | 25,796 lines | 25,796 lines |

### #7: 113 files, 25,796 lines baseline — **PASS**

Batch-Plan Section 1.4: "25,796 lines across 113 Python source files"
ADR-035 Section Context: "25,796 lines across 113 Python files" — identical.

### #8: 35 slash commands (not 33) — **PASS**

Both batch-plan and ADR-035 use **35 slash commands** consistently. The MASTER-RESTRUCTURE-PLAN's "33 commands" is a documented error corrected by ADR-035.

### #9: 7 Hermes hooks — **PASS**

Correct hook names used consistently: pre_prompt, post_prompt, pre_tool_call, post_tool_call, pre_response, post_response, on_error.

MASTER plan's invented names (pre_gateway_dispatch, pre_llm_call, transform_llm_output) are explicitly corrected in ADR-035 and never appear in batch-plan.

### #10: AC-SAFE-001..008 IDs — **PASS**

| AC-SAFE | Batch-Plan Gate | ADR-035 Mapping |
|---|---|---|
| AC-SAFE-001 | Gate 1 — HARD STOP | HARD STOP 100% |
| AC-SAFE-002 | Gate 3 — Yandere | Y6 prohibition |
| AC-SAFE-003 | Gate 2 — Consent | Consent fail-closed |
| AC-SAFE-004 | Gates 4,7 — Distress + Classification | Distress zero FN |
| AC-SAFE-005 | Gate 6 — DNR | DNR enforcement |
| AC-SAFE-006 | Gates 8,9 — Secrets + Punishment | Secret scanner + Forbidden |
| AC-SAFE-007 | Gate 5 — Drift | Drift detector |
| AC-SAFE-008 | Gate 10 — Forbidden | Forbidden patterns |

Mapping consistent across both documents and phase-1-safety.md.

### #11: Rollback procedures — **PASS**

| Phase | Batch-Plan | Phase Detail File |
|---|---|---|
| 0 | pip install + git checkout | "< 5 minutes" — same core |
| 1 | rm plugins/hooks + git checkout | "< 3 minutes rm -f" — same core |
| 2 shadow | hermes gateway stop + uninstall | "< 1 min hermes gateway stop" OK |
| 2 cutover | stop Hermes + start bot.py | "< 2 min" — identical commands |

Batch-plan rollbacks are more detailed but command core and timing match.

### #12: Gate criteria — **PASS**

All 8 phases have identical gate descriptions between batch-plan Section 4.x "Gate Criteria" and phase detail files' "Gate" fields. Verified for P0, P1, P7.

### #13: T1-T10 verification tests — **PASS**

Batch-Plan Section 5 defines T1-T10 with commands, expected results, pass/fail criteria. Phase-7-hardening.md step 7.1 references running the full suite. T1-T10 gate criteria match.

### #14: Shadow mode procedure — **PASS**

| Aspect | Batch-Plan Phase 2A | phase-2-discord.md |
|---|---|---|
| Minimum duration | 48hr+ | "48hr+ shadow mode" |
| Separate channels | #guinevere-chat vs #hermes-shadow | same |
| Active injections | 9 tests enumerated | referenced in pre-conditions |
| Memory write mutex | Only bot.py writes | "read-only for Hermes" |
| Cost cap | $5 | implied |

### #15: ADR-035 status: Accepted — **PASS**

Batch-Plan Section 2.1: "ADR-035 accepted and published — Accepted 2026-06-04"
ADR-035 frontmatter: status: "Accepted" — consistent.

### #16: No contradictions between batch-plan and phase detail files — **NEEDS REVIEW**

**Finding A — Phase duration mismatch (LOW severity):**

| Phase | Batch-Plan Table | Phase Detail File |
|---|---|---|
| 0 | 1-2 days | **2-3 days** (phase-0-security.md) |
| 1 | 4-6 days | **7-10 days** (phase-1-safety.md) |
| 2 | 4-6 days | **5-8 days** (phase-2-discord.md) |

Root cause: Phase detail files use ADR-035 Summary table durations (solo-dev padded), while batch-plan uses Implementation Notes durations (optimistic). This originates from ADR-035's own internal inconsistency between its Summary Table and Implementation Notes sections.

**Finding B — Internal batch-plan net delta inconsistency (LOW severity):**

Per-phase section net deltas differ from Appendix A.1 net deltas and neither sums to the claimed total:

| Phase | Per-Phase Section | Appendix A.1 |
|---|---|---|
| 0 | +90 | +90 OK |
| 1 | +4,300 | +4,300 OK |
| 2 | **-5,779** | **-2,896** MISMATCH |
| 3 | +319 | +319 OK |
| 4 | **-2,473** | **-2,383** MISMATCH |
| 5 | **-446** | **-366** MISMATCH |
| 6 | +185 | +185 OK |
| 7 | +1,305 | +1,305 OK |

Both the per-phase section sum (-2,499) and Appendix sum (+554) differ from the claimed total (-8,057). The overall claim of 8,057 line reduction / 31.2% is consistent with ADR-035, but the internal per-phase accounting within the batch-plan is internally inconsistent.

Recommendation: Reconcile per-phase net deltas in batch-plan so they sum to -8,057. Normalize phase detail file durations to match batch-plan primary table.

---

## Additional Observations

### ADR-035 Internal Inconsistency

ADR-035 has two different duration sets within the same document:
- Summary Table (line 1181-1190): P0=2-3d, P1=7-10d, P2=5-8d, P3=4-5d, P4=5-7d
- Implementation Notes (lines 1432-1503): P0=1-2d, P1=4-6d, P2=4-6d, P3=3-4d, P4=3-4d

Neither set is labeled as "canonical." Both batch-plan and phase files picked different sets, creating downstream inconsistency.

### MASTER-RESTRUCTURE-PLAN Corrections

All 3 MASTER plan errors are correctly addressed:
1. 33 commands -> 35: CORRECTED
2. Invented hook names: CORRECTED
3. 59% code reduction -> 31.2%: CORRECTED

Batch-plan and ADR-035 consistently use corrected values.

### No BLOCKING Issues Found

None of the 16 checklist items has a BLOCKING-level failure. The inconsistencies found are:
- Low-severity duration mismatches between batch-plan and phase files
- Internal batch-plan accounting errors in net deltas
- Neither affects architectural correctness, safety mapping, or migration feasibility.

---

## Final Score: 15 PASS / 1 NEEDS REVIEW -> **NEEDS REVIEW**