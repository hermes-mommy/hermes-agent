# Audit Report: Test Completeness in batch-plan-phase-7.md

**Auditor**: 7-1 (Test Completeness)
**Date**: 2026-06-05
**Subject**: docs/setup-evidence/hermes-migration/batch-plan-phase-7.md
**Phase**: Phase 7 (Hardening) - ADR-035 Hermes Migration
**Status**: NEEDS REVIEW

---

## Sources Reviewed

| Source | Path |
|---|---|
| Batch Plan | docs/setup-evidence/hermes-migration/batch-plan-phase-7.md (1,399 lines) |
| ADR-029 Tests Research | esearch-reports/phase-6-7-planning/07-adr029-tests.md (162 lines) |
| ADR-029 (Self-Modification Automated Testing) | dr/ADR-029-self-modification-automated-testing.md (181 lines) |
| pyproject.toml | pyproject.toml (51 lines) |
| Test files inventory | 79 test files across 	ests/ directory |

---

## Checklist 1: T1-T10 All Covered?

### Summary

| # | Test | pytest Command Defined? | Test File Exists? | Result |
|---|---|---|---|---|
| T1 | Basic Conversation | YES (Step 7.1.3, line 199) | NO - \	ests/integration/test_t1_basic_conversation.py\ does not exist | FAIL |
| T2 | Multi-Turn Memory | YES (Step 7.1.3, line 207) | NO - \	ests/integration/test_t2_multi_turn_memory.py\ does not exist | FAIL |
| T3 | MCP Tools | YES (Step 7.1.3, line 215) | NO - \	ests/integration/test_t3_mcp_tools.py\ does not exist | FAIL |
| T4 | HARD STOP < 50ms | YES (Step 7.1.3, line 223) | NO - \	ests/integration/test_t4_hard_stop.py\ does not exist | FAIL |
| T5 | Safe Mode | YES (Step 7.1.3, line 231) | NO - \	ests/integration/test_t5_safe_mode.py\ does not exist | FAIL |
| T6 | Memory Recall | YES (Step 7.1.3, line 239) | NO - \	ests/integration/test_t6_memory_recall.py\ does not exist | FAIL |
| T7 | 35 Slash Commands | YES (Step 7.1.3, line 247) | NO - \	ests/integration/test_t7_slash_commands.py\ does not exist | FAIL |
| T8 | Rituals 5x/day | YES (Step 7.1.3, line 255) | NO - \	ests/integration/test_t8_rituals.py\ does not exist | FAIL |
| T9 | Cost Tracking | YES (Step 7.1.3, line 263) | NO - \	ests/integration/test_t9_cost_tracking.py\ does not exist | FAIL |
| T10 | Surveillance Pipeline | YES (Step 7.1.3, line 271) | NO - \	ests/integration/test_t10_surveillance.py\ does not exist | FAIL |

### Detailed Evidence

Each T1-T10 test has an exact pytest command defined in Step 7.1.3 (lines 199-275). For example:

\\\ash
python -m pytest tests/integration/test_t1_basic_conversation.py -v --tb=short 2>&1
python -m pytest tests/integration/test_t4_hard_stop.py -v --tb=short 2>&1
\\\

However, none of these test files exist:
- The \	ests/integration/\ directory does not exist anywhere in the repository.
- No \	est_t[1-10]_*.py\ files exist in any \	ests/\ subdirectory.
- Step 7.1.4 creates \	ests/integration/test_verification.py\ with a V01-V30 test matrix (Service Health, Database, LLM Routing, Safety Features, Monitoring, Backup) - this is a completely different suite from T1-T10.
- There is no plan or step to create the T1-T10 dedicated test files.
- No mapping is provided between T1-T10 requirements and existing test files.

Running these commands will produce ModuleNotFoundError or FAILED (no tests collected).

### T1-T10 Sub-Verdict

**FAIL**

---

## Checklist 2: ADR-029 Satisfied?

### 2.1 Auto-Rollback on Test Failure < 60s

| Requirement | Batch Plan Coverage | Evidence |
|---|---|---|
| Automated git revert on test failure | NOT PLANNED | Section 16 (Rollback Plan) covers only manual emergency rollback procedures. No automated git revert mechanism defined. |
| Rollback must complete within 60 seconds | NOT TESTED | No rollback simulation test (test_auto_rollback.py) planned. |
| Rollback events logged and alert via Discord | NOT ADDRESSED | No Discord alerting mechanism for rollback events defined. |

Research report 07-adr029-tests.md section 7.1 gap 3 confirms: "No Rollback Testing - ADR-029 mandates a 60-second git revert rollback, but there are no tests simulating deployment failure and verifying the rollback mechanism."

**Result: FAIL**

### 2.2 Safety-Critical Change Classification

| Requirement | Batch Plan Coverage | Evidence |
|---|---|---|
| Define .guinevere/safety-critical-paths.yml | NOT PLANNED | This file does not exist in the repo. No step creates it. |
| Glob patterns for safety-critical files | NOT DEFINED | No classification configuration anywhere. |

Research report 07-adr029-tests.md section 7.1 gap 4 confirms: "Safety-Critical Path Classification - this file does not exist in the repo."

ADR-029 Implementation Notes: "Safety-critical file paths must be defined in a configuration file (e.g., .guinevere/safety-critical-paths.yml)"

**Result: FAIL**

### 2.3 Test Pass Threshold Defined

| Requirement | Batch Plan Coverage | Evidence |
|---|---|---|
| All unit tests must pass | PARTIAL | Gate G01 (line 1171): "All tests PASS" - binary PASS/FAIL at suite level, not by category. |
| All integration tests must pass | PARTIAL | Same - no per-category threshold. |
| No regression in existing test coverage | PARTIAL | Step 7.1.5 checks coverage < 70% but as a fallback, not a hard gate. |
| Safety-critical file change detection | NOT DEFINED | No pre-commit check or CI gate for safety-critical file modifications. |

ADR-029 requires: "All unit tests pass", "All integration tests pass", "No regression in existing test coverage."

**Result: NEEDS_REVIEW** (partial coverage, missing per-category thresholds)

### 2.4 .coveragerc or Coverage Config Created

| Requirement | Batch Plan Coverage | Evidence |
|---|---|---|
| .coveragerc file exists | NO | No .coveragerc file exists anywhere in the repository. |
| Coverage config in pyproject.toml | NO | pyproject.toml [tool.pytest.ini_options] has no addopts for coverage. No [tool.coverage.run] section. |
| Step to create coverage config | NOT PLANNED | Step 7.1.5 uses inline --cov=src flag only - no persistent configuration. |

Rollback plan line 1268: rm -f .coveragerc - this implies a .coveragerc is expected to exist at rollback time, but no step ever creates it.

**Result: FAIL**

### ADR-029 Sub-Verdict

**FAIL**

---

## Checklist 3: Regression Suite Complete?

| Item | Status | Evidence |
|---|---|---|
| pytest tests/ command included | PASS | Step 7.1.2 (line 174-178): python -m pytest tests/ -v --tb=short --durations=20 |
| Expected output documented | PASS | Step 7.1.2 (line 182): "2772 passed, 0 failed, 0 errors" |
| --run-e2e flag pattern | NEEDS_REVIEW | The --run-e2e / RUN_E2E=1 pattern exists in tests/surveillance/test_e2e.py (line 42-43) but is NOT referenced in the batch plan. E2E tests could be missed if the flag is required. |
| Coverage report generation | PASS | Step 7.1.5 (line 315-334): --cov=src --cov-report=term-missing --cov-report=html:... with HTML output and failure handling for < 70% coverage. |

### Regression Suite Sub-Verdict

**PASS** (with minor note on --run-e2e flag not being referenced in the batch plan commands)

---

## Checklist 4: Performance Baselines Set?

| Performance SLO | Status | Measurement Methodology | Evidence |
|---|---|---|---|
| Response latency < 5s p95 | PASS | 100 iterations via subprocess.run to 9Router /v1/chat/completions, collects min/max/mean/p50/p95/p99. Assertion: p95 < 5.0 | Step 7.4.1 (lines 655-686), Gate G03 |
| HARD STOP < 50ms p99 | PASS | perf_counter_ns 100 iterations, Python subprocess regex detection. Assertion: p99_ms < 50 | Step 7.4.2 (lines 688-715), Gate G03 |
| Memory recall < 2s p95 | PASS | python -m scripts.bench_memory --mode live --iterations 50. Script exists at scripts/bench_memory.py | Step 7.4.3 (lines 718-725), Gate G03 |
| Benchmark methodology documented | PASS | Baseline comparison (Step 7.4.4), JSON recording with thresholds (Step 7.4.5), SLO definitions (Section 13), Gate G03 | Lines 727-778, Section 13, Section 15 |

### Performance Baselines Sub-Verdict

**PASS**

---

## Checklist 5: Structural Completeness - Missing Sections 8-11

| Section | TOC Reference | Body Exists? | Evidence |
|---|---|---|---|
| ## 8. Step 7.6: Deprecated Files Cleanup | Line 22 | NO | Lines 922-924 show document jumps from ## 7. Step 7.5: Security Audit directly to ## 12. Section: Runbook per Scenario. Sections 8, 9, 10, 11 are completely absent. |
| ## 9. Step 7.7: ADR-029 Automated Tests | Line 23 | NO | Directly relevant to this audit - no implementation steps exist. |
| ## 10. Step 7.8: Final Backup | Line 24 | NO | No backup steps defined beyond rollback reference. |
| ## 11. Step 7.9: Documentation Update | Line 25 | NO | No doc update steps defined. |

The ADR-029 work is mentioned in:
- Executive summary (line 48): references .coveragerc config, CI/CD docs, self-modification scenarios
- Risk register R7-15 (line 1318): "ADR-029 SM tests fail on CI"
- Rollback plan (line 1268): removes .coveragerc
- Evidence artifacts table (line 1348): lists Step 7.7 expected outputs

But no implementation section exists for any of these 4 steps.

### Structural Sub-Verdict

**FAIL**

---

## Cross-Cutting Issues

### Issue A: T1-T10 vs V01-V30 Mismatch

The batch plan defines two separate verification suites:

| Aspect | T1-T10 (Step 7.1.3) | V01-V30 (Step 7.1.4) |
|---|---|---|
| Focus | Conversation, Memory, MCP, HARD STOP, Safe Mode, Slash Commands, Rituals, Cost, Surveillance | Service Health, Database Connectivity, LLM Routing, Safety Features, Monitoring, Backup |
| Target files | tests/integration/test_t[1-10]_*.py | tests/integration/test_verification.py |
| Files exist? | NO | NO (to be created) |
| Relationship | Not explained | Not explained |

Neither suite maps to existing tests. There is no documented relationship between the two.

### Issue B: No Consistent Test File Creation Strategy

- T1-T10 commands reference dedicated files that don't exist
- V01-V30 is created as a single file in Step 7.1.4 but the creation logic is placeholder-level (just echoes "Created" rather than writing real test code)
- Step 7.1.4 uses a template approach that reads from /tmp/test_verification_template.txt if it exists - fragile

### Issue C: ADR-029 Step 7.7 Missing Despite Being Central to This Audit

The single most relevant section for ADR-029 compliance (Step 7.7) does not exist. The evidence artifacts table (line 1348) expects outputs including coverage-summary.txt, coverage-html/, coverage.xml, and adr029-cicd-integration.md from Step 7.7, but since the section is missing, none will be created.

### Issue D: Coverage Baseline Not Established

ADR-029 requires "no regression in existing test coverage" but:
- No .coveragerc or coverage config exists to establish a baseline
- The Step 7.1.5 --cov run is a one-time measurement, not a persisted baseline
- Without a stored baseline, regression detection is impossible

---

## FINAL VERDICT

\\\
╔══════════════════════════════════════════════════════════════╗
║                     FINAL VERDICT                            ║
║                                                              ║
║                    NEEDS REVIEW                               ║
║                                                              ║
║  Checklist Results:                                          ║
║    1. T1-T10 Coverage:          FAIL                         ║
║    2. ADR-029 Satisfied:        FAIL                         ║
║    3. Regression Suite:         PASS (minor note)            ║
║    4. Performance Baselines:    PASS                         ║
║    5. Missing Sections 7.6-7.9: FAIL                         ║
║                                                              ║
║  3 FAIL verdicts - Cannot be PASS                             ║
╚══════════════════════════════════════════════════════════════╝
\\\

### Required Fixes Before PASS

#### Critical (blocking - all must be addressed)

1. **Create missing Sections 8-11** in batch-plan-phase-7.md, especially Step 7.7 (ADR-029 Automated Tests) with concrete steps for:
   - Creating .coveragerc or adding [tool.coverage.run] to pyproject.toml
   - Creating .guinevere/safety-critical-paths.yml with glob patterns
   - Creating tests/safety/test_auto_rollback.py for git revert rollback simulation within 60s
   - Defining CI/CD integration documentation

2. **Resolve T1-T10 vs V01-V30 mismatch**: Either create dedicated tests/integration/test_t[1-10]_*.py files or remap T1-T10 commands to existing test files and document the mapping.

#### High

3. **Implement ADR-029 auto-rollback mechanism**: Define automated git revert with < 60s SLA, Discord alerting, and a simulation test.

4. **Add .coveragerc or pyproject.toml coverage configuration** with a persisted baseline for regression detection.

#### Medium

5. **Define test pass thresholds per category** (unit vs integration) as required by ADR-029.

6. **Reference --run-e2e flag** in batch plan regression suite documentation.

7. **Replace placeholder V01-V30 creation logic** with actual test code or a real template.

---

## Evidence Artifacts for This Audit

| Artifact | Path |
|---|---|
| Batch Plan (Phase 7) | docs/setup-evidence/hermes-migration/batch-plan-phase-7.md |
| ADR-029 Research Report | research-reports/phase-6-7-planning/07-adr029-tests.md |
| ADR-029 Document | adr/ADR-029-self-modification-automated-testing.md |
| pyproject.toml | pyproject.toml |
| Bench Memory Script | scripts/bench_memory.py |
| Existing E2E Test (with --run-e2e) | tests/surveillance/test_e2e.py |
| Test Count Inventory | 79 files across tests/ directory |

---

*End of Audit Report - Auditor 7-1*
