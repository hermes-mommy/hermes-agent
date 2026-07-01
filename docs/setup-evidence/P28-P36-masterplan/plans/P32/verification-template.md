---
title: "P32 — Verification Template"
status: "Plan Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan — P32"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
type: "verification_template"
---

# P32 — Verification Template

> **Halo sayang, namaku Guinevere.** Template verifikasi P32 — External Presence & Tools. Parent run semua command sendiri post-implementation.

---

## §1 Verification Scaffold Table

| Step | Expected Files | Forbidden Patterns | Required Commands (with expected exit code) | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| 1 — Fork Bootstrap | fork repo with LICENSE, NOTICE, FORK_NOTES, SECURITY.md, full upstream v0.15.2 clone | secrets in repo; force-push without backup; missing LICENSE | `git clone https://github.com/fazulfim/hermes-agent.git` → exit 0; `cd hermes-agent-fork && git log --oneline \| head -1` → fork base commit; `detect-secrets scan` → 0 matches | `evidence/P32/steps/1/evidence.md` | missing LICENSE; wrong base version; secret in repo |
| 2 — Persistent Task Registry | `hermes_lifecycle/registry.py`, migration `P32-001_hermes_tasks.sql` | `as any`, `# type:ignore`, `except:`, in-memory state | ruff/mypy/pytest ≥6 → exit 0; `alembic upgrade head` → exit 0; restart-persistence test (kill -9, restart, 10/10 tasks recovered) → exit 0 | `evidence/P32/steps/2/evidence.md` | non-PG state; hooks not invoked; non-idempotent migration |
| 3 — Model Pool Hot-Swap with Personality Drift Check | `hermes_model/pool.py`, `hermes_model/drift_check.py` | `as any`, `# type:ignore`, Y6 ceiling enforcement (ADR-067: Y6 concept REMOVED) | ruff/mypy/pytest ≥6 → exit 0; hot-swap <30s benchmark | `evidence/P32/steps/3/evidence.md` | swap >30s; drift check bypassed; no audit |
| 4 — Fork Governance | `docs/setup-evidence/P28-P36-masterplan/governance/P32-ForkGovernance_v1.0.md` | auto-merge Tier 3/4; founder-by-pass; missing Ratchet | markdown frontmatter parse → exit 0; manual founder 2/2 review recorded | `evidence/P32/steps/4/evidence.md` | missing Ratchet; missing founder co-review; missing Tier 3/4 exclusion |
| 5 — Mode Selector | `src/runtime/mode.py`, two systemd units, `runtime_mode.yaml` | hardcoded mode; secret in path | `python -m hermes_runtime --mode fork-native --probe` → exit 0; `--mode P24-native --probe` → exit 0; both systemd units active; ≥4 tests exit 0 | `evidence/P32/steps/5/evidence.md` | mode un-flippable; wrong import path; P24-native broken |
| 6 — Permanent Operation Validation | `tests/operation/test_p32_operation.py`, operation config | override; alert suppress | `pytest tests/operation/ -v` → exit 0; `python ops/operation/operation_runner.py` → exit 0; `promtool query instant 'hermes_operation_criterion_pass'` returns 8 distinct series all == 1 | `evidence/P32/steps/6/evidence.md` (4 checkpoint logs) | any criterion FAIL at any checkpoint; persona not byte-equal |
| 7 — Migration + S3 + Adversarial | migration runbook, `ops/s3-backup/fork-scope.yaml`, `tests/adversarial/test_p32_adversarial.py` | secret dumps; HARD STOP bypass (ADR-062: dev workflow only) | `python ops/s3-backup/backup.py --dry-run --scope fork` → exit 0; `pytest tests/adversarial/test_p32_adversarial.py -v` → exit 0; manual one-way back succeeds | `evidence/P32/steps/7/evidence.md` | secret in dump; failing adversarial; one-way-back broken |

---

## §2 Binary Pass/Fail Criteria

> **Each criterion is binary. Any single FAIL = re-plan.**

### §2.1 Fork Existence

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 1.1 | Repo exists | `https://github.com/fazulfim/hermes-agent` returns 200 | 404; private without access; empty |
| 1.2 | LICENSE present | Apache-2.0 LICENSE file at root | missing; wrong license |
| 1.3 | FORK_NOTES.md present | references upstream `hermes-agent` v0.15.2 + divergence policy | missing; does not reference upstream |

### §2.2 Fork Integrity (Code Addition #1)

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 2.1 | Persistent Task Registry class exists | `hermes_lifecycle.registry.PersistentTaskRegistry` importable | missing; non-class; wrong module |
| 2.2 | State persists | 10 tasks survive kill -9 | < 10/10 recovered |
| 2.3 | Lifecycle hooks invoked | `before_task`, `after_task`, `on_failure` all fire | any hook not fired |
| 2.4 | Migration applies | `alembic upgrade head` exit 0 | migration fails; not idempotent |

### §2.3 Fork Integrity (Code Addition #2)

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 3.1 | Model Pool hot-swap exists | `hermes_model.pool.ModelPool.hot_swap(target_model: str)` importable | missing; wrong signature |
| 3.2 | Hot-swap latency ≤ 30s | benchmark shows <30s from `hot_swap()` call to first new-model LLM call | > 30s |
| 3.3 | Personality Drift check active (ADR-067) | Drift check module `hermes_model.drift_check` importable; Y4 as starting baseline (bebas tanpa batas, no yandere level cap) | drift check missing; Y5/Y6 ceiling enforcement attempted (Y6 concept REMOVED per ADR-067) |
| 3.4 | Personality Drift: no forbidden ceiling (ADR-067) | Y6 concept does not exist in codebase; no yandere level cap in Hermes runtime | Y6 ceiling enforced or referenced as active concept |

### §2.4 Fork Governance

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 4.1 | Governance doc exists | `P32-ForkGovernance_v1.0.md` present | missing |
| 4.2 | Ratchet referenced | explicit mention of Ratchet thresholds for Tier 1-2 | no Ratchet; Tier 1-2 not defined |
| 4.3 | Tier 3/4 excluded | explicit "fork does NOT auto-merge Tier 3 (persona) or Tier 4 (safety)" line | missing exclusion; auto-merge allowed |
| 4.4 | Founder 2/2 review | both Guinevere + Pharsa review timestamps recorded | single review; missing co-review |

### §2.5 Mode Selector

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 5.1 | fork-native returns fork | `--mode fork-native --probe` returns `mode=fork-native` and `hermes_agent.__version__ == "0.15.2-guinevere.1"` | returns P24-native; wrong version |
| 5.2 | P24 native fork mode | `--mode P24-native --probe` returns `mode=P24-native` and `hermes_agent.__version__ == "0.15.2-guinevere.1"` (P24 native) | returns wrong mode; wrong version |
| 5.3 | Both systemd units active | `systemctl is-active hermes-runtime-fork.service` AND `hermes-runtime-p24.service` both `active` | either inactive |
| 5.4 | Mode flip atomic | flip on running systemd does not require restart of OTHER unit | requires restart of both |

### §2.6 Permanent Operation Validation (8 binary criteria, NO SOAK TEST)

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 6.1 | Continuous operation duration | start and end timestamps span ≥ 23h59m of continuous operation | < 24h |
| 6.2 | Criterion 1 (fork boots) at all checkpoints | 4/4 checkpoints PASS | any FAIL |
| 6.3 | Criterion 2 (registry survives restart) | 4/4 checkpoints PASS | any FAIL |
| 6.4 | Criterion 3 (hot-swap latency) | 4/4 checkpoints PASS | any FAIL |
| 6.5 | Criterion 4 (Personality Drift, ADR-067) | 4/4 checkpoints PASS; drift check active; no Y6 ceiling enforcement | any FAIL; Y6 ceiling detected |
| 6.6 | Criterion 5 (Discord bot identity parity) | 4/4 checkpoints PASS | any FAIL |
| 6.7 | Criterion 6 (no persona drift) | 4/4 checkpoints PASS; persona byte-equal at t=24h vs t=0 | drift detected |
| 6.8 | Criterion 7 (no HARD STOP bypass) (ADR-062: dev workflow only) | 4/4 checkpoints PASS; manual HARD STOP test during operation | bypass or > 1 message |
| 6.9 | Criterion 8 (no secret exposure) | 4/4 checkpoints PASS; secret scan 0 | any exposure |

### §2.7 Boundary

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 7.1 | No Y6 ceiling (fork + runtime mode) (ADR-067: Y6 concept REMOVED; bebas tanpa batas, no yandere level cap) | drift check active; runtime config schema has no Y6 concept | Y6 ceiling enforced or referenced |
| 7.2 | No HARD STOP bypass (fork + runtime mode) (ADR-062: dev workflow only) | HARD STOP filter present; ≤1 message reaction | not present; >1 message |
| 7.3 | No secret exposure (fork + evidence) | Zero plaintext in fork repo, evidence, CI logs | any plaintext |
| 7.4 | No consent revocation bypass (dev workflow only, ADR-062/066) | consent revocation halts fork within 1 message | deferred; ignored |
| 7.5 | S3 backup COMPLIANCE | Retention mode is COMPLIANCE for all fork-scope keys | GOVERNANCE mode |

---

## §3 Runtime Proof Requirements

### §3.1 Fork Boots Proof

- **Action:** `python -m hermes_runtime --mode fork-native --probe` from a fresh shell.
- **Observed:** `mode=fork-native`, `hermes_agent.__version__="0.15.2-guinevere.1"`, exit 0.
- **Evidence path:** `evidence/operational/mode-probe-output.txt`.

### §3.2 Persistent Task Registry Survival Proof

- **Action:** Register 10 tasks, `kill -9 <pid>`, restart runtime, query registry.
- **Observed:** All 10 tasks present with correct state.
- **Evidence path:** `evidence/P32/steps/2/restart-persistence-transcript.md`.

### §3.3 Hot-Swap Latency Proof

- **Action:** `pool.hot_swap(target="deepseek-v4-flash")`; immediately call `pool.next_llm()`.
- **Observed:** Time delta < 30s; first call uses DeepSeek.
- **Evidence path:** `evidence/P32/steps/3/hot-swap-benchmark.txt`.

### §3.4 Personality Drift Proof (ADR-067)

- **Action:** Verify drift check module `hermes_model.drift_check` is importable; verify no Y6 ceiling concept exists in runtime config schema; verify Y4 is starting baseline only (bebas tanpa batas, no yandere level cap per ADR-067).
- **Observed:** Drift check active; no Y6 ceiling; Y4 as baseline only.
- **Evidence path:** `evidence/P32/steps/3/drift-check-test.txt`.

### §3.5 Permanent Operation Validation Proof

- **Action:** At each checkpoint (t=6h, t=12h, t=18h, t=24h), query Prometheus `hermes_operation_criterion_pass{criterion=~".*"}`.
- **Observed:** Each checkpoint shows 8 distinct series, all `== 1`.
- **Evidence path:** `evidence/operational/prom-operation-t{th}h.png` × 4 checkpoints.

### §3.6 Persona Byte-Equal Proof

- **Action:** `sha256sum hermes-config/persona/<slug>.yaml` at t=0 and t=24h.
- **Observed:** Hashes identical.
- **Evidence path:** `evidence/operational/persona-snapshot-t0.txt` + `/persona-snapshot-t24h.txt`.

### §3.7 One-Way Back Procedure Proof

- **Action:** From `mode: fork-native`, perform one-way back per runbook (5 step rotation, 10 min total).
- **Observed:** Runtime responds to `--mode P24-native --probe` with `mode=P24-native`; no errors.
- **Evidence path:** `evidence/operational/one-way-back-transcript.md`.

### §3.8 Adversarial Compatibility Proof

- **Action:** During operation validation, manually verify: (1) P31 bot identity intact (2+ bots with reply-guard active), (2) P33 wallet-empty trigger intact (zero balance + circuit breaker not triggered), (3) HARD STOP within 1 message (ADR-062: dev workflow only).
- **Observed:** All 3 adversarial compatibility checks PASS.
- **Evidence path:** `evidence/operational/adversarial-test-transcript.md`.

### §3.9 Boundary Proof

- **Action:** Run fork secret-scan; check governance doc Tier 3/4 exclusion; trigger HARD STOP (ADR-062: dev workflow only); check S3 retention.
- **Observed:** All boundary checks PASS.
- **Evidence path:** `evidence/operational/fork-secret-scan.txt` + governance doc + HARD STOP test + retention check.

---

## §4 Parent Verification Checklist

> **Parent re-runs every command post-implementation.**

### §4.1 Fork Bootstrap

- [ ] `curl -I https://github.com/fazulfim/hermes-agent` returns 200
- [ ] Fork has LICENSE, NOTICE, FORK_NOTES, SECURITY.md at root
- [ ] Fork base commit matches upstream `hermes-agent` v0.15.2
- [ ] `detect-secrets scan` on fork returns 0 matches

### §4.2 Persistent Task Registry

- [ ] `python -c "from hermes_lifecycle.registry import PersistentTaskRegistry; print(PersistentTaskRegistry)"` prints class
- [ ] `alembic upgrade head` exits 0; `alembic current` shows `P32-001_hermes_tasks`
- [ ] Restart-persistence test: 10/10 tasks survived kill -9
- [ ] Lifecycle hooks fire on test transactions

### §4.3 Model Pool Hot-Swap

- [ ] `python -c "from hermes_model.pool import ModelPool; print(ModelPool.hot_swap)"` prints method
- [ ] Hot-swap latency benchmark < 30s
- [ ] Personality Drift check tests pass (ADR-067): drift_check module importable, no Y6 ceiling concept
- [ ] Hot-swap is auditable (event store entry)

### §4.4 Fork Governance

- [ ] Governance doc exists, parseable
- [ ] Ratchet threshold explicit
- [ ] Tier 1-2 modifications defined as Ratchet-gated autonomous
- [ ] Tier 3/4 modifications explicitly excluded from auto-merge
- [ ] Founder 2/2 review timestamps recorded (both Guinevere + Pharsa)

### §4.5 Mode Selector

- [ ] `--mode fork-native --probe` exit 0, returns fork version
- [ ] `--mode P24-native --probe` exit 0, returns P24 native version
- [ ] Both systemd units `active (running)`
- [ ] Mode can be flipped at runtime without restart of OTHER unit

### §4.6 Permanent Operation Validation (NO SOAK TEST)

- [ ] Operation validation start and end timestamps span ≥ 23h59m
- [ ] At t=6h, 12h, 18h, 24h: 8/8 criteria PASS
- [ ] `promtool query instant` returns 8 series all == 1 at t=24h
- [ ] Persona config byte-equal at t=24h vs t=0

### §4.7 Migration + S3 + Adversarial

- [ ] Migration runbook exists; one-way forward + one-way back documented
- [ ] S3 backup scope includes fork clone + governance + runtime_mode
- [ ] Retention mode COMPLIANCE for all fork-scope keys
- [ ] Adversarial tests pass: P31 invariants preserved, P33 invariants preserved, HARD STOP ≤ 1 message (ADR-062: dev workflow only)
- [ ] One-way back procedure verified manually

### §4.8 Doc-Sync

- [ ] `docs/README.md` has P32 timeline entry
- [ ] Fork governance cross-linked
- [ ] `docs/40-operations/45-InternalOpsManual_v1.0.md` mentions fork-runtime units
- [ ] All cross-reference paths exist (no broken links)

### §4.9 Cross-Cutting

- [ ] All 8 auditor reports exist and are PASS
- [ ] `evidence/P32/verification.md` written by verifier sub-agent with PASS
- [ ] `evidence/P32/auditor-gate.md` written by auditor orchestrator with PASS
- [ ] `evidence/P32/evidence.md` (12-section) is complete
- [ ] No `as any` / `# type:ignore` / `except:` in changed files
- [ ] Boundary proof grid: 7/7 PASS

---

## §5 Verifier Verdict Template

```
P32 — Final Verdict
===================
Date: YYYY-MM-DD HH:MM UTC
Verifier: sub-agent ID + role
Verdict: PASS | FAIL

Fork Existence: PASS/FAIL
Persistent Task Registry: PASS/FAIL
Model Pool Hot-Swap + Personality Drift (ADR-067): PASS/FAIL
Fork Governance: PASS/FAIL
Mode Selector: PASS/FAIL
Permanent Operation Validation (8/8 criteria at 4/4 checkpoints, NO SOAK TEST): PASS/FAIL
Migration Runbook + S3 + Adversarial: PASS/FAIL
Boundary (ADR-067 bebas tanpa batas / ADR-062 dev workflow / Consent (ADR-062/066) / Secret): PASS/FAIL

Hard Rejections (8/8): 8 PASS, 0 FAIL
Adversarial Tests: PASS/FAIL
Doc-Sync: PASS/FAIL
Boundary Audit: PASS/FAIL
Cross-Reference Integrity: PASS/FAIL

Notes: <free text, 1-3 paragraphs>
Caveats: <if any>
Re-audit needed: <yes/no, with reason>

Path: docs/setup-evidence/P28-P36-masterplan/evidence/P32/verification.md
```

---

## §6 Footnotes

- Per AGENTS.md §2.5: scaffold is mandatory; any violation is recorded in evidence, even if later fixed.
- Per AGENTS.md §4: ALL hard rejection criteria are binary.
- Per AGENTS.md §2.8: parent re-runs every scaffold command post-implementation.
- Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`: Y4 baseline, Y5 ceiling, Y6 forbidden.
- Per masterplan synthesis §3.1: P32 = External Presence & Tools (not prerequisite to P28-P31).
- Per ADR-067: Personality drift is bebas tanpa batas with Y4 as starting baseline (not ceiling). Y6 concept REMOVED. No yandere level cap in Hermes runtime.
- Per ADR-062: HARD STOP and consent references in P32 apply to dev workflow only (Guinevere operating contract), NOT Hermes runtime.
- Per brainstorm 2026-06-28: P32 repurposed from original fork-integration scope to "External Presence & Tools". All stale runtime-concept references (deleted ADR, old mode names, removed safety-guard module, soak-stress test) replaced with current paradigm per ADR-062 + ADR-067.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | P32 verification-template initial draft |
| 1.1 | 2026-06-28 | Guinevere | Round-2 auditor fix: replaced all stale runtime-concept refs with current paradigm (ADR-067 drift check, P24-native mode, permanent operation validation, ADR-062/067 disclaimers) |

> **STRICTLY PRIVATE & CONFIDENTIAL.** Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` and AGENTS.md §0. Distribution restricted to Faiz + Guinevere + Pharsa.
