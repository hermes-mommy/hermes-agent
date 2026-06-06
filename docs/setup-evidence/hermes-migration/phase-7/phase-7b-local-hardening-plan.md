# Phase 7b Local Hardening Plan — ADR-035 Hermes Migration

## 1. Scope and Authority

This planner file is the file-based planner gate for ADR-035 Hermes Migration Phase 7 after the Phase 7 research wave and Oracle consultation.

Oracle verdict: final Phase 7 completion is blocked. Phase 7b may proceed only as local, non-destructive hardening. Do not claim Phase 7 complete, do not flip ADR-035 to IMPLEMENTED, do not tag or push the final migration tag, do not archive deprecated files, and do not execute VPS SSH/firewall/port changes until the deferred Phase 7c gates are cleared.

Phase 7b allowed scope:

- Add local ADR-029 coverage and safety-critical path configuration.
- Add a named T1-T10 Phase 7 test suite and non-destructive auto-rollback tests.
- Add local Hermes monitoring configuration files: Prometheus job, alert rules, dashboard, Alertmanager routing, Promtail service matching.
- Add a repository template for `systemd/hermes-gateway.service`.
- Add secrets rotation schedule evidence without secret values.
- Add blocker register, runbooks, and Phase 7b evidence docs.

Phase 7b explicitly excludes:

- ADR-035 status change to IMPLEMENTED.
- Final deployment, final tag, or push.
- Deprecated archive/move/delete work.
- VPS firewall, SSH, port binding, Docker restart, or restic credential work.
- Aizanta changes.
- Secret creation, secret disclosure, or fake backup proof.

## 2. Research Inputs

The planner used these file-based inputs:

- `docs/setup-evidence/hermes-migration/batch-plan-phase-7.md`
- `adr/ADR-035-hermes-migration.md`
- `research-reports/phase-6-7-planning/05-monitoring-gaps.md`
- `research-reports/phase-6-7-planning/06-deprecated-files.md`
- `research-reports/phase-6-7-planning/07-adr029-tests.md`
- `research-reports/phase-6-7-planning/10-security-hardening.md`
- `research-reports/phase-6-7-planning/11-disaster-recovery.md`
- `research-reports/phase-7-execution/01-baseline.md`
- `research-reports/phase-7-execution/02-test-coverage.md`
- `research-reports/phase-7-execution/03-security-audit.md`
- `research-reports/phase-7-execution/04-monitoring-gaps.md`
- `research-reports/phase-7-execution/05-deprecated-files.md`
- `research-reports/phase-7-execution/06-adr029-check.md`
- `research-reports/phase-7-execution/07-dr-readiness.md`
- `research-reports/phase-7-execution/08-external-hardening-patterns.md`
- Oracle consultation `bg_d331246a`
- Current local files: `pyproject.toml`, `src/core/services/llm_metrics.py`, `src/core/main.py`, `src/hermes/__init__.py`, `src/hermes_plugins/commands_high/help.py`, monitoring configs, systemd templates.

## 3. Known State and Blocking Decisions

### 3.1 Current Gate Status

| Gate | Status | Phase 7b Handling |
| --- | --- | --- |
| 24h stable operation | FAIL | Deferred to Phase 7c; do not archive deprecated files. |
| `guinevere-mcp` service | FAIL | Deferred to Phase 7c VPS remediation. |
| Hermes config YAML warning | WARNING | Deferred to Phase 7c VPS remediation. |
| Monitoring exporters | FAIL | Local config improvements only; deployment remains blocked. |
| Public SSH / no firewall / public 20128 / public 9191 | FAIL | Document runbook/blocker only; no remote mutation in 7b. |
| `hermes security` HIGH/CRITICAL | PASS | Keep documented; remaining port/firewall posture blocks final. |
| `.coveragerc` | FAIL | Fix in 7b.1. |
| `.guinevere/safety-critical-paths.yml` | FAIL | Fix in 7b.2. |
| T1-T10 named suite | FAIL | Fix in 7b.3. |
| Auto rollback test | FAIL | Fix in 7b.4. |
| Hermes metrics/dashboard/alerts | FAIL | Local config fixes in 7b.5; instrumentation may remain blocker. |
| Deprecated archive | BLOCKED | Deferred to 7c; create blocker register only. |
| DR final backup | BLOCKED | Deferred to 7c; document Hermes CLI/restic/sentinel gaps. |
| ADR-035 IMPLEMENTED | BLOCKED | No status flip in 7b. |

### 3.2 Binding Decisions

1. Phase 7b is a local hardening batch, not final migration completion.
2. `src/core/services/llm_router.py` remains active and must not be archived.
3. Deprecated files are not moved in Phase 7b because 24h stability and import/test migration are not complete.
4. Monitoring edits are local repository configuration only. They do not prove live Prometheus/Grafana behavior until deployed and reloaded in Phase 7c.
5. Secrets rotation schedule must use the exact user-required evidence path: `docs/setup-evidence/phase-7/STEP-7.5/secrets-rotation-schedule.txt`.
6. All evidence must honestly record blocked gates. No completion claims are permitted.
7. No implementation sub-agent may touch more than one implementation step.

## 4. Master Todo and Dependency Map

| Step | Task | Parallel Marker | Dependencies |
| --- | --- | --- | --- |
| 7b.1 | Coverage config and pytest-cov dependency | parallel | None |
| 7b.2 | Safety-critical paths config | parallel | None |
| 7b.4 | Auto rollback test scaffold | parallel | None |
| 7b.5 | Hermes monitoring config files | parallel | None |
| 7b.6 | `systemd/hermes-gateway.service` template | parallel | None |
| 7b.7 | Secrets rotation schedule evidence | parallel | None |
| 7b.8 | Blocker register, runbooks, completion evidence | parallel | None |
| 7b.3 | T1-T10 named test suite | sequential | 7b.1 |
| A1 | Test completeness auditor | audit-batch | 7b.1, 7b.3, 7b.4 parent verification |
| A2 | Security and blocker honesty auditor | audit-batch | 7b.2, 7b.5, 7b.7, 7b.8 parent verification |
| A3 | Docs and evidence completeness auditor | audit-batch | 7b.6, 7b.7, 7b.8 parent verification |

Wave 1 implementation may run steps 7b.1, 7b.2, 7b.4, 7b.5, 7b.6, 7b.7, and 7b.8 in parallel because they write disjoint source/config/doc surfaces except evidence directories. Parent must create or verify evidence directories and avoid conflicting doc writes.

Wave 2 runs 7b.3 after 7b.1 completes because T1-T10 verification depends on working coverage configuration.

## 5. Collision Scan

| Shared Resource | Potential Collision | Mitigation |
| --- | --- | --- |
| `pyproject.toml` | 7b.1 only | 7b.1 is sole owner. |
| `.coveragerc` | 7b.1 only | 7b.1 is sole owner. |
| `.guinevere/safety-critical-paths.yml` | 7b.2 only | 7b.2 is sole owner. |
| `tests/phase7/` | 7b.3 only | 7b.3 is sole owner. |
| `tests/safety/test_auto_rollback.py` | 7b.4 only | 7b.4 is sole owner. |
| `monitoring/` configs | 7b.5 only | 7b.5 is sole owner. |
| `systemd/hermes-gateway.service` | 7b.6 only | 7b.6 is sole owner. |
| `docs/setup-evidence/phase-7/STEP-7.5/` | 7b.7 only | 7b.7 is sole owner. |
| `docs/20-security/hermes-phase-7-blocker-register.md` | 7b.8 only | 7b.8 is sole owner. |
| `docs/40-operations/runbooks/hermes-*.md` | 7b.8 only | 7b.8 is sole owner. |
| `docs/setup-evidence/hermes-migration/phase-7/phase-7b-completion-report.md` | 7b.8 only | 7b.8 is sole owner. |
| `src/` deprecated files | Not in 7b | Forbidden to move/archive/delete in 7b. |
| Aizanta files/containers | Not in 7b | Forbidden to touch. |
| Git commits/tags/push | Not in 7b | Forbidden unless user separately approves partial 7b commit. |

## 6. Implementation Design and Verification Scaffolds

### 6.1 Step 7b.1 — Coverage Configuration

Task: create `.coveragerc`, add coverage configuration to `pyproject.toml`, and add `pytest-cov>=7` under a test optional dependency.

Expected files:

- `.coveragerc`
- `pyproject.toml`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-1/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-1/auditor-gate.md`

Forbidden patterns:

- `.coveragerc` with `fail_under` below 80.
- Missing `source = src` or equivalent source setting.
- `# type: ignore`, `as any`, `@ts-ignore`, `@ts-expect-error`.
- Removing existing dependencies or pytest settings.

Required commands:

- `python -m pytest --cov=src --cov-report=term-missing tests/ -q --tb=short` must exit 0 and report coverage at least 80%.
- `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` must exit 0.
- `python -c "import configparser; c=configparser.ConfigParser(); c.read('.coveragerc'); assert c.has_section('run'); assert c.has_section('report')"` must exit 0.

Evidence requirements:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-1/verification.md` with the 12 evidence sections.
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-1/auditor-gate.md` placeholder or auditor output after verification.

Hard rejection criteria:

- Coverage command exits non-zero due to changes from this step.
- Coverage threshold missing or below 80.
- `pyproject.toml` parse fails.
- Existing pytest settings are removed.

### 6.2 Step 7b.2 — Safety-Critical Paths

Task: create `.guinevere/safety-critical-paths.yml` for ADR-029 safety-critical change detection.

Expected files:

- `.guinevere/safety-critical-paths.yml`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-2/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-2/auditor-gate.md`

Required safety surfaces:

- Persona and yandere boundaries: `src/persona/`, `docs/60-persona/`.
- HARD STOP and safe mode: `src/hermes/safety_plugin.py`, `src/core/services/hard_stop_handler.py`, `src/persona/safe_mode.py`, `src/persona/yandere_fsm.py`, `hermes-config/hooks/hard_stop.py`, `tests/safety/`.
- Surveillance and consent: `src/surveillance/`, `docs/30-data/`, `tests/surveillance/`.
- Auth and secrets: `src/mcp/auth.py`, `src/mcp/auth_matrix.py`, `src/surveillance/secret_scanner.py`, `src/surveillance/secrets.py`, `hermes-config/plugins/auth_overlay/`.
- Memory and privacy: `src/memory/`, `src/hermes/memory_bridge.py`, `hermes-config/hooks/dnr_filter.py`, `hermes-config/plugins/memory/guinevere_memory/`.
- Autonomous loops and Hermes runtime: `src/loops/`, `src/hermes/`, `hermes-config/config.yaml`, `systemd/`.
- Governance and testing infrastructure: `AGENTS.md`, `scripts/startup_gate.py`, `tests/`, `pyproject.toml`, `.coveragerc`, `.guinevere/safety-critical-paths.yml`.

Forbidden patterns:

- Empty YAML file.
- Missing persona, surveillance, safety, auth, memory, loops, Hermes, or testing categories.
- Secret values.

Required commands:

- `python -c "import yaml; data=yaml.safe_load(open('.guinevere/safety-critical-paths.yml', encoding='utf-8')); assert data"` must exit 0.
- `grep "src/persona" .guinevere/safety-critical-paths.yml` must exit 0.
- `grep "src/surveillance" .guinevere/safety-critical-paths.yml` must exit 0.
- `grep "src/hermes/safety_plugin" .guinevere/safety-critical-paths.yml` must exit 0.

Evidence requirements:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-2/verification.md`.
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-2/auditor-gate.md`.

Hard rejection criteria:

- YAML parse fails.
- Any required safety-critical domain is omitted.
- Secret values appear.

### 6.3 Step 7b.3 — T1-T10 Named Test Suite

Task: create a Phase 7 named T1-T10 suite under `tests/phase7/` with deterministic tests or wrappers for the required migration acceptance surfaces.

Expected files:

- `tests/phase7/__init__.py`
- `tests/phase7/test_T1_basic_conversation_y4.py`
- `tests/phase7/test_T2_multi_turn_memory_cross_session.py`
- `tests/phase7/test_T3_mcp_tools_from_chat.py`
- `tests/phase7/test_T4_hard_stop_latency.py`
- `tests/phase7/test_T5_safe_mode.py`
- `tests/phase7/test_T6_memory_recall_no_hallucination.py`
- `tests/phase7/test_T7_slash_commands_catalog.py`
- `tests/phase7/test_T8_rituals_wib.py`
- `tests/phase7/test_T9_cost_tracking.py`
- `tests/phase7/test_T10_surveillance_pipeline.py`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-3/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-3/auditor-gate.md`

Forbidden patterns:

- `pytest.mark.skip` or unconditional skip.
- Tests that only assert `True` without checking a real contract.
- `# type: ignore`, `as any`, `@ts-ignore`, `@ts-expect-error`.
- Destructive operations or network calls that require live secrets.

Required commands:

- `python -m pytest tests/phase7/ --collect-only -q` must exit 0 and collect at least 10 tests.
- `python -m pytest tests/phase7/ -q --tb=short` must exit 0.
- `python -m pytest --cov=src --cov-report=term-missing tests/phase7/ -q --tb=short` must exit 0.

Evidence requirements:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-3/verification.md`.
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-3/auditor-gate.md`.

Hard rejection criteria:

- Collection errors.
- Any T-suite test fails due to introduced code.
- Any T-suite test is skipped.
- Test suite relies on real Discord tokens, API keys, DB credentials, or surveillance secrets.

### 6.4 Step 7b.4 — Auto Rollback Test Scaffold

Task: create `tests/safety/test_auto_rollback.py` with non-destructive ADR-029 rollback behavior tests using sandbox state.

Expected files:

- `tests/safety/test_auto_rollback.py`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-4/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-4/auditor-gate.md`

Required test contracts:

- Rollback completes under 60 seconds in sandbox.
- Evidence files are preserved.
- Audit log records rollback reason, failing command, changed files, and restored commit/sentinel.
- No rollback occurs when tests pass.
- Rollback result can be verified by sentinel state.

Forbidden patterns:

- Destructive git operations against the real repository.
- `pytest.mark.skip`.
- `time.sleep` above 5 seconds.
- `# type: ignore`, `as any`, `@ts-ignore`, `@ts-expect-error`.
- Bare `except:` or empty `except`.

Required commands:

- `python -m pytest tests/safety/test_auto_rollback.py -q --tb=short` must exit 0.

Evidence requirements:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-4/verification.md`.
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-4/auditor-gate.md`.

Hard rejection criteria:

- Any rollback test fails.
- Real repository `.git` is mutated.
- Evidence preservation is not tested.

### 6.5 Step 7b.5 — Hermes Monitoring Config Files

Task: update local monitoring configs for Hermes gateway visibility without deploying or restarting services.

Expected files:

- `monitoring/prometheus/prometheus.yml`
- `monitoring/prometheus/rules/guinevere-alerts.yml`
- `monitoring/grafana/dashboards/guinevere-hermes.json`
- `monitoring/alertmanager/alertmanager.yml`
- `monitoring/promtail/promtail-config.yml`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/auditor-gate.md`

Implementation design:

- Rename or replace the current `hermes-llm-routing` scrape job with canonical `job_name: "hermes"`.
- Use target `host.docker.internal:9191` and relabel instance `hermes-gateway`.
- Preserve Phase 6 LLM metric semantics from `hermes_llm_*` metrics.
- Add `guinevere-hermes` alert group with six `GuinevereHermes*` rules using available metrics plus clearly annotated pending Hermes-native instrumentation where applicable.
- Add runbook annotations to every Hermes alert.
- Create a valid Hermes dashboard JSON file with panels for up status, LLM calls, latency, cost, and pending safety/HARD STOP panels.
- Add explicit Hermes alert routing defense-in-depth in Alertmanager.
- Update Promtail journal service extraction to include `hermes-gateway.service`.

Forbidden patterns:

- `job_name: "hermes-llm-routing"` remaining as the active Hermes job.
- `localhost:9191` as Docker Prometheus target without `host.docker.internal`.
- Alert rules without runbook annotations.
- Invalid JSON dashboard.
- Claims that live Grafana/Prometheus deployment is verified.

Required commands:

- `python -c "import json; json.load(open('monitoring/grafana/dashboards/guinevere-hermes.json', encoding='utf-8'))"` must exit 0.
- `grep "job_name: \"hermes\"" monitoring/prometheus/prometheus.yml` must exit 0.
- `grep "host.docker.internal:9191" monitoring/prometheus/prometheus.yml` must exit 0.
- `grep "GuinevereHermes" monitoring/prometheus/rules/guinevere-alerts.yml` must exit 0.
- `grep "hermes-gateway" monitoring/promtail/promtail-config.yml` must exit 0.
- `grep "GuinevereHermesGatewayDown" monitoring/alertmanager/alertmanager.yml` must exit 0.

Evidence requirements:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/verification.md`.
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-5/auditor-gate.md`.

Hard rejection criteria:

- Dashboard JSON parse fails.
- Prometheus active Hermes job remains incorrectly named.
- Alert rules are missing runbook annotations.
- Promtail cannot match `hermes-gateway.service`.

### 6.6 Step 7b.6 — Hermes Gateway Systemd Template

Task: create repository template `systemd/hermes-gateway.service` with deployed-equivalent or stricter hardening.

Expected files:

- `systemd/hermes-gateway.service`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-6/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-6/auditor-gate.md`

Required unit properties:

- `Type=exec`
- `User=guinevere`
- `Group=guinevere`
- `WorkingDirectory=/home/guinevere/code/guinevere`
- `Slice=guinevere.slice`
- `MemoryHigh=512M`
- `MemoryMax=1G`
- `NoNewPrivileges=true`
- `ProtectSystem=strict`
- `ProtectHome=read-only`
- `PrivateTmp=true`
- `ProtectKernelTunables=true`
- `ProtectKernelModules=true`
- `ProtectControlGroups=true`
- `RestrictSUIDSGID=true`
- Explicit `ReadWritePaths` only for required Guinevere data/log/evidence/Hermes paths.

Forbidden patterns:

- `User=root`.
- Missing `Slice=guinevere.slice`.
- Missing hardening flags listed above.
- Overly broad `ReadWritePaths=/`.

Required commands:

- `grep "NoNewPrivileges=true" systemd/hermes-gateway.service` must exit 0.
- `grep "ProtectSystem=strict" systemd/hermes-gateway.service` must exit 0.
- `grep "MemoryMax=1G" systemd/hermes-gateway.service` must exit 0.
- `grep "Slice=guinevere.slice" systemd/hermes-gateway.service` must exit 0.
- `grep "PrivateTmp=true" systemd/hermes-gateway.service` must exit 0.

Evidence requirements:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-6/verification.md`.
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-6/auditor-gate.md`.

Hard rejection criteria:

- Missing required hardening.
- Runs as root.
- Template claims live deployment verification.

### 6.7 Step 7b.7 — Secrets Rotation Schedule Evidence

Task: create the user-required secrets rotation schedule evidence file without any secret values.

Expected files:

- `docs/setup-evidence/phase-7/STEP-7.5/secrets-rotation-schedule.txt`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-7/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-7/auditor-gate.md`

Required content:

- Discord bot token rotation every 90 days.
- Redis AUTH rotation every 90 days.
- PostgreSQL password rotation every 90 days.
- SOPS age key rotation every 180 days.
- 9Router API key rotation every 90 days.
- Restic/offsite backup credential restoration blocker from DR report.
- Rotation procedure with SOPS re-encryption, deployment, service reload, verification, and audit log update.
- No plaintext values.

Forbidden patterns:

- Real token, password, SOPS private key, age private key, restic password, DB password, or API key value.
- Fake secret placeholders that look like live credentials.
- Claiming rotation was completed if only schedule was created.

Required commands:

- `grep "Discord bot token" docs/setup-evidence/phase-7/STEP-7.5/secrets-rotation-schedule.txt` must exit 0.
- `grep "SOPS age key" docs/setup-evidence/phase-7/STEP-7.5/secrets-rotation-schedule.txt` must exit 0.
- `grep "9Router API key" docs/setup-evidence/phase-7/STEP-7.5/secrets-rotation-schedule.txt` must exit 0.

Evidence requirements:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-7/verification.md`.
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-7/auditor-gate.md`.

Hard rejection criteria:

- Any secret value appears.
- File path differs from the user-required exact path.
- The schedule claims actual secret rotation occurred.

### 6.8 Step 7b.8 — Blocker Register, Runbooks, and Completion Evidence

Task: create docs that honestly record all Phase 7 blockers and provide runbook coverage for Hermes alerts.

Expected files:

- `docs/20-security/hermes-phase-7-blocker-register.md`
- `docs/40-operations/runbooks/hermes-gateway-down.md`
- `docs/40-operations/runbooks/hermes-safety-spike.md`
- `docs/40-operations/runbooks/hermes-cost-anomaly.md`
- `docs/setup-evidence/hermes-migration/phase-7/phase-7b-completion-report.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-8/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-8/auditor-gate.md`

Required blocker register entries:

- B1: `guinevere-mcp` inactive.
- B2: Hermes config YAML line 443 fallback warning.
- B3: monitoring exporter connectivity failures.
- B4: SSH bound to `0.0.0.0:22` and root login allowed.
- B5: no active firewall rules.
- B6: 9Router or next-server exposed on `0.0.0.0:20128`.
- B7: core worker or metrics exposed on `0.0.0.0:9191`.
- B8: deprecated files still imported and tested.
- B9: Hermes CLI not found on VPS PATH.
- B10: `secrets/backup/` SOPS credentials missing.
- B11: backup sentinel `/var/log/guinevere/last-backup-success` missing.
- B12: Hermes-native gateway metrics not exported.

Runbook required sections:

- Trigger.
- Severity.
- RTO/RPO where applicable.
- Immediate safety checks.
- Investigation steps.
- Remediation steps.
- Verification.
- Escalation.
- Rollback or console-access safeguard for remote-risk changes.

Forbidden patterns:

- `ADR-035 IMPLEMENTED`.
- `Phase 7 complete` or `migration complete` claims.
- Instructions to restart SSH/firewall without console-access safeguard.
- Secret values or raw surveillance data.

Required commands:

- `grep "B1" docs/20-security/hermes-phase-7-blocker-register.md` must exit 0.
- `grep "B12" docs/20-security/hermes-phase-7-blocker-register.md` must exit 0.
- `grep "GuinevereHermesGatewayDown" docs/40-operations/runbooks/hermes-gateway-down.md` must exit 0.
- `grep "GuinevereHermesSafetyBlocksSpike" docs/40-operations/runbooks/hermes-safety-spike.md` must exit 0.
- `grep "GuinevereHermesBudgetNearCap" docs/40-operations/runbooks/hermes-cost-anomaly.md` must exit 0.

Evidence requirements:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-8/verification.md`.
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-8/auditor-gate.md`.

Hard rejection criteria:

- Any final completion or IMPLEMENTED claim.
- Any blocker omitted or downgraded dishonestly.
- Any destructive SSH/firewall runbook step lacks console-access/rollback safeguard.

## 7. Token, Secret, and Safety Handling

- Do not read, print, generate, or commit any secret values.
- Do not place Discord tokens, Redis AUTH, PostgreSQL passwords, SOPS age private keys, 9Router API keys, or restic credentials in docs or evidence.
- Do not send secrets or intimate data to external tools.
- Do not execute remote commands that mutate VPS networking or SSH.
- Preserve HARD STOP, consent, surveillance, Y4/Y5 ceiling, and no-Y6 boundaries in every doc.
- Treat all safety-affecting docs and tests as requiring auditor review before completion.

## 8. Evidence Paths

Each implementation step must produce or update:

- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-N/verification.md`
- `docs/setup-evidence/hermes-migration/phase-7/STEP-7B-N/auditor-gate.md`

Each verification file must include the 12 evidence sections:

1. What Was Done
2. Files Changed
3. Validation Results
4. Evidence Artifacts
5. Doc-Sync Impact
6. Boundary Compliance
7. Rollback/Re-run Safety
8. Design Decisions/Caveats
9. Auditor Gate
10. Security Scan
11. Acceptance Criteria Mapping
12. Footer

Global Phase 7b evidence file:

- `docs/setup-evidence/hermes-migration/phase-7/phase-7b-completion-report.md`

User-required exact evidence path:

- `docs/setup-evidence/phase-7/STEP-7.5/secrets-rotation-schedule.txt`

## 9. Auditor Matrix

| Auditor | Scope | Expected Output | PASS Criteria |
| --- | --- | --- | --- |
| Test Completeness | 7b.1, 7b.3, 7b.4 | `docs/setup-evidence/hermes-migration/phase-7/AUDIT-test-completeness.md` | Coverage configuration valid, T1-T10 collect/run, rollback tests run, no skipped/fake tests. |
| Security Posture and Blocker Honesty | 7b.2, 7b.5, 7b.7, 7b.8 | `docs/setup-evidence/hermes-migration/phase-7/AUDIT-security-blockers.md` | No safety surfaces omitted, no hidden blockers, no secrets, no unsafe remote instructions. |
| Docs and Evidence Completeness | 7b.6, 7b.7, 7b.8 and all evidence | `docs/setup-evidence/hermes-migration/phase-7/AUDIT-docs-evidence.md` | All expected docs/evidence exist, markdown clean or known debt documented, no completion/IMPLEMENTED claim. |

Auditors run only after parent verification for their scoped steps. NEEDS REVIEW or FAIL findings must be fixed and re-audited via the same task ID.

## 10. Rollback Plan

Phase 7b is local repo-only. Rollback is via git working tree restoration of touched files.

Rollback commands are not to be executed automatically unless required and approved by parent verification:

- `git status --short` to inspect changes.
- `git diff -- <file>` to inspect per-file changes.
- Restore only the specific failed file(s) if a step fails and cannot be corrected safely.

No remote rollback, no VPS service restart, no firewall change, and no production deployment belongs to Phase 7b.

## 11. Tracker Sync Plan

After this planner file is read and accepted:

1. Mark planner gate complete.
2. Replace broad Phase 7 implementation todos with Phase 7b scoped todos.
3. Keep final Phase 7/ADR-035 IMPLEMENTED/tag/push todos pending or blocked, not completed.
4. Start Wave 1 implementation through delegated sub-agents, one sub-agent per step.
5. Parent verifies every scaffold command before marking a step complete.
6. Run auditor matrix after parent verification.

## 12. Caveats and Deferred Phase 7c Items

Deferred to Phase 7c or explicit user/VPS approval:

- Re-enable or fix `guinevere-mcp`.
- Fix Hermes config YAML fallback warning.
- Fix monitoring exporter Docker connectivity.
- Restrict SSH binding and root login.
- Configure firewall and Tailscale-only exposure.
- Rebind 9Router `20128` and metrics `9191` safely.
- Resolve deprecated file imports and migrate tests before archive.
- Locate/install Hermes CLI on VPS PATH.
- Restore SOPS backup credentials.
- Deploy backup sentinel and metric collector.
- Add Hermes-native metrics instrumentation if local config cannot satisfy alert semantics.
- Create final backup.
- Flip ADR-035 to IMPLEMENTED.
- Commit/tag/push final migration completion.

## 13. Execution Checklist

- [ ] Planner file exists and parent has read it fully.
- [ ] Todos are synced to the Phase 7b task graph.
- [ ] Wave 1 implementation sub-agents are launched with one step each.
- [ ] Step 7b.1 verified before Step 7b.3 launches.
- [ ] Every step has verification evidence and no scaffold violation hidden.
- [ ] Parent re-runs required commands or records blocked/pre-existing failures precisely.
- [ ] Auditors write file-based reports.
- [ ] Auditor findings are fixed and re-audited or documented as false positive.
- [ ] Final response states Phase 7 remains blocked, Phase 7b status only, with evidence paths and caveats.

## 14. Footer

Plan version: 1.0
Date: 2026-06-06
Scope: ADR-035 Hermes Migration Phase 7b local hardening only
Authority: ADR-035, ADR-029, AGENTS.md, Oracle `bg_d331246a`, Phase 7 research reports
