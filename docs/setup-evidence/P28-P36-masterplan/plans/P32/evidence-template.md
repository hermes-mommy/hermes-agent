---
title: "P32 — Evidence Template (12 Sections per AGENTS.md §11)"
status: "Plan Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan — P32"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
type: "evidence_template"
---

# P32 — Evidence Template

> **Halo sayang, namaku Guinevere.** Template evidence P32 dengan fokus khusus pada permanent operation validation dan 8 binary criteria. Boundary Compliance wajib hijau semua. (NO SOAK TEST — P32 operates as permanent continuous operation per brainstorm 2026-06-28.)

---

## Section 1 — What Was Done

> **Renderer note:** Each of 7 implementation steps. Special focus on Step 6 (permanent operation validation) with checkpoint timestamps.

### §1.1 Step 1 — Fork Repository Bootstrap

- **Date:** YYYY-MM-DD HH:MM
- **Executor:** sub-agent ID, role
- **Outcome:** PASS
- **Narrative:** Fork created at `github.com/fazulfim/hermes-agent`; upstream `hermes-agent` v0.15.2 cloned; FORK_NOTES.md added; LICENSE verified Apache-2.0; zero secret scan via `git secrets` + `detect-secrets`.

### §1.2 Step 2 — Persistent Task Registry

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `hermes_lifecycle/registry.py` written (~ LOC); PostgreSQL migration applied; 6+ tests pass; restart-persistence verified (10 tasks survived `kill -9`).

### §1.3 Step 3 — Model Pool Hot-Swap with Personality Drift Check

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `hermes_model/pool.py` + `drift_check.py` written (~ LOC); 6+ tests pass; hot-swap latency ≤ 30s; drift check active (ADR-067: Y4 as starting baseline, bebas tanpa batas, no yandere level cap, Y6 concept REMOVED).

### §1.4 Step 4 — Fork Governance Policy

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** Governance doc written; founder 2/2 review recorded (with timestamps); Ratchet Tier 1-2 references present; Tier 3/4 explicitly excluded from auto-merge.

### §1.5 Step 5 — Mode Selector

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `src/runtime/mode.py` written; `hermes-runtime-fork.service` and `hermes-runtime-p24.service` units active; both modes verified via `--mode … --probe`.

### §1.6 Step 6 — Permanent Operation Validation (NO SOAK TEST)

- **Date (start):** YYYY-MM-DD HH:MM UTC
- **Checkpoints:** t=6h, t=12h, t=18h, t=24h
- **Outcome:** PASS (all 4 checkpoints; all 8 criteria PASS at each)
- **Narrative:** Continuous permanent operation with fork-native mode; checkpoint snapshots captured; alerts configured; if any checkpoint FAIL, operation invalid + restart. (NO SOAK TEST — permanent continuous operation per brainstorm 2026-06-28.)

#### Checkpoint summary table

| Checkpoint | Time UTC | Criteria PASS | Notable |
|---|---|---|---|
| t=6h | YYYY-MM-DD HH:MM | 8/8 | (no issues) |
| t=12h | YYYY-MM-DD HH:MM | 8/8 | (no issues) |
| t=18h | YYYY-MM-DD HH:MM | 8/8 | (no issues) |
| t=24h | YYYY-MM-DD HH:MM | 8/8 | operation PASS |

### §1.7 Step 7 — Migration Runbook + S3 + Adversarial

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** Migration runbook written; S3 backup scope extended (`fork-scope.yaml`); adversarial tests pass (bot identity preserved, wallet-empty preserved, HARD STOP ≤ 1 message (ADR-062: dev workflow only)); one-way back procedure tested manually.

---

## Section 2 — Files Changed

| Path | LOC / Status | Type | Owner |
|---|---|---|---|
| `github.com/fazulfim/hermes-agent` (fork repo) | NEW | fork | Step 1 |
| `hermes_lifecycle/registry.py` (fork) | +~50 LOC | NEW (Code Addition #1) | Step 2 |
| `hermes_lifecycle/__init__.py` (fork) | +5 | NEW | Step 2 |
| `hermes_model/pool.py` (fork) | +~60 LOC | NEW (Code Addition #2) | Step 3 |
| `hermes_model/drift_check.py` (fork) | +~40 LOC | NEW | Step 3 |
| `hermes_model/__init__.py` (fork) | +5 | NEW | Step 3 |
| `src/runtime/mode.py` (Guinevere repo) | +~80 | NEW | Step 5 |
| `src/runtime/__init__.py` | +5 | NEW | Step 5 |
| `migrations/P32-001_hermes_tasks.sql` | +~30 | NEW | Step 2 |
| `ops/systemd/hermes-runtime-fork.service` | +~20 | NEW | Step 5 |
| `ops/systemd/hermes-runtime-p24.service` | +~20 | NEW | Step 5 |
| `hermes-config/runtime/<slug>/runtime_mode.yaml` | +~15 | NEW | Step 5 |
| `docs/setup-evidence/P28-P36-masterplan/governance/P32-ForkGovernance_v1.0.md` | +~150 | NEW | Step 4 |
| `docs/setup-evidence/P28-P36-masterplan/evidence/P32/migration-runbook.md` | +~80 | NEW | Step 7 |
| `ops/s3-backup/fork-scope.yaml` | +~30 | NEW | Step 7 |
| `tests/hermes_lifecycle/test_registry.py` (fork) | +~150 | NEW | Step 2 |
| `tests/hermes_model/test_pool.py` (fork) | +~150 | NEW | Step 3 |
| `tests/runtime/test_mode.py` | +~80 | NEW | Step 5 |
| `tests/operation/test_p32_operation.py` | +~200 | NEW | Step 6 |
| `tests/adversarial/test_p32_adversarial.py` | +~150 | NEW | Step 7 |
| `docs/README.md` | +N | MOD | Parent (post-implementation) |
| `docs/40-operations/45-InternalOpsManual_v1.0.md` | +N | MOD | Step 5 (systemd units) |
| **TOTAL fork LOC additions** | **~200 LOC** | (matches plan budget) | |

---

## Section 3 — Validation Results

| Step | ruff/flake8 | mypy | pytest | runtime smoke | operation criterion | exit code |
|---|---|---|---|---|---|---|
| 1 | n/a | n/a | n/a | `git clone` exit 0; `detect-secrets` 0 | n/a | 0 |
| 2 | 0 | 0 | ≥6 tests exit 0, cov ≥ 90% | migration applies; restart-persistence OK | n/a | 0 |
| 3 | 0 | 0 | ≥6 tests exit 0, cov ≥ 90% | hot-swap <30s; drift check active (ADR-067) | n/a | 0 |
| 4 | n/a | n/a | n/a | markdown frontmatter parse OK; co-review recorded | n/a | 0 |
| 5 | 0 | 0 | ≥4 tests exit 0 | both systemd units active; both modes probe OK | n/a | 0 |
| 6 | n/a | n/a | 0 | permanent operation_runner exit 0 (NO SOAK TEST) | 8/8 PASS at t=24h | 0 |
| 7 | n/a | n/a | 0 (adversarial) | backup dry-run exit 0; one-way-back OK | n/a | 0 |

**Aggregate:** all 7 steps exit 0; zero linter violations; zero type errors; zero test failures; 8/8 operation criterion PASS at all checkpoints.

---

## Section 4 — Evidence Artifacts

| Artifact | Path |
|---|---|
| Sub-step evidence files | `evidence/P32/steps/1-fork-bootstrap/evidence.md` … `/7-migration/evidence.md` |
| Verification report | `docs/setup-evidence/P28-P36-masterplan/evidence/P32/verification.md` |
| Auditor gate | `docs/setup-evidence/P28-P36-masterplan/evidence/P32/auditor-gate.md` |
| Fork commit hashes | `evidence/P32/operational/fork-commit-hashes.txt` |
| Permanent operation checkpoint log | `evidence/P32/operational/operation-checkpoint-t6h.log` … `/operation-checkpoint-t24h.log` |
| Persona config byte-equal snapshot | `evidence/P32/operational/persona-snapshot-t0.txt` + `/persona-snapshot-t24h.txt` (diff = 0) |
| Prometheus screenshot per checkpoint | `evidence/P32/operational/prom-operation-t6h.png` … `/prom-operation-t24h.png` |
| Mode probe output | `evidence/P32/operational/mode-probe-output.txt` |
| Migration runbook | `docs/setup-evidence/P28-P36-masterplan/evidence/P32/migration-runbook.md` |
| One-way back procedure transcript | `evidence/P32/operational/one-way-back-transcript.md` |
| Adversarial test transcript | `evidence/P32/operational/adversarial-test-transcript.md` |
| S3 retention check | `evidence/P32/operational/s3-fork-scope-retention.txt` |
| Fork secret scan report | `evidence/P32/operational/fork-secret-scan.txt` |
| Co-review record | `evidence/P32/operational/founder-co-review.txt` (with timestamps) |

---

## Section 5 — Doc-Sync Impact

- `docs/README.md` — timeline entry for P32 PASS; note: P32 = External Presence & Tools (repurposed from original fork-integration scope per brainstorm 2026-06-28).
- `adr/ADR-056-p32-fork-integration.md` — **(DELETED — superseded by ADR-062 + P24 v2.0)**. Cross-link to fork governance doc via ADR-062 + P24 v2.0 instead.
- `docs/setup-evidence/P28-P36-masterplan/governance/P32-ForkGovernance_v1.0.md` — new file (governance family).
- `docs/40-operations/45-InternalOpsManual_v1.0.md` — add fork-runtime systemd unit section.
- `docs/40-operations/43-DisasterRecoveryPlan_v1.0.md` — extend DR scenario with fork runtime failure / one-way back.
- Cross-references:
  - `docs/00-core/02-TechnicalArchitecture_v2.0.md` — note: runtime_mode selector.
  - `docs/00-core/03-AgentLoopSpec_v2.0.md` — note: lifecycle hooks (Persistent Task Registry).

**Doc-sync verify:** all paths above exist; `grep` for `P32\|fork-native\|hermes-agent` returns at least one entry per file.

---

## Section 6 — Boundary Compliance

> **ALL 7 rows must be PASS. Any RED = re-plan, not silent fix.**

| Boundary | Check | Result | Evidence |
|---|---|---|---|
| **No persona drift** | Drift check active (ADR-067: bebas tanpa batas, Y4 as baseline only); persona config byte-equal at t=0 and t=24h | PASS | `evidence/operational/persona-snapshot-t0.txt` + `persona-snapshot-t24h.txt` (diff = 0) |
| **No consent violation** | No fork code reads/consumes consent ledger without explicit channel-level opt-in (dev workflow only, ADR-062/066) | PASS | `evidence/operational/consent-leak-check.md` |
| **No surveillance overreach** | Fork does not extend SurveillanceDataPolicy; P22 default unchanged | PASS | `evidence/operational/fork-surveillance-leak-check.md` |
| **No Y6 ceiling** | Drift check active (ADR-067: Y6 concept REMOVED; bebas tanpa batas, no yandere level cap); runtime config schema has no Y6 | PASS | `evidence/operational/drift-check-y6-removal-test.md` |
| **No HARD STOP bypass** | HARD STOP filter present in fork actor state; manual trigger during operation ≤ 1 message (ADR-062: dev workflow only) | PASS | `evidence/operational/hard-stop-during-operation.md` |
| **No secret/intimate exposure** | Fork pre-commit hook with `detect-secrets`; CI blocks merge; zero plaintext in evidence | PASS | `evidence/operational/fork-secret-scan.txt` |
| **No consent revocation bypass** | Consent revocation event halts fork runtime within 1 message; no deferred mode (dev workflow only, ADR-062/066) | PASS | `evidence/operational/consent-revocation-fork-test.md` |

**Aggregate boundary verdict:** ALL 7 GREEN. If ANY RED → STOP, re-plan, escalate to Faiz + Oracle.

---

## Section 7 — Rollback / Re-run Safety

| Step | Rollback Action | Re-run Safety |
|---|---|---|
| 1 | Archive fork repo (no delete); GitHub retains history; tag `v0.15.2-guinevere.1` is immutable once cut | `git clone` is naturally idempotent |
| 2 | `alembic downgrade -1`; remove `hermes_lifecycle/` from import path | Migration is idempotent (`alembic upgrade head` is re-applicable) |
| 3 | Revert commits; restore drift check to baseline (ADR-067: bebas tanpa batas) | Hot-swap is idempotent (later overrides earlier) |
| 4 | Doc version revert (governance doc is rev'd, not deleted) | Doc is a mark-down file; revert is git revert |
| 5 | Stop fork service; flip to `mode: P24-native`; start P24-native service | `mode: P24-native` is always-available fallback |
| 6 | Stop operation runner; promote t=0 snapshot as fallback runtime; document failure | Permanent operation validation re-runnable from t=0 (NO SOAK TEST) |
| 7 | Stop fork service; revert S3 scope; manual one-way back per runbook | One-way back procedure verified manually |

**Aggregate rollback verdict:** all 7 steps have safe-rollback path; one-way back is procedural and documented.

---

## Section 8 — Design Decisions / Caveats

| Decision | Rationale | Caveat |
|---|---|---|
| **Fully-owned fork (not upstream PR)** | Per P24 masterplan discussion; full fork = lower governance friction than upstream PR cycle | Quarterly upstream rebase is needed; rebase conflict resolution is governance-doc-defined |
| **2 code additions only (~200 LOC)** | Bounded; matches research synthesis §3.1 (P32 = External Presence & Tools, P24 = full plan); lower review burden | Future additions need new P32.X waves |
| **`P24-native` default** | Reversibility; P24 native fork is the standard runtime per brainstorm 2026-06-28 | Boot order: P24-native first to confirm baseline |
| **Personality Drift check (ADR-067)** | Y4 as starting baseline only; bebas tanpa batas; no yandere level cap; Y6 concept REMOVED | Drift check is per-Hermes; peer monitoring (Guin↔Pharsa) at equal status (setara) |
| **Permanent operation validation with 4 checkpoints** | Checkpoint design surfaces intermittent failure; one-way forward means failure → revert. NO SOAK TEST per brainstorm 2026-06-28. | Operation is production-bound; potential impact is bounded by drift check + Y4 baseline |
| **Concurrently running fork + P24-native unit during operation** | Side-by-side comparison | Resource overhead: ~2x RAM during operation; reduced to 1x post-operation |
| **Fork governance doc in `setup-evidence/` not `docs/`** | Masterplan-level governance; standard governance lives in `docs/10-governance/` | Move to `docs/10-governance/` post-P32 (ADR-056 DELETED — superseded by ADR-062 + P24 v2.0) |

---

## Section 9 — Auditor Gate

- **Compliance auditor:** `audit-reports/p32-step-1-fork-bootstrap.md` — verdict PASS.
- **Runtime auditor:** `audit-reports/p32-step-2-task-registry.md` — verdict PASS.
- **Safety auditor:** `audit-reports/p32-step-3-pool-hot-swap.md` — verdict PASS.
- **Governance auditor:** `audit-reports/p32-step-4-governance.md` — verdict PASS.
- **Ops auditor:** `audit-reports/p32-step-5-mode-selector.md` — verdict PASS.
- **Operation validation auditor:** `audit-reports/p32-step-6-operation.md` — verdict PASS (8/8 criteria at 4/4 checkpoints, NO SOAK TEST).
- **DR auditor:** `audit-reports/p32-step-7-migration.md` — verdict PASS.
- **Boundary auditor:** `audit-reports/p32-boundary.md` — verdict PASS.

**Aggregate auditor verdict:** 8/8 PASS. Auditor orchestrator writes `evidence/P32/auditor-gate.md` with overall PASS.

---

## Section 10 — Security Scan

| Scan | Command | Expected | Got |
|---|---|---|---|
| Plaintext secret in fork | `git secrets --scan` (or `detect-secrets scan`) on fork repo | 0 | 0 |
| Plaintext secret in evidence | `grep -rE "([A-Za-z0-9_-]{59})" docs/setup-evidence/P28-P36-masterplan/evidence/P32/` | 0 | 0 |
| Plaintext secret in CI logs | `grep -rE "([A-Za-z0-9_-]{59})" /var/log/ci/p32/` | 0 | 0 |
| Forbidden patterns in fork code | `grep -rE "as any\|@ts-ignore\|# type:ignore\|except:" hermes_lifecycle/ hermes_model/ src/runtime/` | 0 | 0 |
| Empty catch in fork | `grep -rE "except.*:.*pass" hermes_lifecycle/ hermes_model/ src/runtime/` | 0 | 0 |
| Fork pre-commit hook | `ls .git/hooks/pre-commit` shows detect-secrets hook | yes | yes |
| CI secret scan | GitHub Actions secret-scan step | blocks on violation | blocks |
| S3 retention | `aws s3api get-object-retention` for fork-scope keys | COMPLIANCE | COMPLIANCE |
| Drift check active (ADR-067) | drift check module importable; no Y6 ceiling concept | drift check active; Y6 REMOVED | confirmed |
| Persona byte-equal | sha256sum t=0 vs t=24h | identical | identical |

**Aggregate security verdict:** clean. No secret. No suppression. No drift.

---

## Section 11 — Acceptance Criteria Mapping

> **Map each of 8 binary criteria to evidence.**

| Criterion | Evidence Path |
|---|---|
| 1. Fork boots from `mode: fork-native` | `evidence/operational/mode-probe-output.txt` |
| 2. Persistent Task Registry survives restart | `evidence/P32/steps/2/evidence.md` (restart-persistence test) |
| 3. Model Pool hot-swap < 30s | `evidence/P32/steps/3/evidence.md` (latency benchmark) |
| 4. Personality Drift check active (ADR-067) | `evidence/P32/steps/3/evidence.md` (drift check tests; Y6 concept REMOVED) |
| 5. Discord bot identity parity (P31) | `evidence/operational/adversarial-test-transcript.md` (P31 invariants under fork) |
| 6. No persona drift | `evidence/operational/persona-snapshot-t0.txt` vs `/persona-snapshot-t24h.txt` (diff = 0) |
| 7. No HARD STOP bypass (ADR-062: dev workflow only) | `evidence/operational/hard-stop-during-operation.md` |
| 8. No secret exposure | `evidence/operational/fork-secret-scan.txt` + grep result above |

**Map-hard-rejection:** 8/8 hard rejections in P32 §8 mapped to Section 9 auditor reports.

---

## Section 12 — Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | P32 evidence-template initial draft |
| 1.1 | 2026-06-28 | Guinevere | Round-2 auditor fix: replaced all stale runtime-concept refs with current paradigm (ADR-067 drift check, P24-native mode, permanent operation validation, deleted ADR annotated, ADR-062/067 disclaimers) |

> **STRICTLY PRIVATE & CONFIDENTIAL.** Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` and AGENTS.md §0. Distribution restricted to Faiz + Guinevere + Pharsa.
