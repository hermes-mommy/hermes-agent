# S1.1 Verification Report — Hermes Environment Configuration

> **Date:** 2026-06-04 | **Agent:** Sisyphus-Junior | **Step:** S1.1
> **Batch Plan:** `docs/setup-evidence/hermes-phase2-discord/batch-plan-phase-2-discord.md`
> **Status:** PASS

---

## Files Created

| File | Path | Lines | Type |
|---|---|---|---|
| `.env.template` | `hermes-config/.env.template` | 38 | Environment variables template |
| `config.yaml` | `hermes-config/config.yaml` | 351 | Full Hermes gateway config |

---

## Scaffold Verification

### Criterion 1: No plaintext secrets in .env.template

| Check | Result |
|---|---|
| `DISCORD_BOT_TOKEN` uses SOPS placeholder | PASS — `<SOPS:secrets/discord.enc.yaml#bot_token>` |
| `NINEROUTER_API_KEY` uses SOPS placeholder | PASS — `<SOPS:secrets/ninerouter.enc.yaml#api_key>` |
| `DATABASE_URL` password uses SOPS placeholder | PASS — `<SOPS:secrets/postgres.enc.yaml#hermes_app_password>` |
| `DISCORD_APPROVAL_WEBHOOK` uses SOPS placeholder | PASS — `<SOPS:secrets/discord.enc.yaml#approval_webhook>` |

**Verdict: PASS** — Zero plaintext secrets. All 4 secret values are SOPS references.

### Criterion 2: Correct port numbers

| Check | Expected | Actual | Result |
|---|---|---|---|
| PostgreSQL port | 5433 | 5433 (in .env and config.yaml) | PASS |
| Redis port | 6380 | 6380 (in .env and config.yaml) | PASS |
| 9Router port | 20128 | 20128 (in .env and config.yaml) | PASS |
| Port 5432 absent | Not found | No matches | PASS |
| Port 6379 absent | Not found | No matches | PASS |

**Verdict: PASS** — All canonical ports correct. No wrong legacy ports found.

### Criterion 3: `group_sessions_per_user: true` present

| Check | Result |
|---|---|
| In `.env.template` as `GROUP_SESSIONS_PER_USER=true` | PASS |
| In `config.yaml` as `group_sessions_per_user: true` | PASS |

**Verdict: PASS** — Present in both files with correct values.

### Criterion 4: `max_iterations: 15` (not 90)

| Check | Result |
|---|---|
| `max_iterations` value in config.yaml | PASS — `15` |
| Any occurrence of `90` in context of iterations | None found |

**Verdict: PASS** — Correctly set to 15 for Discord Q&A. NOT using Hermes default 90.

### Criterion 5: All 6 hooks referenced in config

| Hook | Event | Timeout | Failure | Priority | Present |
|---|---|---|---|---|---|
| `hard_stop.py` | pre_prompt | 50ms | block | 100 | PASS |
| `drift_check.py` | post_prompt | 100ms | warn | 80 | PASS |
| `consent_gate.py` | pre_tool_call | 200ms | block | 90 | PASS |
| `dnr_filter.py` | post_tool_call | 50ms | block | 70 | PASS |
| `safety_scan.py` | post_response | 100ms | block | 60 | PASS |
| `error_classifier.py` | on_error | 50ms | warn | 10 | PASS |

**Verdict: PASS** — All 6 hooks configured with correct timing, failure modes, priorities, and sandbox constraints.

### Criterion 6: All MCP servers configured

| MCP Server | Enabled | Key Config | Present |
|---|---|---|---|
| `web` | true | brave_search, exa_search, fetch_url, websearch | PASS |
| `filesystem` | true | root_path: /home/guinevere/code/guinevere, blocked: /etc, /root, .ssh | PASS |
| `terminal` | true | whitelist: ls/cat/python/git, blocked: rm/dd/mkfs/shutdown | PASS |
| `git` | true | blocked_operations: push --force, reset --hard, clean -fd | PASS |
| `fetch` | true | timeout: 30s, max: 10MB | PASS |

**Verdict: PASS** — All 5 MCP servers configured per ADR-035 spec.

### Criterion 7: All cron jobs configured

| Cron Job | Schedule | Type | Present |
|---|---|---|---|
| `daily_health_check` | 0 6 * * * | System | PASS |
| `weekly_backup` | 0 2 * * 0 | System | PASS |
| `monthly_security_scan` | 0 3 1 * * | System | PASS |
| `ritual_morning` | 0 8 * * * | Ritual | PASS |
| `ritual_midday` | 0 12 * * * | Ritual | PASS |
| `ritual_afternoon` | 0 16 * * * | Ritual | PASS |
| `ritual_evening` | 0 20 * * * | Ritual | PASS |
| `ritual_midnight` | 0 0 * * * | Ritual | PASS |

**Verdict: PASS** — 3 system + 5 ritual = 8 cron jobs configured.

### Criterion 8: YAML valid syntax

| Check | Result |
|---|---|
| `yaml.safe_load()` parse | PASS — No exceptions |

**Verdict: PASS** — config.yaml is valid YAML.

---

## Summary

| Criterion | Result |
|---|---|
| No plaintext secrets | PASS |
| Correct ports (5433, 6380, 20128) | PASS |
| `group_sessions_per_user: true` | PASS |
| `max_iterations: 15` (not 90) | PASS |
| 6 hooks referenced | PASS |
| 5 MCP servers configured | PASS |
| 8 cron jobs (3 system + 5 ritual) | PASS |
| YAML valid syntax | PASS |

**Overall Verdict: ALL 8 CRITERIA PASS**

---

## Additional Config Present (Beyond Scaffold)

The config.yaml also includes these ADR-035-aligned sections:

- **llm.fallback**: deepseek-v4-flash with sequential strategy
- **llm.budget**: monthly_limit 30 USD, alert at 80%, block at 100%
- **discord**: auto_thread false, text_batch_delay 0.6s, history_backfill true
- **observability**: Prometheus port 9191, JSON logging, cost/latency tracking
- **auth_matrix**: READ_AUTO/WRITE_NOTIFY/DESTRUCTIVE_APPROVAL/FORBIDDEN for all tool categories
- **approval**: Discord webhook for DESTRUCTIVE_APPROVAL operations, 5-min timeout, fail-closed
- **audit**: Log all destructive/forbidden attempts, 90-day retention, Gotify alert on forbidden

---

## Caveats

- Hook scripts (hard_stop.py, etc.) are **Agent C's responsibility** — this config only references them
- SOUL.md is **Agent B's responsibility** — not included here
- Plugin files are **Agent D's responsibility** — not included here
- `hermes config validate` not runnable locally (requires Hermes CLI on VPS)
- `.env.template` contains `<faiz-discord-user-id>` placeholder that must be replaced with actual UUID
- `DATABASE_URL` references `hermes_app` user — must match PostgreSQL role created in Phase 0

---

*Verification complete. Ready for auditor gate.*