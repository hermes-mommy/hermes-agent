# ADR-035 Compliance Audit — Phase 4 Batch Plan

> **Audit Type**: PLANNING audit (pre-implementation)  
> **Audit Target**: `docs/setup-evidence/phase-4/batch-plan-phase-4.md`  
> **Source of Truth**: `adr/ADR-035-hermes-migration.md` v1.3 (Accepted)  
> **Date**: 2026-06-05  
> **Auditor**: ADR-035 Compliance Auditor  

---

## VERDICT: NEEDS REVIEW

The batch plan demonstrates strong alignment with ADR-035 Pillar 4 in its core substance (architecture, risk mitigation, auth overlay design, fail-open handling). However, **7 specific findings** require resolution before the plan can achieve PASS status — 3 are CONDITIONAL (blocking only under specific conditions), 4 are ADVISORY (should fix before implementation). No FAIL-level finding was identified.

**Bottom line**: The plan is implementation-ready for execution but needs 3 pre-flight fixes and 4 documentation clarifications. Primary concern is the Phase 3 dependency (F-004) which ADR-035 does not require.

---

## Section 1: Requirement-to-Step Traceability

| ADR-035 Requirement | Source | Batch Plan Step | Status | Notes |
|---|---|---|---|---|
| Phase 4 total scope (5-7 days) | line 1597 | 8 steps, 5 waves | PASS | All 6 ADR steps mapped + 2 justified additions |
| 4.1: Add 5 Hermes native MCP servers | line 1601 | P4-001 (3hr) | PASS | web, filesystem, terminal, git, fetch |
| 4.2: Build auth overlay plugin | line 1602 | P4-002 (12hr) | PASS | Full plugin arch, 4-level routing |
| 4.3: Migrate 4 hybrid tools | line 1603 | P4-004 (6hr) | PASS | shell/docker/git/github mapped to terminal+plugin guards |
| 4.4: Keep 7 custom MCP tools | line 1604 | P4-005 (2hr) | NEEDS REVIEW | 7 tools correct; op-list inflated to 24 names (F-002) |
| 4.5: Plugin load gate test | line 1605 | P4-006 (3hr) | PASS | Startup gate enforces fail-closed |
| 4.6: Security audit all 16 tools | line 1606 | P4-007 (4hr) | PASS | 14 audit checks, YAML/Python parity |
| Budget enforcement (R-010) | Risk line 1314 | P4-003 (4hr) | NEEDS REVIEW | Not in Phase 4 expanded steps (F-001a) |
| Integration test suite | — | P4-008 (4hr) | NEEDS REVIEW | Not in ADR-035 Phase 4 steps (F-001b) |
| Auth matrix YAML config | Appendix B (2216-2301) | P4-001 config.yaml | NEEDS REVIEW | Granularity mismatch with auth_matrix.py (F-003) |
| Rollback: auth overlay failure | line 1612 | Section 14 | PASS | Exact match: `hermes mcp remove` + `rm -f plugins/auth_overlay.py` |
| Phase 4 dependency: Phase 2 | line 1608 | Section 3 preamble | NEEDS REVIEW | Batch plan adds Phase 3 dependency (F-004) |
| Duration: 5-7 days | line 1597 | 38hr / ~6hr/day = ~6.3d | PASS | Fits within 5-7 day window |
| Hermes fail-open finding | line 1141, R4-007 | Section 17 Addendum | PASS | Correctly documented with startup gate + runtime fail-closed mitigation |

---

## Section 2: Scope Analysis

### 2.1 Scope Creep Items (Plan includes things ADR-035 doesn't specify)

| # | Item | Step | Severity | Finding |
|---|---|---|---|---|
| **F-001a** | Budget enforcement (Redis Lua hook) | P4-003 | CONDITIONAL — JUSTIFIED | Not in ADR-035 Phase 4 expanded steps. However, it mitigates R-010: "Custom pre_tool_call hook checks cumulative cost. Alerts at 80% ($24), blocks at 100% ($30)." No phase is assigned in the risk register, but `pre_tool_call` hook is unambiguously Phase 4 territory. Adds 4hr — does not exceed 7-day window. **Verdict: Acceptable scope expansion with clear rationale.** |
| **F-001b** | End-to-end integration test suite | P4-008 | ADVISORY | Not in ADR-035 Phase 4 steps. 4hr of E2E testing across all 16 tools is pragmatic quality assurance. Does not contradict ADR-035. No explicit ADR rule prohibits post-implementation testing. **Verdict: Retain as optional/can-defer step.** |
| **F-004** | Phase 3 (Memory Bridge) dependency | Section 3 preamble | CONDITIONAL — SHOULD REMOVE | ADR-035 line 1608: "Phase 2 must pass (Discord cutover complete). FastMCP server must still be running for custom tools. Auth matrix config must be deployed." **Phase 3 is NOT listed.** Adding it unnecessarily gates Phase 4 on Memory Bridge completion. If Phase 3 encounters delays, Phase 4 is blocked despite having no technical dependency on memory functionality. **Action: Change dependency to Phase 2 only, or file ADR-035 amendment justifying Phase 3 dependency.** |

### 2.2 Scope Deficit Items (ADR-035 specifies things plan doesn't cover)

| # | Item | Missing Coverage | Severity |
|---|---|---|---|
| **F-002** | Custom tool operation inflation | P4-005 `fastmcp_custom` tool list expands 7 custom tools into 24 named entries (postgres_query, postgres_tables, postgres_describe, redis_get, redis_keys, redis_hgetall, redis_lrange, redis_set, redis_hset, redis_del, obscura_navigate, obscura_get_markdown, obscura_fill_form, obscura_click, grep_app_search, context7_resolve, context7_query, sequential_think, current_time, convert_time, days_in_month, relative_time, get_timestamp, get_week_year). ADR-035 Pillar 4 counts exactly 16 tools total (7 custom + 5 native + 4 hybrid). The 24 entries are sub-operations exposed by Hermes MCP transport — NOT separate tools. **Action: Add explicit annotation that the 24 entries are sub-operations of 7 canonical tools, and that P4-007 audit check #1 verifies the collapse from 24 to 16.** | ADVISORY |
| **F-005** | NFR-P05 (tool execution latency) | No baseline comparison framework for tool latency. NFR-P05 target: "Within +10% of baseline." Batch plan P4-008 checks native tool latency < 5s but has no baseline measurement mechanism and no comparison logic. **Action: Add a baseline latency capture step to P4-007 audit checklist, and add +10% comparison to P4-008 test assertions.** | ADVISORY |

---

## Section 3: Binding Decision Validation

| # | Batch Plan BD | ADR-035 Intent | Verdict |
|---|---|---|---|
| BD-001 | Auth overlay as SEPARATE Hermes plugin | line 1141: "Auth overlay plugin: Built as a Hermes plugin that intercepts pre_tool_call hook." Separate from guinevere_safety. | PASS — Correct separation of concerns |
| BD-002 | Custom startup wrapper for critical:true | line 1610: "Auth overlay plugin is loaded as critical: true — Hermes refuses to start without it." R4-007 discovered this flag is NOT native Hermes v0.15.2. | PASS — Correctly identifies the gap and proposes equivalent fail-closed semantics |
| BD-003 | Redis Lua script for atomic budget check | R-010: "Custom pre_tool_call hook checks cumulative cost. Alerts at 80% ($24), blocks at 100% ($30)." | PASS — Lua atomicity is implementation detail consistent with risk mitigation intent |
| BD-004 | FastMCP retained as stdio backend | line 1604: "Keep 7 custom MCP tools ... src/mcp/tools/ (unchanged)" | PASS — Zero code changes to tool implementations |
| BD-005 | Hybrid tool safety via Hermes config + plugin | line 1603: "shell -> terminal+blocking, docker -> terminal+whitelist, git/github -> native+auth" | PASS — Hybrid guards supplement native terminal security |
| BD-006 | Dual source-of-truth (YAML + Python) | Appendix B auth_matrix.yaml as Hermes config + auth_matrix.py as FastMCP registry | NEEDS REVIEW — Concept is sound (Hermes reads YAML, FastMCP reads Python). But Appendix B auth_matrix.yaml and auth_matrix.py show different operation granularities. E.g., ADR-035 postgres_tool has 7 named ops (select/insert/update/delete/ddl/drop/pg_dump), while auth_matrix.py postgres has 16 operations under READ_AUTO(2)+FORBIDDEN(5). Similarly, redis_tool: 5 ops in ADR-035 vs 28 in auth_matrix.py. P4-007 audit is tasked with verifying parity — but ADR-035 does not specify which matrix is authoritative for the canonical set of per-tool operations. **Action: Declare YAML (Appendix B) as canonical for Hermes-facing tools, with auth_matrix.py as the matching Python mirror. P4-001 should ensure config.yaml auth_matrix section matches Appendix B granularity exactly.** |
| BD-007 | Budget thresholds: Warning $24 (80%), Block $30 (100%) | FinOps v1.1 Section 4.1.4: $30/month hard cap. R-010: "Alerts at 80% ($24), blocks at 100% ($30)." | PASS — Consistent with both ADR-035 risk register and FinOps v1.1 budget ceiling |

---

## Section 4: Risk Register Coverage

### 4.1 R-004: Auth Matrix Bypass (Score 15 — HIGH)

| Mitigation in ADR-035 | Batch Plan Coverage | Status |
|---|---|---|
| Plugin load gate (Hermes refuses to start without it) | P4-006 startup gate wrapper | PASS |
| FORBIDDEN tools hard-disabled in Hermes config | P4-001 config.yaml + P4-002 forbidden_handler.py | PASS |
| Independent audit daemon verifies plugin presence every 60s | Not explicitly in batch plan. ADR-035 mentions this but batch plan P4-006 is startup-only (not runtime daemon). | GAP — Consider adding runtime watchdog to P4-006 or noting as Phase 7 (Hardening) task |

### 4.2 R-010: Budget Enforcement Gap (Score 9 — HIGH)

| Mitigation in ADR-035 | Batch Plan Coverage | Status |
|---|---|---|
| Custom pre_tool_call hook checks cumulative cost | P4-003 budget_check.py hook | PASS |
| Alerts at 80% ($24), blocks at 100% ($30) | P4-003 Lua script: WARNING at $24, BLOCKED at $30 | PASS |
| Tested at 80%, 90%, 100% thresholds | P4-003 scaffold: tests/hermes/test_budget_hook.py | PASS |

### 4.3 R-014: Tool Isolation Failure (Score 8 — MEDIUM)

| Mitigation in ADR-035 | Batch Plan Coverage | Status |
|---|---|---|
| FORBIDDEN commands hard-disabled in Hermes config | P4-004 config.yaml terminal.blocked_commands + git.blocked_operations | PASS |
| Auth overlay plugin blocks destructive patterns | P4-004 hybrid_guards.py shell injection/Docker net/git force-push | PASS |
| Independent audit daemon verifies tool config | Same gap as R-004 — runtime watchdog not addressed in batch plan | GAP — Same note as R-004 |

---

## Section 5: Prerequisite Gate Validation

| Prerequisite | ADR-035 Spec (line 1608) | Batch Plan (Section 3) | Compliance |
|---|---|---|---|
| Phase 2 must pass | "Phase 2 must pass (Discord cutover complete)" | Required | PASS |
| FastMCP server running | "FastMCP server must still be running for custom tools" | P4-005 verifies systemctl status | PASS |
| Auth matrix config deployed | "Auth matrix config must be deployed" | P4-001 configures auth_matrix section | PASS |
| Phase 3 (Memory Bridge) | NOT specified in ADR-035 | ADDED in batch plan | NEEDS REVIEW — See F-004 |

---

## Section 6: Duration Estimate Validation

| Metric | ADR-035 | Batch Plan | Analysis |
|---|---|---|---|
| Total estimate | 5-7 days | 38 hours | 38 / 6hr-day = 6.3 days — within bounds |
| 4.1 native MCP | 3 hr | 3 hr | Exact match |
| 4.2 auth overlay | 12 hr | 12 hr | Exact match |
| 4.3 hybrid tools | 6 hr | 6 hr | Exact match |
| 4.4 custom tools | 2 hr | 2 hr | Exact match |
| 4.5 load gate | 1 hr | 3 hr (+2hr) | Expanded for startup wrapper complexity |
| 4.6 security audit | 4 hr | 4 hr | Exact match |
| P4-003 budget | — | 4 hr | Addition (F-001a) |
| P4-008 integration | — | 4 hr | Addition (F-001b) |
| **Total addition** | — | **+8 hr** | Stays within 5-7 day window only if >5.3hr/day |

---

## Section 7: FinOps Threshold Validation

| Threshold | FinOps v1.1 Reference | Batch Plan (P4-003) | Status |
|---|---|---|---|
| Warning threshold | Section 4.3: "Category >80% of its monthly allotment" | $24 (80% of $30) | PASS — Matches 80% rule |
| Block threshold | Section 2.2: "$30/month hard cap" | $30 (100%) | PASS — Matches hard cap |
| Budget method | Section 4.3: "Daily burn above trendline — Investigate" | Redis Lua atomic check | PASS — Atomicity prevents race conditions |
| LLM cost tracking | Section 5: Token budget policy separate from tool costs | GAP-005 explicitly deferred to Phase 6 | PASS — Correct scoping |

---

## Section 8: Rollback Procedure Validation

| Procedure | ADR-035 (line 1612) | Batch Plan (Section 14) | Compliance |
|---|---|---|---|
| Trigger | "auth overlay plugin fails to load OR any tool bypasses auth matrix" | Scenario-based rollback + full Phase 4 rollback | PASS — Batch plan is more detailed but consistent |
| Commands | `hermes mcp remove web filesystem terminal git fetch` + `rm -f plugins/auth_overlay.py` + restart FastMCP | Full Phase 4 rollback matches + adds hook cleanup and systemd revert | PASS — Additive, not contradictory |
| Time | < 2 min | < 5 min | PASS — More conservative estimate |
| Data impact | None (code + config + plugin files only) | "No destructive modifications to existing production code" | PASS — Consistent |

**Universal kill-switch**: Batch plan does not explicitly mention `hermes gateway stop` as the first rollback step (ADR-035 line 1416: "Every rollback starts with hermes gateway stop"). Section 14 rollback procedures skip this prefix. **Action: Add `hermes gateway stop` as the first command in every rollback procedure in Section 14.**

---

## Section 9: 16-Tool Accounting

### Migration Category Distribution

| Category | Count | Tools | Batch Plan Coverage |
|---|---|---|---|
| Native (MIGRATE to Hermes) | 5 | brave_search, exa_search, fetch, websearch, filesystem | P4-001 web + filesystem servers |
| Hybrid (Hermes terminal + guards) | 4 | shell_tool, docker_tool, git_tool, github | P4-004 hybrid_guards.py + P4-001 terminal/git |
| Custom (KEEP on FastMCP) | 7 | postgres_tool, redis_tool, obscura_cdp, grep_app, context7, sequential_thinking, time_tools | P4-005 FastMCP verification |
| **Total** | **16** | | All 16 accounted |

### Custom Tool Operation Mapping

| Canonical Tool | ADR-035 Name | P4-005 Operations Listed | Count | Match |
|---|---|---|---|---|
| Postgres | postgres_tool | postgres_query, postgres_tables, postgres_describe | 3 | OK (sub-operations) |
| Redis | redis_tool | redis_get, redis_keys, redis_hgetall, redis_lrange, redis_set, redis_hset, redis_del | 7 | OK (sub-operations) |
| Obscura CDP | obscura_cdp | obscura_navigate, obscura_get_markdown, obscura_fill_form, obscura_click | 4 | OK (sub-operations) |
| Grep App | grep_app | grep_app_search | 1 | OK |
| Context7 | context7 | context7_resolve, context7_query | 2 | OK |
| Sequential Thinking | sequential_thinking | sequential_think | 1 | OK |
| Time Tools | time_tools | current_time, convert_time, days_in_month, relative_time, get_timestamp, get_week_year | 6 | Inflated — ADR-035 treats time_tools as 1 tool |
| **Total listed** | **7 canonical** | **24 operations** | | F-002 |

---

## Section 10: NFR Coverage for Phase 4

| NFR | Target | Batch Plan Coverage | Status |
|---|---|---|---|
| NFR-P05 | Tool execution latency: Within +10% of baseline | Partial — P4-008 checks latency < 5s for native tools only. No baseline capture or comparison logic. | NEEDS REVIEW (F-005) |
| NFR-S04 | Auth matrix enforcement: All tools gated | P4-002 auth overlay plugin + P4-007 audit check #2-#5 | PASS |
| NFR-S05 | Tool isolation: No bypass possible | P4-004 hybrid guards + P4-006 startup gate + P4-007 audit check #8-#13 | PASS |
| NFR-CP03 | MCP compatibility: All 16 functional | P4-007 audit check #12 + P4-008 integration tests | PASS |

---

## Section 11: ADDENDUM — CRITICAL Finding Validation

The batch plan Section 17 Addendum correctly documents the R4-007 finding:

> **"R4-007 discovered that `critical: true` and `on_failure: block` are NOT native Hermes v0.15.2 plugin flags."**

**Validation**: This finding is TRUE. ADR-035 line 1610 states: "Auth overlay plugin is loaded as `critical: true`" — but Hermes v0.15.2 catches plugin errors, logs them, and continues. The batch plan mitigation is two-layered:

1. **Startup gate (P4-006)**: Pre-flight validation refuses to start Hermes if critical plugins fail.
2. **Runtime fail-closed (P4-002)**: Auth overlay catches ALL exceptions and returns `{"action": "block"}` — even if Hermes considers the plugin "failed", the last successful hook return is "block".

**Verdict**: Correctly identified, correctly mitigated. The recommendation to file an ADR-035 amendment is appropriate.

---

## Section 12: Complete Findings Index

| # | Finding | Severity | Action Required |
|---|---|---|---|
| **F-001a** | P4-003 (Budget Enforcement) not in ADR-035 Phase 4 steps | CONDITIONAL — JUSTIFIED | Accept as R-010 mitigation. No action needed. |
| **F-001b** | P4-008 (Integration Tests) not in ADR-035 Phase 4 steps | ADVISORY | Mark as optional/deferrable if Phase 4 exceeds 7 days. |
| **F-002** | P4-005 tool list inflates 7 custom tools to 24 named entries | ADVISORY | Add annotation that 24 entries collapse to 7 canonical tools. P4-007 audit should verify the collapse. |
| **F-003** | Auth matrix granularity mismatch between Appendix B and auth_matrix.py | ADVISORY | Declare canonical source (YAML = Hermes, Python = FastMCP). P4-001 should ensure config.yaml auth_matrix matches Appendix B. |
| **F-004** | Phase 3 added as dependency (ADR-035 only requires Phase 2) | CONDITIONAL — SHOULD REMOVE | Change dependency to Phase 2 only, or file ADR-035 amendment. |
| **F-005** | NFR-P05 latency baseline not addressed | ADVISORY | Add baseline capture to P4-007 audit or P4-008 test assertions. |
| **F-006** | Rollback procedures omit `hermes gateway stop` prefix | ADVISORY | Add universal kill-switch as first command in every Section 14 rollback scenario. |
| **F-007** | Runtime watchdog daemon (60s plugin presence check) from R-004/R-014 mitigations not in batch plan | ADVISORY | Defer to Phase 7 (Hardening) or add as post-execution todo with explicit note. |

---

## Section 13: Final Assessment

### Strengths
- Core architecture (auth overlay, hybrid tool porting, custom tool retention) matches ADR-035 exactly
- All 16 tools accounted for with correct migration categories
- Risk mitigations for R-004, R-010, R-014 are substantively addressed
- Hermes fail-open model is correctly identified and mitigated
- Duration estimate fits ADR-035 5-7 day window
- Rollback procedures are consistent with ADR-035 (with minor F-006 fix)
- Budget thresholds ($24/$30) match FinOps v1.1 and R-010

### Required Pre-Implementation Fixes
1. **F-004** (CONDITIONAL): Remove Phase 3 dependency or file ADR-035 amendment
2. **F-006** (ADVISORY): Add `hermes gateway stop` prefix to all Section 14 rollback procedures
3. **F-002** (ADVISORY): Annotate P4-005 24-entry tool list as sub-operations of 7 canonical tools

### Recommended Improvements (Not Blocking)
4. **F-003**: Clarify canonical auth matrix source (YAML vs Python)
5. **F-005**: Add NFR-P05 latency baseline to audit/test suite
6. **F-007**: Note runtime watchdog daemon as Phase 7 deferred item
7. **F-001b**: Mark P4-008 as optional if schedule tightens

---

## Section 14: Footer

| Field | Value |
|---|---|
| Audit Type | ADR-035 Compliance — Planning Audit |
| Audit Target | `docs/setup-evidence/phase-4/batch-plan-phase-4.md` v1.0 |
| Documents Reviewed | ADR-035 v1.3 (full), FinOps v1.1, MCP Config Guide v1.0, 8 research reports (R4-001 through R4-008) |
| Verification Method | Cross-referenced every ADR-035 Pillar 4 requirement, Appendix B auth matrix, risk register entries, NFR table, and rollback procedures against batch plan |
| Auditor Signature | ADR-035 Compliance Auditor — Guinevere (consultant agent) |
| Audit Date | 2026-06-05 |
