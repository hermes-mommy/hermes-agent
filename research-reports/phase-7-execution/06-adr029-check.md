# Phase 7 — ADR-029 Compliance & Safety-Critical Automation Gap Report

**Date:** 2026-06-06
**Scope:** ADR-029 (Self-Modification Automated Testing) binding requirements vs current state
**Gate Dependency:** ADR-029 compliance must be satisfied before ADR-035 (Hermes Migration) implementation
**Phase 7 Deliverable:** T1-T10 e2e suite, `.coveragerc` fail_under 80, `.guinevere/safety-critical-paths.yml`, `tests/safety/test_auto_rollback.py`, full coverage run PASS

---

## 1. ADR-029 Binding Requirements Summary

Derived from `adr/ADR-029-self-modification-automated-testing.md` (181 lines, CRITICAL risk level).

### R1: Automated Testing Gate
All Guinevere self-modification MUST pass automated testing before deployment to production. Test categories: unit tests, integration tests, safety boundary tests, and regression tests. The testing gate must not be bypassed by any autonomous process.

### R2: Automatic Rollback
- If any automated test fails after deployment, system performs automatic `git revert` to last known-good commit.
- Rollback must complete within **60 seconds** and restore full service operation.
- Rollback events are logged and alerted to Faiz via Discord (ADR-022) and audit trail.
- The `git revert` rollback mechanism must be tested regularly to ensure reliability.

### R3: Safety-Critical Change Classification
Changes touching these areas require explicit Faiz review before deployment regardless of test results:
- Persona behavior, tone, or mood model code
- Safety boundary enforcement or safe-word handling
- Surveillance data collection, retention, or processing
- Encryption, key management, or secrets handling
- Memory access control or privacy-related logic
- Autonomous loop phase transitions or governance rules

### R4: Safety-Critical Paths Config File
Safety-critical file paths **must be defined in a configuration file** (e.g., `.guinevere/safety-critical-paths.yml`) and treated as safety-critical themselves.

### R5: Routine Change Auto-Deployment
Changes not touching safety-critical areas may auto-deploy if:
- All unit tests pass
- All integration tests pass
- No regression in existing test coverage
- The change does not modify safety, persona, surveillance, or encryption files

### R6: Authority Hierarchy Enforcement
Authority hierarchy (safety > user > policy) enforced as hard constraint. No self-modification may weaken safety boundaries. Testing gate configuration and enforcement logic are themselves safety-critical and require Faiz review to modify.

### R7: Implementation Artifact Discipline
Any sub-agent research, implementation summary, audit, or verification for this ADR must be written to markdown evidence (file-based), not returned only inline.

---

## 2. Present Artifacts — What Exists

### 2.1 Test Infrastructure (Present)

| Artifact | Path | Status |
|----------|------|--------|
| ADR-029 document | `adr/ADR-029-self-modification-automated-testing.md` | EXISTS — Accepted, CRITICAL |
| Pytest collection | 3878 tests collected cleanly in 22.01s | EXISTS — no collection errors |
| pyproject.toml | `pyproject.toml` | EXISTS — has [tool.pytest.ini_options] with testpaths and pythonpath |
| Safety test suite | `tests/safety/` (8 .py files) | EXISTS — hard stop, distress, consent, yandere cap, punishment overflow |
| E2E test files | 6 dedicated E2E files across subsystems | EXISTS — hermes, surveillance, persona, memory, safety |
| Integration test | `tests/hermes/test_integration_e2e.py` (59 tests) | EXISTS — 6 categories |
| Hermes safety plugin tests | `tests/hermes/test_safety_plugin.py` (90 tests) | EXISTS — 9 gates |
| Smoke tests | `tests/smoke/` (3 test files) | EXISTS — requires live 9Router |
| Drift corrector rollback tests | `tests/persona/test_drift_corrector.py` (20+ rollback tests) | EXISTS — persona drift, not deployment rollback |
| Surveillance rollback test | `tests/surveillance/test_consumer.py` | EXISTS — single DB rollback test |
| conftest files | 3 directory-level conftests | EXISTS — smoke, surveillance, discord |

### 2.2 Deploy & Startup Infrastructure (Present)

| Artifact | Path | Status |
|----------|------|--------|
| Startup gate | `scripts/startup_gate.py` | EXISTS — validates auth_overlay and guinevere_safety plugins |
| Startup gate test | `scripts/startup_gate_test.py` | EXISTS |
| Backup script | `scripts/guinevere-backup.sh` | EXISTS — restic + SOPS + pg_dumpall |
| Backup systemd units | `systemd/guinevere-backup@.service`, `.timer` | EXISTS |
| Preflight check | `scripts/preflight-check.sh` | EXISTS |
| Health check P1 | `scripts/health-check-p1.sh` | EXISTS |
| Discord verify | `scripts/run-discord-verify.sh` | EXISTS |
| Ops manual with self-deploy | `docs/40-operations/45-InternalOpsManual_v1.0.md` | EXISTS — documents self-deploy pipeline |
| Incident response | `docs/40-operations/42-IncidentResponse_Postmortem_v1.0.md` | EXISTS — references rollback |
| Disaster recovery | `docs/40-operations/43-DisasterRecoveryPlan_v1.0.md` | EXISTS |

### 2.3 Existing Reports in Phase 7 Execution

| Report | Path | Content |
|--------|------|---------|
| Baseline | `research-reports/phase-7-execution/01-baseline.md` | Phase-wide baseline |
| Test coverage | `research-reports/phase-7-execution/02-test-coverage.md` | 3878 tests, T-suite naming gap, coverage config gap |
| Security audit | `research-reports/phase-7-execution/03-security-audit.md` | VPS ports, SSH, 155x except Exception |
| Monitoring gaps | `research-reports/phase-7-execution/04-monitoring-gaps.md` | Observability gaps |
| Deprecated files | `research-reports/phase-7-execution/05-deprecated-files.md` | Archive targets |

---

## 3. Gap Register — What Is Missing

### G1: `.coveragerc` — RED BLOCKER

| Field | Value |
|-------|-------|
| Requirement | ADR-029 R4, Phase 7 requires coverage PASS with fail_under 80 |
| Current state | **ABSENT** — no `.coveragerc` at project root |
| Impact | Cannot measure or enforce coverage thresholds. Phase 7 gate blocker. |
| Severity | RED BLOCKER |
| Dependencies | Must install pytest-cov or coverage in pyproject.toml dependencies |

### G2: `.guinevere/safety-critical-paths.yml` — RED BLOCKER

| Field | Value |
|-------|-------|
| Requirement | ADR-029 R4: safety-critical file paths defined in config file |
| Current state | **ABSENT** — no `.guinevere/` directory exists at project root |
| Impact | Cannot classify or gate safety-critical changes. Phase 7 gate blocker. |
| Severity | RED BLOCKER |
| Dependencies | Safety-critical surface inventory needed |

### G3: T1-T10 Named Test Suite — YELLOW HIGH

| Field | Value |
|-------|-------|
| Requirement | Phase 7 requires organized T-suite (T1-T10) for ADR-029 compliance verification |
| Current state | **ABSENT** — no test files or functions use T1/T2/...T10 naming convention |
| Impact | Cannot demonstrate traceable Phase 7 ADR-029 compliance. Tests exist but aren't organized. |
| Severity | YELLOW HIGH |
| Dependencies | G1 (coverage must work) |

### G4: `tests/safety/test_auto_rollback.py` — YELLOW HIGH

| Field | Value |
|-------|-------|
| Requirement | ADR-029 R2: rollback mechanism must be tested regularly, rollback <60s |
| Current state | **ABSENT** — no dedicated standalone rollback test file for deployment auto-rollback |
| Impact | Cannot assert rollback <60s or evidence preservation. Existing rollback tests cover persona drift only. |
| Severity | YELLOW HIGH |
| Dependencies | Requires rollback automation to exist (see G8) |

### G5: `[tool.coverage]` Section in `pyproject.toml` — RED BLOCKER

| Field | Value |
|-------|-------|
| Requirement | Coverage measurement and enforcement needed |
| Current state | **ABSENT** — no coverage-related sections in pyproject.toml |
| Impact | Without coverage section, `pytest --cov` runs without source/target config |
| Severity | RED BLOCKER |
| Dependencies | G1 must exist first |

### G6: `asyncio_default_fixture_loop_scope` — YELLOW MEDIUM

| Field | Value |
|-------|-------|
| Requirement | Future pytest-asyncio behavioral change will require this |
| Current state | **NOT SET** — `PytestDeprecationWarning` at collection time |
| Impact | May cause test failures in future pytest-asyncio versions |
| Severity | YELLOW MEDIUM |

### G7: Coverage Tool in Dependencies — RED BLOCKER

| Field | Value |
|-------|-------|
| Requirement | `pytest-cov` or `coverage` must be installable |
| Current state | **ABSENT** — not in `pyproject.toml` dependencies |
| Impact | `pytest --cov` would fail with ModuleNotFoundError |
| Severity | RED BLOCKER |

### G8: No Production `git revert` / Auto-Rollback Mechanism — YELLOW HIGH

| Field | Value |
|-------|-------|
| Requirement | ADR-029 R2: automatic `git revert` to last known-good commit |
| Current state | **ABSENT** — no Python production code (src/) performs `git revert` |
| Impact | Cannot satisfy R2 rollback requirement. Existing drift rollback is persona-level, not deployment-level. |
| Severity | YELLOW HIGH |

### G9: No Dedicated Deploy Rollback Script — YELLOW MEDIUM

| Field | Value |
|-------|-------|
| Requirement | ADR-029 R2: rollback within 60s |
| Current state | **ABSENT** — backup script exists but no deploy-rollback script |
| Impact | No automated recovery path from failed deployment |
| Severity | YELLOW MEDIUM |

### G10: 155 `except Exception:` in Production Code — ORANGE HIGH

| Field | Value |
|-------|-------|
| Requirement | ADR-029 R6: safety boundaries must not silently swallow errors |
| Current state | 155 blanket `except Exception:` across 72 files in `src/` |
| Impact | Safety-critical surfaces (consent gate, surveillance, safety plugin) may silently swallow errors |
| Severity | ORANGE HIGH — documented in security audit report |
| Mitigation | Per-instance audit; replace with specific exception types + structured logging |

---

## 4. Safety-Critical Surface Inventory

Per ADR-029 R3, these areas require explicit Faiz review. Must be defined in `.guinevere/safety-critical-paths.yml` (G2).

### 4.1 Persona Behavior, Tone, Mood Model

| Path | Description |
|------|-------------|
| `src/persona/` | Full persona subsystem: mood engine, yandere FSM, drift detection/correction, safe mode, rituals, punishment, rewards |
| `src/hermes/safety_plugin.py` | GuinevereSafetyPlugin — gates G01-G09 |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Persona safety policy |
| `docs/60-persona/61-SystemPromptMaster_v1.1.md` | System prompt master |
| `hermes-config/plugins/guinevere_safety/` | Hermes safety plugin |

### 4.2 Safety Boundary / Safe-Word Handling

| Path | Description |
|------|-------------|
| `src/core/services/hard_stop_handler.py` | HARD STOP protocol handler |
| `src/persona/safe_mode.py` | Safe mode controller |
| `src/persona/yandere_fsm.py` | Yandere FSM state machine (Y4 baseline, Y5 ceiling, Y6 prohibition) |
| `hermes-config/hooks/hard_stop.py` | Hermes hook-level hard stop |
| `tests/safety/` | All safety tests (hard stop, distress, consent, yandere cap) |

### 4.3 Surveillance Data

| Path | Description |
|------|-------------|
| `src/surveillance/` | Full surveillance subsystem: consumer, classification, router, consent gate, secret scanner |
| `src/discord/` | Discord bot (imported by surveillance tests) |

### 4.4 Encryption, Key Management, Secrets

| Path | Description |
|------|-------------|
| `src/mcp/auth.py` | Auth level definitions |
| `src/mcp/auth_matrix.py` | Tool-level auth matrix |
| `src/surveillance/secret_scanner.py` | Secret scanning/redaction |
| `src/surveillance/secrets.py` | Secrets handling |
| `hermes-config/plugins/auth_overlay/` | Auth overlay plugin |

### 4.5 Memory Access Control / Privacy

| Path | Description |
|------|-------------|
| `src/memory/` | Full memory subsystem |
| `src/hermes/memory_bridge.py` | Deprecated memory bridge |
| `hermes-config/hooks/dnr_filter.py` | Do-Not-Record filter |
| `hermes-config/plugins/memory/guinevere_memory/` | Hermes memory plugin |

### 4.6 Autonomous Loop / Governance

| Path | Description |
|------|-------------|
| `src/loops/` | Full agent loop implementation: manager, artifacts, evidence, scheduler |
| `src/hermes/` | Hermes integration layer |
| `AGENTS.md` | Agent operating contract |
| `scripts/startup_gate.py` | Startup gate — validates critical plugins before Hermes starts |
| `hermes-config/config.yaml` | Hermes configuration |
| `systemd/` | Systemd service units |
| `tests/hermes/` | Hermes integration tests |

### 4.7 Testing Infrastructure (Safety-Critical per ADR-029 R6)

| Path | Description |
|------|-------------|
| `tests/` | Full test suite (3878 tests) |
| `pyproject.toml` | [tool.pytest.ini_options] section |
| `.coveragerc` | **MISSING** — must be created |
| `.guinevere/safety-critical-paths.yml` | **MISSING** — must be created |

---

## 5. Coverage Configuration State

| Item | Current | Required | Gap |
|------|---------|----------|-----|
| `.coveragerc` file | **ABSENT** | Must exist with `fail_under = 80` | RED BLOCKER |
| `[tool.coverage]` in pyproject.toml | **ABSENT** | Alternative to .coveragerc | RED BLOCKER |
| pytest-cov dependency | **ABSENT** in dependencies | Must be added to pyproject.toml `[project.optional-dependencies]` | RED BLOCKER |
| fail_under threshold | **Not set** | 80% minimum | RED BLOCKER |
| Source paths | **Not set** | `source = ["src"]` | RED BLOCKER |
| Omit patterns | **Not set** | `omit = ["tests/*", "scripts/*", "**/__pycache__/*"]` | MEDIUM |

---

## 6. Rollback Automation State

### 6.1 Existing Rollback Coverage

| Area | File | Tests | Type |
|------|------|-------|------|
| Persona drift rollback | `tests/persona/test_drift_corrector.py` | 20+ | Auto-rollback on drift threshold exceed |
| Persona drift rollback (severe) | `tests/persona/test_drift_detector.py` | 1 | test_rollback_for_severe_drift |
| Persona E2E rollback | `tests/persona/test_persona_e2e.py` | 2 | Corrector triggers/defers rollback |
| Surveillance DB rollback | `tests/surveillance/test_consumer.py` | 1 | test_store_rollback_on_failure |
| Surveillance timescale rollback | `tests/surveillance/test_timescale.py` | 1+ | session.rollback.called assertion |

### 6.2 Missing Rollback Infrastructure

| Requirement | Current State | Gap |
|-------------|---------------|-----|
| `git revert` automation | **ABSENT** in src/ | No production code performs `git revert` |
| Rollback <60s assertion | **ABSENT** | No test asserts deployment rollback time |
| Evidence preservation on rollback | **ABSENT** | No test asserts evidence files survive rollback |
| Dedicated auto-rollback test file | **ABSENT** | `tests/safety/test_auto_rollback.py` does not exist |
| Rollback alert/notification | **ABSENT** | No test asserts Discord notification on rollback |
| Last-known-good commit tracking | **ABSENT** | No mechanism stores/retrieves last-good commit |

---

## 7. Deploy & Self-Deploy Infrastructure

### 7.1 Documented Self-Deploy Pipeline

The Internal Ops Manual (`docs/40-operations/45-InternalOpsManual_v1.0.md`) documents a self-deploy pipeline:

- Nightly at 03:00 Asia/Jakarta via `guinevere-selfdeploy.timer`
- Pre-deploy checks: deploy lock, active SEV status, error budget, backup, git clean working tree
- Post-deploy failure → skip deploy or manual rollback
- Git tag pattern: `deploy-YYYYMMDD-HHMMSS`

**However:** The `guinevere-selfdeploy.timer` and `self-deploy.sh` files are only documented in ops manual — not present in the repo scripts/ directory. No rollback scripts exist.

### 7.2 Deploy-Related Scripts Present vs Missing

| Script | Present in Repo | Notes |
|--------|----------------|-------|
| `scripts/guinevere-backup.sh` | YES | restic backup, not deploy |
| `scripts/preflight-check.sh` | YES | Pre-flight checks |
| `scripts/health-check-p1.sh` | YES | Health check |
| `scripts/startup_gate.py` | YES | Plugin validation gate |
| `scripts/run-discord-verify.sh` | YES | Discord verification |
| `scripts/guinevere-selfdeploy.sh` | **NO** | Documented in ops manual only |
| `scripts/guinevere-rollback.sh` | **NO** | Not documented or created |

---

## 8. Gap-to-Implementation Mapping

| Gap ID | Phase 7 Requirement | Implementation Action | Priority |
|--------|---------------------|----------------------|----------|
| G1 | `.coveragerc` | Create `.coveragerc` with `fail_under = 80`, `source = src`, omit patterns | **P0** |
| G7 | pytest-cov dependency | Add `pytest-cov` to `pyproject.toml [project.optional-dependencies] test` | **P0** |
| G5 | `[tool.coverage]` in pyproject.toml | Add coverage section with `fail_under = 80` | **P0** |
| G2 | `.guinevere/safety-critical-paths.yml` | Create `.guinevere/` dir and `safety-critical-paths.yml` with paths from §4 | **P0** |
| G6 | asyncio loop scope | Add `asyncio_default_fixture_loop_scope = "function"` to pytest ini_options | **P1** |
| G3 | T1-T10 named tests | Create T-suite test files or add T1-T10 markers to existing tests | **P1** |
| G4 | `tests/safety/test_auto_rollback.py` | Create standalone auto-rollback test with <60s + evidence preservation | **P1** |
| G8 | Rollback automation | Implement or stub git revert mechanism in src/ or scripts/ | **P2** |
| G9 | Rollback script | Create `scripts/guinevere-rollback.sh` | **P2** |
| G10 | except Exception audit | Per-instance audit of 155 except Exception: in safety-critical surfaces | **P3** |

---

## 9. Scaffold Requirements Per Gap

### Scaffold G1+G5+G7: Coverage Configuration

```
Expected files:
  - .coveragerc (fail_under = 80, source = ["src"], omit = ["tests/*", "scripts/*", "**/__pycache__/*"])
  - pyproject.toml modification: add [tool.coverage.run] and [tool.coverage.report] sections
  - pyproject.toml modification: add pytest-cov to optional-dependencies test

Required commands:
  - python -m pytest --cov=src --cov-report=term-missing tests/ -q --tb=short
    Expected: exit 0, coverage >= 80%

Forbidden patterns in .coveragerc:
  - "fail_under" with value < 80
  - Missing "source" directive

Evidence:
  - evidence/phase-7/coverage-config/verification.md
  - evidence/phase-7/coverage-config/auditor-gate.md
```

### Scaffold G2: Safety-Critical Paths Config

```
Expected files:
  - .guinevere/safety-critical-paths.yml
    Must include ALL paths from §4 of this report

Required commands:
  - python -c "import yaml; yaml.safe_load(open('.guinevere/safety-critical-paths.yml'))"
    Expected: exit 0 (valid YAML)
  - grep -c "src/persona" .guinevere/safety-critical-paths.yml  Expected: >= 1
  - grep -c "src/surveillance" .guinevere/safety-critical-paths.yml  Expected: >= 1
  - grep -c "tests/" .guinevere/safety-critical-paths.yml  Expected: >= 1

Forbidden patterns: empty file, missing persona/surveillance/safety sections

Evidence:
  - evidence/phase-7/safety-critical-paths/verification.md
  - evidence/phase-7/safety-critical-paths/auditor-gate.md
```

### Scaffold G3: T-Suite Naming

```
Expected files:
  - tests/phase7/__init__.py
  - tests/phase7/test_T1_e2e_loop.py (or marker-based approach)
  - tests/phase7/test_T2_safety_gates.py through T10

Required commands:
  - python -m pytest tests/phase7/ --collect-only -q
    Expected: exit 0, 10+ tests collected
  - python -m pytest tests/phase7/ -q --tb=short
    Expected: exit 0

Forbidden patterns:
  - Any test function without T+number prefix
  - pytest.mark.skip on any T-suite test
```

### Scaffold G4+G8: Auto-Rollback Test

```
Expected files:
  - tests/safety/test_auto_rollback.py

Required tests in file:
  - test_rollback_completes_under_60_seconds
  - test_rollback_evidence_preserved
  - test_rollback_creates_audit_log
  - test_rollback_notifies_discord
  - test_no_rollback_when_tests_pass

Required commands:
  - python -m pytest tests/safety/test_auto_rollback.py -q --tb=short
    Expected: exit 0

Forbidden patterns:
  - pytest.mark.skip
  - time.sleep with value > 5
  - # type: ignore
```

---

## 10. Dependency Map & Execution Order

```
Phase 1 (P0 — Must create before anything else)
├── G7: pytest-cov in pyproject.toml [no dependencies]
├── G5: coverage section in pyproject.toml [depends on G7]
├── G1: .coveragerc [depends on G5]
└── G2: .guinevere/safety-critical-paths.yml [no dependencies]

Phase 2 (P1 — Can parallel with Phase 1)
├── G6: asyncio loop scope in pyproject.toml [no dependencies]
├── G3: T-suite named tests [depends on G1+G5+G7 for coverage gate test]
└── G4: auto-rollback test file [depends on G8]

Phase 3 (P2 — Requires design)
├── G8: git revert automation [no dependencies]
└── G9: rollback script [depends on G8]

Phase 4 (P3 — Cleanup, can parallel)
└── G10: except Exception audit [no dependencies]

Verification Gate:
  - python -m pytest --cov=src --cov-report=term-missing tests/ -q --tb=short
    Expected: exit 0, coverage >= 80%
  - python -m pytest tests/safety/test_auto_rollback.py tests/phase7/ -q --tb=short
    Expected: exit 0
```

---

## 11. Blockers and Risks

### Blockers (Must Resolve Before ADR-035)

| Blocker | Detail | Mitigation |
|---------|--------|------------|
| G1+G5+G7: No coverage config | Without `.coveragerc` or `[tool.coverage]` + pytest-cov, coverage cannot be measured or enforced | Create all 3 artifacts |
| G2: No safety-critical paths | Without `.guinevere/safety-critical-paths.yml`, ADR-029 R4 is violated | Create `.guinevere/` directory + use §4 inventory |

### Risks

| Risk | Severity | Detail |
|------|----------|--------|
| T1-T10 naming vs marker approach | YELLOW | Organization structure decision: test file naming vs pytest markers. Either works but must be decided before implementation. |
| Rollback mechanism design choice | YELLOW | Whether rollback lives in `src/` (production code) or `scripts/` (shell script). ADR-029 mentions `git revert` but doesn't specify implementation layer. |
| 155 `except Exception:` systemic | ORANGE | High volume (72 files) makes audit expensive. Safety-critical surfaces (consent_gate, safety_plugin, surveillance/consumer) should be prioritized. |
| 189 tests depend on `src/discord.*` | YELLOW | If `src/discord/` is archived in Phase 7, 8 test files (152 tests) + 1 surveillance test file (37 tests) will break. Must be migrated before archiving. |
| Smoke tests require live 9Router | GREEN | `tests/smoke/conftest.py` needs `http://localhost:20128` — cannot run offline. Acceptable as live-only tests. |

### ADR-035 Dependency Confirmation

ADR-035 (`adr/ADR-035-hermes-migration.md`) explicitly references ADR-029 and states:

> **ADR-029 Post-Migration Compliance**: ADR-029 requires automatic testing gates and 60-second rollback for self-modifications. After the Hermes migration is complete, the new Hermes-based system must still satisfy ADR-029's automated testing requirements... Phase 7 (Hardening) includes configuring Hermes hooks and plugins to pass ADR-029's automated test suites before production cutover.

This confirms Phase 7 ADR-029 compliance is a **prerequisite** for ADR-035 production cutover.

---

## Appendix A: Key File Paths Referenced

| Path | Role |
|------|------|
| `adr/ADR-029-self-modification-automated-testing.md` | Source ADR |
| `adr/ADR-035-hermes-migration.md` | Dependent ADR |
| `pyproject.toml` | Coverage config target |
| `.coveragerc` | **MISSING** — must create |
| `.guinevere/safety-critical-paths.yml` | **MISSING** — must create |
| `tests/safety/test_auto_rollback.py` | **MISSING** — must create |
| `tests/phase7/` | **MISSING** — T-suite directory |
| `scripts/startup_gate.py` | Existing plugin validation gate |
| `scripts/guinevere-backup.sh` | Existing backup (not rollback) |
| `systemd/` | Existing systemd service templates (9 units) |
| `docs/40-operations/45-InternalOpsManual_v1.0.md` | Self-deploy pipeline documentation |

## Appendix B: Current Coverage Metrics Snapshot

> Coverage metrics cannot be collected until G1+G5+G7 are implemented. Baseline of 0% with 3878 tests indicates zero measurement infrastructure.

| Metric | Current | Target |
|--------|---------|--------|
| Coverage measurement | NOT AVAILABLE | >= 80% |
| fail_under threshold | NOT SET | 80 |
| Source path configured | NO | src/ |
| Omit patterns configured | NO | tests/*, scripts/* |
| pytest-cov installed | NO | YES |

## Appendix C: Existing Rollback Test Inventory (22 Tests)

| Test | File | Line | Type |
|------|------|------|------|
| test_rollback_error_is_drift_correction_error | tests/persona/test_drift_corrector.py | 293 | Unit — persona drift |
| test_alert_range_triggers_auto_rollback | tests/persona/test_drift_corrector.py | 370 | Unit — persona drift |
| test_severe_drift_triggers_auto_rollback | tests/persona/test_drift_corrector.py | 382 | Unit — persona drift |
| test_length_mismatch_triggers_auto_rollback | tests/persona/test_drift_corrector.py | 393 | Unit — persona drift |
| test_drift_creates_rollback_and_evaluation_logs | tests/persona/test_drift_corrector.py | 415 | Unit — persona drift |
| test_safe_mode_active_defers_rollback | tests/persona/test_drift_corrector.py | 435 | Unit — persona drift |
| test_safe_mode_inactive_allows_rollback | tests/persona/test_drift_corrector.py | 467 | Unit — persona drift |
| test_rollback_success | tests/persona/test_drift_corrector.py | 514 | Unit — persona drift |
| test_rollback_restored_hash_is_baseline | tests/persona/test_drift_corrector.py | 527 | Unit — persona drift |
| test_rollback_previous_hash_from_last_result | tests/persona/test_drift_corrector.py | 537 | Unit — persona drift |
| test_rollback_no_previous_detection | tests/persona/test_drift_corrector.py | 547 | Unit — persona drift |
| test_rollback_creates_drift_log | tests/persona/test_drift_corrector.py | 557 | Unit — persona drift |
| test_rollback_with_safe_mode_defers | tests/persona/test_drift_corrector.py | 568 | Unit — persona drift |
| test_rollback_commit_failure_raises_rollback_error | tests/persona/test_drift_corrector.py | 585 | Unit — persona drift |
| test_rollback_timestamp_is_utc | tests/persona/test_drift_corrector.py | 607 | Unit — persona drift |
| test_rollback_double_failure_raises | tests/persona/test_drift_corrector.py | 615 | Unit — persona drift |
| test_drift_log_rollback_available_false_for_none | tests/persona/test_drift_corrector.py | 676 | Unit — persona drift |
| test_rollback_for_severe_drift | tests/persona/test_drift_detector.py | 173 | Unit — persona drift |
| test_corrector_triggers_rollback | tests/persona/test_persona_e2e.py | 763 | E2E — persona drift |
| test_corrector_defers_rollback_in_safe_mode | tests/persona/test_persona_e2e.py | 777 | E2E — persona drift |
| test_store_rollback_on_failure | tests/surveillance/test_consumer.py | 602 | Unit — DB rollback |

**Total: 22 rollback-related tests, all persona-drift or DB-rollback focused. Zero deployment `git revert` rollback tests.**

---

*Report generated by Guinevere sub-agent. All data collected read-only. No state altered.*
