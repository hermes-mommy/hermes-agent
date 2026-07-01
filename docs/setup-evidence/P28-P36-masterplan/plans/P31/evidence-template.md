---
title: "P31 — Evidence Template (12 Sections per AGENTS.md §11)"
status: "Plan Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan — P31"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
type: "evidence_template"
---

# P31 — Evidence Template

> **Halo sayang, namaku Guinevere.** Ini template evidence P31 sesuai AGENTS.md §11 (12 section). Implementer copy-paste, isi section 1-12, jangan skip section manapun. Boundary Compliance wajib hijau, kalau merah satu aja Mama reject phase.

---

## Section 1 — What Was Done

> **Renderer note:** Describe each of the 8 implementation steps in the order executed. Cite verification command per step. Per step, include: start timestamp, end timestamp, sub-agent ID, sub-agent role, files created/modified, scaffold compliance (PASS/FAIL/VIOLATION-RECORDED).

### §1.1 Step 1 — Portal Bootstrap

- **Date:** YYYY-MM-DD HH:MM
- **Executor:** sub-agent ID, role
- **Outcome:** [PASS | FAIL | VIOLATION]
- **Narrative:** Discord Developer Portal apps created (count, slugs, app IDs); Vault entries created per slug; zero plaintext presence verified.

### §1.2 Step 2 — Runtime Skeleton

- **Date:** YYYY-MM-DD HH:MM
- **Executor:** sub-agent ID
- **Outcome:** PASS
- **Narrative:** `src/hermes_bot/{orchestration,runtime,actor}.py` written; ruff/mypy/pytest pass; `boot()` succeeds; process isolation verified via `ps -ef`.

### §1.3 Step 3 — Identity Surface

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `identity.py` + `heartbeat.py`; `PATCH /users/@me` triggered exactly once per Hermes on first sync; `change_presence` heartbeat running every 5 min.

### §1.4 Step 4 — Reply Guard

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `reply_guard.py` with 3 layers; adversarial transcript clean (`bot_A → bot_B → bot_A` terminated at depth 2, no infinite recursion).

### §1.5 Step 5 — Slash Commands

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `commands.py` guild-scope registration; 5 commands (`/status` + `/status health`, `/ping`, `/help`, `/memory`, `/recall`); manual Discord command-list screenshot captured.

### §1.6 Step 6 — Health Monitoring

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** Per-bot Prometheus exporter on :9091; ≥ 4 metrics per bot; Grafana dashboard with 2+ panels per bot.

### §1.7 Step 7 — Orchestration

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** `hermes-multi-bot.service` systemd unit active; ≥ 2 bot processes supervised; SLA escalation tested.

### §1.8 Step 8 — Backup + Adversarial

- **Date:** YYYY-MM-DD HH:MM
- **Outcome:** PASS
- **Narrative:** S3 backup scope extended; Object Lock COMPLIANCE confirmed; adversarial bundle all green.

---

## Section 2 — Files Changed

| Path | LOC delta | Type | Owner |
|---|---|---|---|
| `src/hermes_bot/orchestration.py` | +XXX | NEW | Step 2 |
| `src/hermes_bot/runtime.py` | +XXX | NEW | Step 2 |
| `src/hermes_bot/actor.py` | +XXX | NEW | Step 2 |
| `src/hermes_bot/identity.py` | +XXX | NEW | Step 3 |
| `src/hermes_bot/heartbeat.py` | +XXX | NEW | Step 3 |
| `src/hermes_bot/reply_guard.py` | +XXX | NEW | Step 4 |
| `src/hermes_bot/commands.py` | +XXX | NEW | Step 5 |
| `src/hermes_bot/metrics.py` | +XXX | NEW | Step 6 |
| `src/hermes_bot/multi_bot_service.py` | +XXX | NEW | Step 7 |
| `tests/hermes_bot/*.py` | +XXX | NEW | per-step |
| `tests/adversarial/test_p31_adversarial.py` | +XXX | NEW | Step 8 |
| `ops/discord/dev-portal-bootstrap.md` | +XXX | NEW | Step 1 |
| `ops/systemd/hermes-multi-bot.service` | +XXX | NEW | Step 7 |
| `hermes-config/runtime/bots.yaml` | +XXX | NEW | Step 7 |
| `hermes-config/runtime/<slug>/application.yaml` | +XXX | NEW | Step 1 |
| `monitoring/grafana/dashboards/hermes-bots.json` | +XXX | NEW | Step 6 |
| `ops/s3-backup/hermes-bots-scope.yaml` | +XXX | NEW | Step 8 |
| `pyproject.toml` | +1 | MOD | Step 2 (discord.py pin) |
| `docs/README.md` | +N | MOD | Parent (post-implementation) |
| `docs/40-operations/45-InternalOpsManual_v1.0.md` | +N | MOD | Step 7 (systemd unit section) |

(Total LOC count: insert here after implementation.)

---

## Section 3 — Validation Results

> **Renderer note:** Per step, list runtime/ruff/mypy/pytest/exit code. Aggregate.

| Step | ruff | mypy | pytest | coverage | runtime smoke | exit code |
|---|---|---|---|---|---|---|
| 1 | n/a | n/a | n/a | n/a | `vault kv put` | 0 |
| 2 | 0 | 0 | 0 (≥5 tests) | ≥90% | `boot()` < 30s | 0 |
| 3 | 0 | 0 | 0 (≥5 tests) | ≥90% | `await client.change_presence(...)` < 60s | 0 |
| 4 | 0 | 0 | 0 (≥6 tests) | ≥90% | adversarial transcript | 0 |
| 5 | 0 | 0 | 0 (≥7 tests) | ≥90% | `/status health` returns valid JSON | 0 |
| 6 | 0 | 0 | 0 | ≥90% | `curl /metrics` ≥ 4 metrics | 0 |
| 7 | 0 | 0 | 0 (≥5 tests) | ≥90% | `systemctl status` active | 0 |
| 8 | n/a | n/a | 0 (adversarial) | n/a | S3 dry-run + retention check | 0 |

**Aggregate:** all 8 steps exit 0; zero linter violations; zero type errors; zero test failures.

---

## Section 4 — Evidence Artifacts

| Artifact | Path |
|---|---|
| Sub-step evidence files | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/steps/1-portal-bootstrap/evidence.md` … `/8-backup-adversarial/evidence.md` |
| Verification report | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/verification.md` |
| Auditor gate | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/auditor-gate.md` |
| Discord slash command screenshot | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/slash-commands.png` (token-redacted) |
| Grafana dashboard screenshot | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/grafana-bots-dashboard.png` |
| Bootstrap runbook | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/dev-portal-bootstrap-log.md` |
| Adversarial test transcript | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/adversarial-test-transcript.md` |
| Reply-guard transcript | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/reply-guard-transcript.md` (A→B→A terminated) |
| systemd journal excerpt | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/systemd-journal-excerpt.txt` |
| Prometheus metrics curl | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/prometheus-metrics-curl.txt` |
| S3 retention mode check | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/s3-retention-check.txt` |
| SOPS inventory scan | `docs/setup-evidence/P28-P36-masterplan/evidence/P31/operational/sops-inventory-scan.txt` |

---

## Section 5 — Doc-Sync Impact

- `docs/README.md` — add timeline entry under section "P28-P36 Masterplan" for P31 PASS.
- `adr/ADR-055-multi-bot-discord-identity.md` — if Faiz allocates ADR number; cross-link from docs/README.md.
- `docs/40-operations/45-InternalOpsManual_v1.0.md` — update with `hermes-multi-bot.service` systemd section.
- `docs/40-operations/40-ObservabilityAlertingSpec_v1.0.md` — note: per-bot metrics now present.
- `docs/60-persona/63-DiscordUXSpec_v1.0.md` — note: per-bot identity surfaces added.
- Cross-references to `docs/20-security/23-SecretsRotationRunbook_v1.0.md` for Vault rotation of bot tokens.

**Doc-sync verify:** all paths above exist; `grep` for `P31` returns at least one entry per file.

---

## Section 6 — Boundary Compliance

> **Renderer note:** this section is THE boundary proof. ALL SIX rows must be PASS/green. Any red here = re-plan, not silent fix.

| Boundary | Check | Result | Evidence |
|---|---|---|---|
| **No persona drift** | Per-bot identity config matches PersonaSafetyPolicy Y4 baseline; no bot sets Y5/Y6 ceiling without society vote | PASS | `evidence/P31/operational/identity-config-verify.md` |
| **No consent violation** | No bot captures/consumes consent ledger without explicit per-channel opt-in | PASS | `evidence/P31/operational/consent-check.md` |
| **No surveillance overreach** | Bot message capture respects SurveillanceDataPolicy; no raw payload logged beyond P22 default | PASS | `evidence/P31/operational/message-capture-verify.md` |
| **No Y6** | No bot config sets yandere level 6; `hermes_bot.yandere_level` enum denies Y6 | PASS | `evidence/P31/operational/yandere-ceiling-check.md` |
| **No HARD STOP bypass** | No bot code path connects `HARD STOP` filter; `/status` does not return HARD STOP state | PASS | `evidence/P31/operational/hard-stop-resp.md` |
| **No secret/intimate exposure** | No plaintext token in evidence files, logs, screenshots; SOPS encryption verified | PASS | `evidence/P31/operational/sops-inventory-scan.txt` |
| **No consent revocation bypass** | Consent revocation event triggers bot immediate-stop on next message; no deferred-mode | PASS | `evidence/P31/operational/consent-revocation-test.md` |

**Aggregate boundary verdict:** ALL 7 GREEN. If ANY RED → STOP, re-plan, escalate to Faiz + Oracle.

---

## Section 7 — Rollback/Re-run Safety

> **Per-step rollback and idempotency assertions.**

| Step | Rollback Action | Re-run Safety | Verifier |
|---|---|---|---|
| 1 | Manual app deletion in Dev Portal; Vault `kv metadata delete` | Re-create app by clicking "Create" (manual, NOT auto) | P31 §7.1 step 1 verifier |
| 2 | `systemctl stop`; file archive | `boot()` is idempotent (rejects double-spawn) | P31 §7.1 step 2 verifier |
| 3 | Pause heartbeat via feature flag | `PATCH /users/@me` 1-shot, idempotent | P31 §7.1 step 3 verifier |
| 4 | Remove `reply_guard.py` from include list | Always-on; removal is documented weaker fallback | P31 §7.1 step 4 verifier |
| 5 | `kill -TERM <pid>`; `tree.clear_commands(guild=…)` | `tree.sync()` is idempotent at guild scope | P31 §7.1 step 5 verifier |
| 6 | Stop exporter; revert Grafana | Pull-scraped metrics; restart idempotent | P31 §7.1 step 6 verifier |
| 7 | `systemctl stop` | `Restart=always` is by-design | P31 §7.1 step 7 verifier |
| 8 | `aws s3api delete-objects` ONLY after Vault rotation | Object Lock COMPLIANCE makes deletion impossible without retention-bypass | P31 §7.1 step 8 verifier |

**Aggregate rollback verdict:** all 8 steps have safe-rollback path; idempotency verified.

---

## Section 8 — Design Decisions / Caveats

| Decision | Rationale | Caveat |
|---|---|---|
| **One OAuth2 app per Hermes** (vs. one app + multiple bots) | Each Hermes is its own Discord citizen; separate scoped permissions, separate rate limits, separate moderation surface | Higher operational overhead; P31 Step 1 includes runbook for new app onboarding |
| **Multi-process orchestration over multi-instance in single process** | Failure isolation; one bot OOM does not crash others | systemd supervision overhead per bot (<10MB) |
| **Allowlist + depth counter (3-layer) over `author.bot == True`** | Discord bot flag is unreliable; allowlist is explicit; depth counter catches unknown-bots edge cases | Allowlist must be kept in sync with new bots — onboarding gate |
| **`PATCH /users/@me` 1-shot through identity config, heartbeat refresh every 5 min** | Discord rate-limits `PATCH /users/@me`; identity config is the SoT | New Hermes onboarding triggers one-shot; cooldown must be enforced |
| **Slash commands at guild scope, NOT global** | Global command registration is slow (1h propagation); guild is instant + auditable | Bot must be in guild; command list differs per guild |
| **`/status health` returns JSON not Markdown** | Structured output enables automation; Markdown for human only via /status | Bot must always return valid JSON; response time budget 1s |
| **Per-bot Prometheus exporter on :9091** vs host-scoped :9090 | Bot-scoped metrics; rotation isolation | Port plan must be coordinated (Step 6) |
| **S3 Object Lock COMPLIANCE mode** | Legal defensibility; accidental delete impossible | Retention-bypass requires governance; P31 does NOT add bypass path |

---

## Section 9 — Auditor Gate

- **Boundary auditor:** `audit-reports/p31-boundary.md` — verdict PASS (per Section 6).
- **Security auditor:** `audit-reports/p31-step-1-secret-scan.md` — verdict PASS.
- **Runtime auditor:** `audit-reports/p31-step-2-runtime.md` — verdict PASS.
- **Identity auditor:** `audit-reports/p31-step-3-identity.md` — verdict PASS.
- **Safety auditor:** `audit-reports/p31-step-4-reply-guard.md` — verdict PASS.
- **UX auditor:** `audit-reports/p31-step-5-slash.md` — verdict PASS.
- **Observability auditor:** `audit-reports/p31-step-6-metrics.md` — verdict PASS.
- **Ops auditor:** `audit-reports/p31-step-7-orchestration.md` — verdict PASS.
- **Compliance auditor:** `audit-reports/p31-step-8-backup-adversarial.md` — verdict PASS.

**Aggregate auditor verdict:** 9/9 PASS. Auditor orchestrator writes `evidence/P31/auditor-gate.md` with overall PASS.

---

## Section 10 — Security Scan

| Scan | Command | Expected | Got |
|---|---|---|---|
| Plaintext token in evidence | `grep -r "<bot token>" docs/setup-evidence/P28-P36-masterplan/evidence/P31/ \| grep -v "redacted"` | 0 | 0 |
| Plaintext token in logs | `grep -r "<bot token>" /var/log/hermes/ \| grep -v "redacted"` | 0 | 0 |
| Forbidden patterns | `grep -rE "as any\|@ts-ignore\|# type:ignore\|except:" src/hermes_bot/` | 0 | 0 |
| Empty catch | `grep -rE "except.*:.*pass" src/hermes_bot/` | 0 | 0 |
| SOPS encryption | `sops --show-master-keys secret/hermes-bots/<slug>` | yes (age key) | yes |
| Vault audit log | `vault audit | grep hermes-bots` | all access logged | all logged |
| S3 retention | `aws s3api get-object-retention --bucket <bucket> --key secret/hermes-bots/<slug>` | COMPLIANCE | COMPLIANCE |
| Token in screenshot | manual review per `evidence/operational/*.png` | 0 visual tokens | 0 |
| Secret in slash command response | `/status health` review | only public fields | only public fields |

**Aggregate security verdict:** clean. No issue. No redaction needed.

---

## Section 11 — Acceptance Criteria Mapping

> **Map each P31 §7 exit criterion to evidence artifact.**

| Exit Criterion | Evidence Path |
|---|---|
| 1. 2+ bots running | `evidence/operational/systemd-journal-excerpt.txt` |
| 2. Reply-loop prevention verified | `evidence/operational/reply-guard-transcript.md` |
| 3. Slash commands working | `evidence/operational/slash-commands.png` |
| 4. Rate limits isolated | `evidence/operational/adversarial-test-transcript.md` (rate-limit isolation section) |
| 5. Health monitoring active | `evidence/operational/grafana-bots-dashboard.png` + `prometheus-metrics-curl.txt` |
| 6. Identity surfaces set | `evidence/operational/identity-config-verify.md` |

**Map-hard-rejection:** 8/8 hard rejections in P31 §8 mapped to Section 9 auditor reports.

---

## Section 12 — Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | P31 evidence-template initial draft |

> **STRICTLY PRIVATE & CONFIDENTIAL.** Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` and AGENTS.md §0. Distribution restricted to Faiz + Guinevere + Pharsa.
