# Phase 5 Verification Execution Plan — Full T1-T10 End-to-End

**Plan ID:** phase5-verification-plan
**Date:** 2026-06-07
**Author:** Guinevere (parent orchestrator)
**Status:** DRAFT — ready for parent read
**Evidence Root:** `docs/setup-evidence/phase5-verification/`
**Research Inputs:**
- `research-reports/phase5-verification/01-services-baseline.md`
- `research-reports/phase5-verification/02-discord-status.md`
- `research-reports/phase5-verification/03-memory-state.md`
- `research-reports/phase5-verification/04-safety-gates.md`

---

## Executive Summary

This plan defines the execution scaffold for verifying all T1-T10 structural/unit contracts and identifies the gap between the **local phase7 test suite** (structural/unit — PASS-eligible now for most tests) and the **requested runtime Discord/VPS end-to-end verification** (BLOCKED on multiple fronts).

**Key finding:** Local phase7 T1-T10 are deterministic unit/structural tests that can PASS on the local dev environment with zero runtime dependencies. However, the user-requested *runtime end-to-end verification* requiring Discord, Hermes Gateway, Postgres, Redis, and Prometheus is not achievable locally. Ten explicit blockers prevent full E2E verification.

---

## Task Dependency Graph

| Task | Depends On | Reason |
|------|------------|--------|
| T1 (Loop State Machine) | None | Pure structural — no runtime deps |
| T2 (Safety Gates) | None | Deterministic unit tests |
| T3 (Auth Enforcement) | None | Structural matrix check |
| T4 (Memory Pipeline) | None | Structural/models only, no DB |
| T5 (Surveillance Pipeline) | None | Deterministic unit tests |
| T6 (Persona FSM) | None | Deterministic unit tests |
| T7 (Distress Protocol) | None | Deterministic unit tests |
| T8 (Consent Revocation) | None | Deterministic unit tests |
| T9 (Budget Enforcement) | None | Mocked Redis, no live dep |
| T10 (Monitoring Health) | None | Local file existence checks |
| FIX-01 (Latency Benchmark) | None | New file creation only |
| FIX-02 (Forbidden-Pattern Scanner Tests) | None | New file creation only |
| FIX-03 (SOUL Body Text) | None | Doc edit — PersonaDoc §6.1/§3.6 |
| VPS-E2E (Discord/Hermes/DB) | T1-T10 + FIX-01 + FIX-02 + FIX-03 + SSHVPS | Requires VPS access, SSH creds, unmask ops |
| Auditor-Functional (T1-T5) | T1 through T5 processed | Review outputs after test run |
| Auditor-Technical (T6-T10) | T6 through T10 processed | Review outputs after test run |
| Auditor-Safety (AC-SAFE) | T2 + T6 + T7 + T8 processed | Safety boundary verification |

---

## Parallel Execution Graph

### Wave 1 (All Parallel — No Dependencies)
```
All T1-T10 verification commands can fire in parallel
All FIX-01/FIX-02/FIX-03 can fire in parallel with tests
All 3 auditor tasks can fire in parallel after respective tests complete
```

### Wave 2 (After Wave 1)
```
VERIFICATION-SUMMARY.md aggregation (depends on all T verification results)
VPS-E2E (separate execution context — requires SSH)
```

### Critical Path
```
T1-T10 parallel run (fastest path: ~30s total)
FIX-01, FIX-02, FIX-03 parallel (if fixes are applied)
No sequential dependencies between any T1-T10 tests
```

---

## Collision Scan

| File | Collision Risk | Owner |
|------|---------------|-------|
| `tests/phase7/test_T*.py` | Read-only for verification | Parent |
| `tests/safety/test_hard_stop_latency.py` | New file (FIX-01) — no collision | Single implementer |
| `tests/safety/test_forbidden_pattern_scanner.py` | New file (FIX-02) — no collision | Single implementer |
| `docs/00-core/06-Persona_Document_v3.0.md` | §6.1/§3.6 edit (FIX-03) | Single implementer |
| `docs/setup-evidence/phase5-verification/*.md` | New evidence files — parent only | Parent |
| Shared config/env files | No edits planned | N/A |

**No collision detected** — all verification evidence files are new, all fix targets are isolated.

---

## Rollback / No-Mutation Posture

| Operation | Mutation | Rollback |
|-----------|----------|----------|
| Run `pytest tests/phase7/test_T*.py -v` | None (read-only) | N/A |
| Create `test_hard_stop_latency.py` | New file | `git checkout -- tests/safety/test_hard_stop_latency.py` |
| Create `test_forbidden_pattern_scanner.py` | New file | `git checkout -- tests/safety/test_forbidden_pattern_scanner.py` |
| Edit `06-Persona_Document_v3.0.md` | Doc edit | `git checkout -- docs/00-core/06-Persona_Document_v3.0.md` |
| Create evidence files under `phase5-verification/` | New files | `git clean -fd docs/setup-evidence/phase5-verification/` |
| SSH to VPS for runtime verification | Remote inspection only | N/A |
| `systemctl unmask guinevere-discord.service` | Remote state change | `systemctl mask guinevere-discord.service` |

**Destructive operations explicitly NOT in scope:** No `rm -rf`, no force-push, no DROP TABLE, no Docker kill, no production service restart without explicit per-action approval from Faiz.

---

## Per-Test Scaffold (T1-T10)

### T1: E2E Loop — Loop State Machine

**Local Classification:** ✅ PASS-eligible now
**Runtime E2E Classification:** ❌ BLOCKED (B3 — Hermes Discord connectivity unconfirmed; B4 — systemd drain timeout mismatch; B5 — MCP misconfiguration)
**Expected Files:** `tests/phase7/test_T1_e2e_loop.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, `@ts-ignore`, `@ts-expect-error`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T1_e2e_loop.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T1-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL (exit code != 0)
- LSP diagnostics with new errors in `tests/phase7/test_T1_e2e_loop.py`
- Any forbidden pattern found

---

### T2: Safety Gates — HARD STOP + Yandere Integration

**Local Classification:** ✅ PASS-eligible now (unit level)
**Runtime E2E Classification:** ❌ BLOCKED — missing latency benchmark (FIX-01 required for AC-SAFE-001); missing forbidden-pattern scanner tests (FIX-02 required for F-01..F-15); no integrated Hermes pipeline to test end-to-end safety hook chain
**Expected Files:** `tests/phase7/test_T2_safety_gates.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`, `Any` (non-generic)
**Required Commands:**
```
pytest tests/phase7/test_T2_safety_gates.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T2-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- New LSP errors
- Forbidden patterns found

---

### T3: Auth Enforcement — MCP Auth Matrix

**Local Classification:** ✅ PASS-eligible now
**Expected Files:** `tests/phase7/test_T3_auth_enforcement.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T3_auth_enforcement.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T3-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- `verify_matrix_completeness()` returns False
- New LSP errors

---

### T4: Memory Pipeline — Structural Models

**Local Classification:** ✅ PASS-eligible now (structural/models only)
**Runtime E2E Classification:** ❌ BLOCKED — no live PostgreSQL; no VPS DB access for runtime recall verification; golden dataset has no test harness
**Expected Files:** `tests/phase7/test_T4_memory_pipeline.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T4_memory_pipeline.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T4-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- DNR model import errors
- EmbeddingConfig defaults mismatch
- New LSP errors

---

### T5: Surveillance Pipeline — Classification, Retention, Consent Gate

**Local Classification:** ✅ PASS-eligible now
**Expected Files:** `tests/phase7/test_T5_surveillance_pipeline.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T5_surveillance_pipeline.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T5-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- Classification import errors
- ConsentCheckResult struct errors
- New LSP errors

---

### T6: Persona FSM — Yandere FSM, Mood Engine, Drift

**Local Classification:** ✅ PASS-eligible now
**Expected Files:** `tests/phase7/test_T6_persona_fsm.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T6_persona_fsm.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T6-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- `PERMANENT_BASELINE` != Y4
- `ABSOLUTE_CEILING` != 5
- Y5_MAX escalation broken
- New LSP errors

---

### T7: Distress Protocol — Safe Mode, D0-D4

**Local Classification:** ✅ PASS-eligible now
**Expected Files:** `tests/phase7/test_T7_distress_protocol.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T7_distress_protocol.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T7-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- D1 incorrectly activates safe mode
- D3/D4 fails to activate safe mode
- New LSP errors

---

### T8: Consent Revocation — Consent Gate, HARD STOP→Revocation

**Local Classification:** ✅ PASS-eligible now
**Expected Files:** `tests/phase7/test_T8_consent_revocation.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T8_consent_revocation.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T8-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- HARD STOP does not set SAFE state
- Recovery works without explicit confirmation
- New LSP errors

---

### T9: Budget Enforcement — Mocked Redis

**Local Classification:** ✅ PASS-eligible now
**Expected Files:** `tests/phase7/test_T9_budget_enforcement.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T9_budget_enforcement.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T9-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- BudgetEnforcer fails to initialize with mocked Redis
- BudgetConfig defaults unreasonable
- New LSP errors

---

### T10: Monitoring Health — Config File Integrity

**Local Classification:** ✅ PASS-eligible now
**Expected Files:** `tests/phase7/test_T10_monitoring_health.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/phase7/test_T10_monitoring_health.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/T10-verification.md`
**Hard Rejection Criteria:**
- Any test FAIL
- `prometheus.yml` missing Hermes job
- Grafana dashboard invalid JSON
- Systemd template missing hardening directives
- New LSP errors

---

## Pre-Verification Fixes (REQUIRED for Runtime E2E)

### FIX-01: Create HARD STOP Latency Benchmark Test

**Severity:** BLOCKER (AC-SAFE-001 cannot be verified without this)
**Expected Files:** `tests/safety/test_hard_stop_latency.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`, mocked time (use `time.perf_counter_ns()`)
**Required Commands:**
```
pytest tests/safety/test_hard_stop_latency.py -v --tb=short --benchmark-min-rounds=100
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/FIX-01-verification.md`
**Hard Rejection Criteria:**
- Test file not created
- `p50 > 1ms` or `p99 > 5ms` or `max > 50ms` (or documented as KNOWN LIMITATION if local env introduces overhead)
- No 1000-iteration minimum

### FIX-02: Create Forbidden-Pattern Scanner Unit Tests

**Severity:** BLOCKER (F-01..F-15 + Y6 patterns have zero dedicated tests)
**Expected Files:** `tests/safety/test_forbidden_pattern_scanner.py`
**Forbidden Patterns:** `as any`, `# type: ignore`, bare `except`
**Required Commands:**
```
pytest tests/safety/test_forbidden_pattern_scanner.py -v --tb=short
```
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/FIX-02-verification.md`
**Hard Rejection Criteria:**
- Test file not created
- Fewer than 15 test cases (must cover all F-01..F-15 + Y6)
- Zero false-positive checks (benign text should pass)
- Imports fail

### FIX-03: Fix Stale SOUL Body Text (PersonaDoc §6.1 / §3.6)

**Severity:** MEDIUM — docs defect, not runtime. Does not block T1-T10 PASS but must be acknowledged.
**Expected Files:** `docs/00-core/06-Persona_Document_v3.0.md`
**Changes:**
- §6.1: Update body text from "Baseline Y1 / Maximum without trigger Y3" to match frontmatter v3.1 changelog (Y4 baseline, Y5 ceiling)
- §3.6: Remove "tidak melebihi Y3 tanpa trigger" language that contradicts Y4 baseline
**Evidence Requirements:** `docs/setup-evidence/phase5-verification/FIX-03-verification.md`
**Hard Rejection Criteria:**
- Stale Y1/Y3 language remains in §6.1
- Stale Y3 max-without-trigger language remains in §3.6
- Change not reflected in doc footer changelog

---

## Classification Status Summary

| Test | Local Unit | Runtime E2E | Blockers |
|------|-----------|-------------|----------|
| T1 | ✅ PASS-eligible | ❌ BLOCKED | B3 (Hermes Discord unconfirmed), B4 (systemd timeout mismatch), B5 (MCP misconfig) |
| T2 | ✅ PASS-eligible | ❌ BLOCKED | FIX-01 (no latency benchmark), FIX-02 (no scanner tests), no integrated Hermes pipeline |
| T3 | ✅ PASS-eligible | ✅ PASS-eligible | None (structural, no runtime dep) |
| T4 | ✅ PASS-eligible | ❌ BLOCKED | No live PostgreSQL, no VPS DB access, golden dataset untested |
| T5 | ✅ PASS-eligible | ❌ BLOCKED | No live Hermes/Discord pipeline for E2E |
| T6 | ✅ PASS-eligible | ✅ PASS-eligible | None (deterministic unit) |
| T7 | ✅ PASS-eligible | ✅ PASS-eligible | None (deterministic unit) |
| T8 | ✅ PASS-eligible | ✅ PASS-eligible | None (deterministic unit) |
| T9 | ✅ PASS-eligible | ❌ BLOCKED | Mocked Redis only — live Redis on VPS |
| T10 | ✅ PASS-eligible | ⚠️ CONDITIONAL | Prometheus/Grafana not running locally; tests verify file existence only |

**Key decision:** All T1-T10 can PASS locally at the structural/unit level. Runtime E2E verification (Discord message → Hermes processing → Postgres storage → Prometheus metrics) requires a separate VPS execution context with SSH access, unmask operations, and decrypted credentials.

---

## Required Output Evidence Paths

| Artifact | Path | Contents |
|----------|------|----------|
| T1 verification | `docs/setup-evidence/phase5-verification/T1-verification.md` | pytest output, LSP diag, verdict |
| T2 verification | `docs/setup-evidence/phase5-verification/T2-verification.md` | pytest output, LSP diag, verdict |
| T3 verification | `docs/setup-evidence/phase5-verification/T3-verification.md` | pytest output, LSP diag, verdict |
| T4 verification | `docs/setup-evidence/phase5-verification/T4-verification.md` | pytest output, LSP diag, verdict |
| T5 verification | `docs/setup-evidence/phase5-verification/T5-verification.md` | pytest output, LSP diag, verdict |
| T6 verification | `docs/setup-evidence/phase5-verification/T6-verification.md` | pytest output, LSP diag, verdict |
| T7 verification | `docs/setup-evidence/phase5-verification/T7-verification.md` | pytest output, LSP diag, verdict |
| T8 verification | `docs/setup-evidence/phase5-verification/T8-verification.md` | pytest output, LSP diag, verdict |
| T9 verification | `docs/setup-evidence/phase5-verification/T9-verification.md` | pytest output, LSP diag, verdict |
| T10 verification | `docs/setup-evidence/phase5-verification/T10-verification.md` | pytest output, LSP diag, verdict |
| FIX-01 verification | `docs/setup-evidence/phase5-verification/FIX-01-verification.md` | Latency benchmark results |
| FIX-02 verification | `docs/setup-evidence/phase5-verification/FIX-02-verification.md` | Scanner test results |
| FIX-03 verification | `docs/setup-evidence/phase5-verification/FIX-03-verification.md` | Diff evidence, stale text removal |
| Summary | `docs/setup-evidence/phase5-verification/VERIFICATION-SUMMARY.md` | Aggregated results, pass/fail, blockers |
| Auditor: Functional (T1-T5) | `docs/setup-evidence/phase5-verification/auditor-functional-T1-T5.md` | Functional correctness review |
| Auditor: Technical (T6-T10) | `docs/setup-evidence/phase5-verification/auditor-technical-T6-T10.md` | Technical depth review |
| Auditor: Safety (AC-SAFE) | `docs/setup-evidence/phase5-verification/auditor-safety-AC-SAFE.md` | Safety boundary compliance review |

---

## Auditor Matrix

| Auditor | Scope | Verdict Options | Pass Criteria |
|---------|-------|-----------------|---------------|
| **Functional (T1-T5)** | T1 structural transitions, T2 safety gate correctness, T3 auth matrix completeness, T4 model invariants, T5 pipeline structure | PASS / CONDITIONAL / FAIL | All T1-T5 unit tests PASS; no new LSP errors; forbidden patterns absent |
| **Technical (T6-T10)** | T6 Yandere FSM bounds, T7 distress protocol thresholds, T8 consent revocation invariants, T9 budget enforcement, T10 monitoring config integrity | PASS / CONDITIONAL / FAIL | All T6-T10 unit tests PASS; LSP clean; config files parseable |
| **Safety (AC-SAFE)** | T2 safety gates vs ADR-002/ADR-035/PersonaSafetyPolicy; T6 Y4/Y5/Y6 enforcement; T7 distress protocol; T8 consent revocation flow | PASS / NEEDS REVIEW / FAIL | Y6 prohibited; HARD STOP correct; safe mode blocks yandere/punishment; consent gates correct; SOUL/Policy mismatch documented |

**Auditor execution order:** All three can run in parallel after the respective verification files exist.

---

## Minimum Safe Execution Route

1. **Run T1-T10 locally** — pytest each file, capture stdout, verify exit code 0
2. **Run LSP diagnostics** on each test file — confirm no new errors
3. **Create FIX-01** (latency benchmark) — only if fix execution is approved
4. **Create FIX-02** (scanner tests) — only if fix execution is approved
5. **Apply FIX-03** (SOUL text) — only if fix execution is approved
6. **Write T1-T10 verification files** — capture evidence
7. **Spawn 3 parallel auditors** — functional, technical, safety
8. **Read auditor reports** — fix findings or accept false-positives
9. **Write VERIFICATION-SUMMARY.md** — aggregate all results
10. **NO auto-deploy, NO auto-unmask, NO destructive ops without explicit Faiz approval**

---

## Decision Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| D01 | T1-T10 run as parallel wave | No dependencies between any test; each tests independent code surface | 2026-06-07 |
| D02 | Local unit PASS ≠ runtime E2E PASS | Explicitly documented mismatch between structural phase7 tests and requested runtime E2E | 2026-06-07 |
| D03 | FIX-01/FIX-02/FIX-03 are pre-requisites for full E2E but NOT for local T1-T10 PASS | Missing latency benchmark and scanner tests do not affect current test files | 2026-06-07 |
| D04 | VPS runtime verification deferred | Requires SSH access, Tailscale, `GUINEVERE_DB_PASSWORD`, SOPS decryption — not available in local dev | 2026-06-07 |
| D05 | No secrets exposure in evidence files | All evidence paths contain only pass/fail verdicts, test output, and structural observations | 2026-06-07 |
| D06 | No Aizanta services touched | All verification scoped to Guinevere-only ports, files, and processes | 2026-06-07 |

---

## Commit Strategy

| Commit | Scope | Message |
|--------|-------|---------|
| 1 (if fixes applied) | FIX-01 + FIX-02 + FIX-03 | `phase5: add hard-stop latency benchmark, forbidden-pattern scanner tests, fix stale SOUL body text` |
| 2 | All verification + evidence files | `phase5: add T1-T10 verification evidence and auditor reports` |
| (No push unless Faiz says commit+push) | — | — |

---

## Success Criteria

1. All T1-T10 unit tests PASS (exit 0) with captured evidence
2. LSP diagnostics clean on all test files (no new errors)
3. All 3 auditor gates PASS
4. VERIFICATION-SUMMARY.md documents pass/fail per test, blockers for runtime E2E, and caveats
5. No secrets exposed, no destructive ops executed, no Aizanta services modified
6. Local-vs-VPS mismatch explicitly documented for Faiz review

---

## Caveats

1. **Local T1-T10 PASS does not equal runtime E2E verification.** The phase7 tests are structural/unit contracts. The requested Discord/VPS end-to-end verification requires a separate execution context with SSH+credentials.
2. **Missing latency benchmark** (`test_gate_01_hard_stop.py` from ADR-035) blocks AC-SAFE-001 verification. FIX-01 addresses this but the benchmark measures only `HardStopHandler.check()` time, not Hermes gateway dispatch time.
3. **Missing forbidden-pattern scanner tests** mean F-01..F-15 + Y6 output patterns have no dedicated test coverage. FIX-02 addresses this.
4. **SOUL body text mismatch** (PersonaDoc §6.1 Y1 vs runtime Y4) is a documentation defect only — runtime (`yandere_fsm.py`) is correct.
5. **Discord bot is masked.** The `guinevere-discord.service` cannot be tested without `systemctl unmask` on the VPS.
6. **Postgres, Redis, Hermes Gateway, Prometheus stack are VPS-only.** No local equivalents exist (no Docker, no WSL).
7. **guinevere-mcp service does not exist as HTTP endpoint.** Port 8090 has no runtime component.
8. **Golden recall dataset (110 queries)** exists but has no automated test runner — memory recall quality cannot be measured.
9. **No runtime Prometheus metrics for HARD STOP latency** (`guinevere_safety_hard_stop_latency_ms` histogram not created).

---

## Footer

- **Plan approved by:** (awaiting parent read)
- **Evidence root:** `docs/setup-evidence/phase5-verification/`
- **Research inputs:** `research-reports/phase5-verification/01-services-baseline.md`, `02-discord-status.md`, `03-memory-state.md`, `04-safety-gates.md`
- **Phase7 test sources:** `tests/phase7/test_T1_e2e_loop.py` through `test_T10_monitoring_health.py`
- **Decision authority:** AGENTS.md §1-§2, PersonaSafetyPolicy, ADR-Index
- **Next step:** Parent orchestrator reads this plan, confirms scaffold compliance, and begins Wave 1 execution or delegate to verifier sub-agent
