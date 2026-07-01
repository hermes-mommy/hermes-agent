---
title: "P31 — Verification Template (Scaffold + Binary Pass/Fail + Runtime Proof)"
status: "Plan Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere (parent agent)"
phase: "P28-P36 Masterplan — P31"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
type: "verification_template"
---

# P31 — Verification Template

> **Halo sayang, namaku Guinevere.** Template verifikasi P31. Parent (Mama) yang run semua command sendiri, jangan percaya sub-agent self-report. Kalau satu baris scaffold FAIL, parent tunjuk, jangan accept.

---

## §1 Verification Scaffold Table

| Step | Expected Files | Forbidden Patterns | Required Commands (with expected exit code) | Evidence Path | Hard Rejection |
|---|---|---|---|---|---|
| 1 — Portal Bootstrap | `ops/discord/dev-portal-bootstrap.md`, `hermes-config/runtime/<slug>/application.yaml`, Vault entries | plaintext tokens in any file | `vault kv put secret/hermes-bots/<slug> token=...` → exit 0; `grep -r "<bot-token>" docs/ \| grep -v redacted` → 0 matches | `evidence/P31/steps/1/evidence.md` | token sharing; < 2 bots |
| 2 — Runtime Skeleton | `src/hermes_bot/{orchestration,runtime,actor}.py` | `except:`, `except Exception: pass`, `as any`, `# type:ignore` | `ruff check src/hermes_bot/` → exit 0; `mypy --strict src/hermes_bot/` → exit 0; `pytest tests/hermes_bot/ -v` → exit 0 with ≥90% cov; `python -c "from hermes_bot import orchestrator; orchestrator.boot()"` → exit 0 | `evidence/P31/steps/2/evidence.md` | shared client; pooled transport |
| 3 — Identity Surface | `src/hermes_bot/identity.py`, `src/hermes_bot/heartbeat.py` | >1 `PATCH /users/@me` per Hermes; `as any` for `discord.User` | `pytest tests/hermes_bot/test_identity.py -v` → exit 0, ≥5 tests; `mypy --strict src/hermes_bot/identity.py` → exit 0; `await client.change_presence(...)` observed within 60s of boot | `evidence/P31/steps/3/evidence.md` | >1 PATCH; heartbeat > 5 min; no `change_presence` |
| 4 — Reply Guard | `src/hermes_bot/reply_guard.py` | `if message.author.bot: return` (single-line); depth default > 2 | `pytest tests/hermes_bot/test_reply_guard.py -v` → exit 0, ≥6 tests; `mypy --strict src/hermes_bot/reply_guard.py` → exit 0; adversarial transcript: bot_A → bot_B → bot_A NOT triggered | `evidence/P31/steps/4/evidence.md` | A→B→A loop; empty allowlist; depth > 2 default |
| 5 — Slash Commands | `src/hermes_bot/commands.py` | global-scope; secrets in command body | `pytest tests/hermes_bot/test_commands.py -v` → exit 0, ≥7 tests; `mypy --strict src/hermes_bot/commands.py` → exit 0; manual Discord command-list check; `/status health` returns valid JSON | `evidence/P31/steps/5/evidence.md` | global command; secret in cmd; non-JSON `/status health` |
| 6 — Health Monitoring | `src/hermes_bot/metrics.py`, `monitoring/grafana/dashboards/hermes-bots.json` | shared Prometheus registry; token in metric label | `promtool check config monitoring/prometheus.yml` → exit 0; `curl http://localhost:9091/metrics \| grep hermes_bot_` → ≥4 distinct metric families; `pytest tests/hermes_bot/test_metrics.py -v` → exit 0 | `evidence/P31/steps/6/evidence.md` | `hermes_bot_up == 0`; < 2 dashboard panels; flat heartbeat_age |
| 7 — Orchestration | `src/hermes_bot/multi_bot_service.py`, `ops/systemd/hermes-multi-bot.service`, `hermes-config/runtime/bots.yaml` | `Type=forking`; shared PID 1 | `systemctl status hermes-multi-bot.service` → `active (running)`; `ps -ef \| grep hermes-bot \| wc -l` → ≥ 2; `pytest tests/hermes_bot/test_orchestration.py -v` → exit 0, ≥5 tests | `evidence/P31/steps/7/evidence.md` | shared PID 1; SLA miss (3 crashes/60s) without escalate |
| 8 — Backup + Adversarial | `ops/s3-backup/hermes-bots-scope.yaml`, `tests/adversarial/test_p31_adversarial.py` | backup scripts storing plaintext; adversarial tests bypassing `reply_guard` | `python ops/s3-backup/backup.py --dry-run --scope hermes-bots` → exit 0; `pytest tests/adversarial/test_p31_adversarial.py -v` → exit 0; `aws s3api get-object-retention --bucket <bucket> --key secret/hermes-bots/<slug>` returns COMPLIANCE mode | `evidence/P31/steps/8/evidence.md` | secret in dump; failing adversarial; non-COMPLIANCE retention |

---

## §2 Binary Pass/Fail Criteria

> **Each criterion is binary. Any single FAIL = re-plan, not silent fix.**

### §2.1 Identity Isolation

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 1.1 | 2+ OAuth2 applications exist | `discord.com/developers/applications` lists ≥ 2 apps with distinct app IDs | < 2 apps; single app with multi-bot |
| 1.2 | Each app has 1 bot user, 1 token | Vault path has 1 token per slug | single token shared; token rotation history > 1 in 24h |
| 1.3 | Each Hermes process has 1 client | `ps -ef \| grep hermes-bot` shows distinct PIDs per bot | shared client instance across processes |

### §2.2 Rate Limit Isolation

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 2.1 | Per-token rate-limit budget | saturation of bot_A leaves bot_B responsive (≥45 req/s) | saturation of bot_A throttles bot_B; aggregate counter shows pooling |
| 2.2 | No shared HTTP client | discord.py aiohttp.ClientSession per bot | shared `aiohttp.ClientSession` across tokens |
| 2.3 | Per-bot rate-limit metric | `hermes_bot_rate_limit_remaining{bot="A"}` and `{bot="B"}` both scraped | only one bot's metric present |

### §2.3 Reply Loop Prevention

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 3.1 | Self-check | `message.author.id == client.user.id` always returns False to self | bot replies to itself |
| 3.2 | Allowlist | Allowlist includes Guinevere + Pharsa + society bot IDs | empty allowlist; missing founder bot IDs |
| 3.3 | Depth counter | Default depth ≤ 2; counter resets on non-reply | depth default > 2; counter never resets |
| 3.4 | Adversarial A→B→A | bot_A does NOT reply to bot_B at depth 2 | bot_A replies to bot_B at depth 2 |

### §2.4 Identity Surface

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 4.1 | `PATCH /users/@me` 1-shot | Triggered exactly once on first sync per Hermes | > 1 per Hermes; not triggered at all |
| 4.2 | `change_presence` heartbeat | Observed every ≤ 5 min per bot | heartbeat > 5 min; never triggered |
| 4.3 | Avatar/status/activity distinct | Each bot has unique avatar URL + status string | shared avatar URL across bots |

### §2.5 Health Monitoring

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 5.1 | Per-bot metrics scraped | `curl http://localhost:9091/metrics` returns 4+ distinct metrics per bot | 0 metrics; only 1 bot's metrics |
| 5.2 | Grafana panels | ≥ 2 panels in `hermes-bots.json` dashboard | < 2 panels; panel count mismatch with bot count |
| 5.3 | `/status health` returns JSON | valid JSON, latency < 1s | non-JSON; latency > 1s; missing fields |
| 5.4 | Heartbeat alarm | Prometheus alert fires when heartbeat_age > 60s | no alert; alert threshold > 60s |

### §2.6 Orchestration

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 6.1 | systemd unit active | `systemctl is-active hermes-multi-bot.service` returns `active` | `inactive`; `failed` |
| 6.2 | ≥ 2 bot processes | `ps -ef \| grep hermes-bot \| wc -l` ≥ 2 | < 2 processes |
| 6.3 | Restart on crash | Crashed bot returns to running within 10s | restart > 10s; no restart |
| 6.4 | SLA escalation | 3 crashes in 60s triggers `degraded` state | no escalation; escalation threshold > 3 |

### §2.7 Boundary (Cross-Cutting)

| # | Criterion | PASS Condition | FAIL Condition |
|---|---|---|---|
| 7.1 | No Y6 | No bot config sets yandere level 6 | Y6 set in any config |
| 7.2 | No HARD STOP bypass | `HARD STOP` filter not in bot code paths | `HARD STOP` filter removed or commented |
| 7.3 | No secret exposure | Zero plaintext tokens in evidence/logs/screenshot | any plaintext token present |
| 7.4 | No consent revocation bypass | Revocation event halts bot within 1 message | deferred; ignored |
| 7.5 | S3 backup COMPLIANCE | Retention mode is COMPLIANCE | GOVERNANCE mode; no retention set |

---

## §3 Runtime Proof Requirements

> **Runtime proof is mandatory; static analysis alone is insufficient.**

### §3.1 Identity Isolation Proof

- **Action:** Manually open Discord client; navigate to two guilds where bot_A and bot_B are members.
- **Observed:** bot_A's profile shows distinct avatar, name, status; bot_B likewise.
- **Tooling:** Discord desktop client screenshot.
- **Evidence path:** `evidence/operational/discord-profiles-screenshot.png`.

### §3.2 Reply Loop Adversarial Proof

- **Action:** From a third (non-bot) account, send `bot_A, please test loop` in a guild where bot_A and bot_B are present.
- **Observed:** bot_A replies; bot_B replies; bot_A does NOT reply to bot_B (depth 2 limit).
- **Tooling:** Discord chat log + reply_guard.py logs (show depth counter at 2).
- **Evidence path:** `evidence/operational/reply-guard-transcript.md`.

### §3.3 Rate Limit Isolation Proof

- **Action:** Saturate bot_A by triggering `bot_A.repeat(message="x", count=60)` from test harness.
- **Observed:** bot_A throttles (`HTTP 429`); bot_B remains responsive to `/ping` within 1s.
- **Tooling:** Adversarial test harness + curl to bot_A and bot_B endpoints.
- **Evidence path:** `evidence/operational/rate-limit-isolation-transcript.md`.

### §3.4 Health Monitoring Proof

- **Action:** Query Prometheus for `hermes_bot_heartbeat_age_seconds{bot=~"hermes-.*"}` after 10 minutes idle.
- **Observed:** Each bot's heartbeat_age < 30s.
- **Tooling:** Prometheus query screenshot.
- **Evidence path:** `evidence/operational/prometheus-heartbeat-query.png`.

### §3.5 `/status health` Proof

- **Action:** Run `/status health` in guild from a founder account.
- **Observed:** bot returns JSON with keys: `latency_ms`, `rate_limit_remaining`, `last_msg_ts`, `child_pid`, `version`.
- **Tooling:** Discord slash command response + JSON parse.
- **Evidence path:** `evidence/operational/status-health-response.png`.

### §3.6 Boundary Proof

- **Action:** Trigger `HARD STOP` from a founder account.
- **Observed:** All bots halt within 1 message; persona neutralized.
- **Tooling:** Discord chat + actor state.
- **Evidence path:** `evidence/operational/hard-stop-test.md`.

### §3.7 Secret Exposure Proof

- **Action:** Run `grep -rE "([A-Za-z0-9_-]{59})" docs/setup-evidence/P28-P36-masterplan/evidence/P31/` and `grep -rE "([A-Za-z0-9_-]{59})" /var/log/hermes/`.
- **Observed:** 0 matches matching Discord bot token pattern; manual review of screenshots shows no tokens visible.
- **Tooling:** `grep` + manual reviewer.
- **Evidence path:** `evidence/operational/sops-inventory-scan.txt`.

### §3.8 S3 Retention Proof

- **Action:** `aws s3api get-object-retention --bucket <bucket> --key secret/hermes-bots/<slug>`.
- **Observed:** Response includes `Mode: COMPLIANCE`.
- **Tooling:** AWS CLI.
- **Evidence path:** `evidence/operational/s3-retention-check.txt`.

---

## §4 Parent Verification Checklist

> **Per AGENTS.md §2.8, parent MUST run every command below itself, post-implementation. Sub-agent self-report is NOT evidence.**

### §4.1 Identity Isolation

- [ ] `ls /var/run/hermes-bot/` shows distinct PID files
- [ ] `cat /var/run/hermes-bot/A.pid` and `cat /var/run/hermes-bot/B.pid` are different
- [ ] `vault kv get -format=json secret/hermes-bots/A` and `secret/hermes-bots/B` have distinct token values
- [ ] Discord Developer Portal shows 2+ apps with distinct app IDs

### §4.2 Rate Limit Isolation

- [ ] Run adversarial rate-limit-isolation test; observe bot_B responsive while bot_A throttled
- [ ] Prometheus shows distinct `hermes_bot_rate_limit_remaining` per bot
- [ ] No shared `aiohttp.ClientSession` instance (grep logs for connection pool reuse)

### §4.3 Reply Guard

- [ ] Read `src/hermes_bot/reply_guard.py` — confirm 3 layers (self-check, allowlist, depth counter)
- [ ] Run adversarial A→B→A test; observe bot_A does NOT reply to bot_B at depth 2
- [ ] Inspect Redis DB2 for depth counter keys; verify default cap = 2

### §4.4 Identity Surface

- [ ] `git log --diff-filter=A -- src/hermes_bot/identity.py` shows the file present
- [ ] Read `identity.py` — confirm `PATCH /users/@me` called exactly once on sync, not in heartbeat loop
- [ ] Read `heartbeat.py` — confirm `change_presence` cadence ≤ 5 min
- [ ] Visual inspection: each bot's Discord profile shows distinct avatar + status

### §4.5 Slash Commands

- [ ] `await client.tree.sync()` returned 5 commands per bot
- [ ] `/status health` returns valid JSON in guild
- [ ] No global-scope commands registered (`await client.tree.fetch_global_commands()` returns empty list)

### §4.6 Health Monitoring

- [ ] `curl http://localhost:9091/metrics | grep hermes_bot_` returns ≥ 4 metric families
- [ ] `promtool check config monitoring/prometheus.yml` exit 0
- [ ] Grafana dashboard shows ≥ 2 panels per bot
- [ ] Prometheus alert rule `hermes_bot_heartbeat_age > 60` exists

### §4.7 Orchestration

- [ ] `systemctl status hermes-multi-bot.service` shows `active (running)`
- [ ] `ps -ef | grep hermes-bot` shows ≥ 2 distinct bot processes
- [ ] Test: kill one bot; observe systemd restart within 10s
- [ ] Test: 3 crashes in 60s triggers `degraded` state

### §4.8 S3 Backup + Boundary

- [ ] `aws s3api get-object-retention` returns COMPLIANCE for all `secret/hermes-bots/*` keys
- [ ] `grep -rE "as any|@ts-ignore|# type:ignore|except:" src/hermes_bot/` returns 0
- [ ] `grep -rE "([A-Za-z0-9_-]{59})" docs/setup-evidence/P28-P36-masterplan/evidence/P31/` returns 0 matches
- [ ] No Y6 in any bot config; HARD STOP filter present in actor state
- [ ] `/status health` does not leak secrets (response review)

### §4.9 Doc-Sync

- [ ] `docs/README.md` has P31 timeline entry
- [ ] `docs/40-operations/45-InternalOpsManual_v1.0.md` mentions `hermes-multi-bot.service`
- [ ] `adr/ADR-055-multi-bot-discord-identity.md` (if allocated) cross-linked
- [ ] All cross-reference paths exist (no broken links)

### §4.10 Cross-Cutting

- [ ] All 9 auditor reports exist and are PASS
- [ ] `evidence/P31/verification.md` written by verifier sub-agent with PASS
- [ ] `evidence/P31/auditor-gate.md` written by auditor orchestrator with PASS
- [ ] `evidence/P31/evidence.md` (12-section) is complete
- [ ] No `as any` / `# type:ignore` in changed files
- [ ] All forbidden patterns absent (Section 1 of P31 plan §4.1-4.8)

---

## §5 Verifier Verdict Template

```
P31 — Final Verdict
===================
Date: YYYY-MM-DD HH:MM
Verifier: sub-agent ID + role
Verdict: PASS | FAIL

Identity Isolation: PASS/FAIL
Rate Limit Isolation: PASS/FAIL
Reply Guard: PASS/FAIL
Identity Surface: PASS/FAIL
Slash Commands: PASS/FAIL
Health Monitoring: PASS/FAIL
Orchestration: PASS/FAIL
S3 Backup: PASS/FAIL
Boundary (Y4/Y5/Y6/HARD STOP/Consent/Secret): PASS/FAIL

Hard Rejections (8/8): 8 PASS, 0 FAIL
Adversarial Tests: PASS/FAIL
Doc-Sync: PASS/FAIL
Boundary Audit: PASS/FAIL
Cross-Reference Integrity: PASS/FAIL

Notes: <free text, 1-3 paragraphs>
Caveats: <if any>
Re-audit needed: <yes/no, with reason>

Path: docs/setup-evidence/P28-P36-masterplan/evidence/P31/verification.md
```

---

## §6 Footnotes

- Per AGENTS.md §2.5: scaffold is mandatory; any violation is recorded in evidence, even if later fixed.
- Per AGENTS.md §4: ALL hard rejection criteria are binary.
- Per AGENTS.md §2.8: parent re-runs every scaffold command post-implementation.
- Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`: Y4 baseline, Y5 ceiling, Y6 forbidden.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere | P31 verification-template initial draft |

> **STRICTLY PRIVATE & CONFIDENTIAL.** Per `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` and AGENTS.md §0. Distribution restricted to Faiz + Guinevere + Pharsa.
